"""Authentication (session ID / access token) for the TCC v1 and v2 APIs."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt
from email.utils import parsedate_to_datetime
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypedDict

import aiohttp
import probatio as vol
from aiohttp import hdrs

from . import exceptions as exc
from .const import (
    DEFAULT_RETRY_AFTER,
    ERR_MSG_LOOKUP_BASE,
    HINT_CHECK_NETWORK,
    HOSTNAME,
    ContentType,
)
from .exceptions import ApiCallErrorReason
from .helpers import (
    convert_dtms_to_utc_str,
    convert_keys_to_camel_case,
    convert_keys_to_snake_case,
    convert_str_enums_to_pascal_case,
    redact_secrets,
)

type _TccResponse = dict[str, Any] | list[dict[str, Any]]

# the keys of the vendor's error code: e.g. [{"code": "DeviceIsLost", ...}] (a request),
# or {"error": "invalid_grant", ...} (an OAuth token request)
_SZ_CODE: Final = "code"
_SZ_ERROR: Final = "error"


class _ApiCallDetails(TypedDict, total=False):
    """The details of an ApiCallFailedError (as a TypedDict, so it is precisely typed).

    So that `**details` cannot be mistaken (e.g. by mypy) for another keyword argument
    of the exception, such as `reason`.
    """

    code: str  # the vendor's error code (if any), e.g. "DeviceIsLost"


if TYPE_CHECKING:
    from collections.abc import Mapping

    from aiohttp.typedefs import StrOrURL

    from .helpers import Validator


async def _payload(rsp: aiohttp.ClientResponse | None) -> str:
    if rsp is None:
        return "<no response>"

    try:
        if rsp.content_type == ContentType.JSON:
            return json.dumps(await rsp.json())
        if rsp.content_type == ContentType.TEXT_PLAIN:
            return await rsp.text()
        return await rsp.text()  # text/html?

    except aiohttp.ClientPayloadError:
        return "<no response>"
    except aiohttp.ClientError:
        return "<no response>"


def _details_of(details: Mapping[str, str]) -> _ApiCallDetails:
    """Return the details of an ApiCallFailedError (e.g. to pass on to another one)."""
    return {_SZ_CODE: details[_SZ_CODE]} if _SZ_CODE in details else {}


async def _details(rsp: aiohttp.ClientResponse | None) -> _ApiCallDetails:
    """Return the details of an error response: its vendor's error code (if any).

    The response's body must have already been read (so there is no further I/O).
    """

    if rsp is None or rsp.content_type != ContentType.JSON:
        return {}

    try:
        body = await rsp.json()
    except (aiohttp.ClientError, json.JSONDecodeError):
        return {}

    if isinstance(body, list) and body and isinstance(body[0], dict):
        code = body[0].get(_SZ_CODE)
    elif isinstance(body, dict):
        code = body.get(_SZ_CODE, body.get(_SZ_ERROR))
    else:
        code = None

    return {_SZ_CODE: code} if isinstance(code, str) else {}  # i.e. _ApiCallDetails


def _reason(status: int) -> ApiCallErrorReason:
    """Return the reason for a response that has an HTTP error status."""

    if status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
        return ApiCallErrorReason.RATE_LIMITED
    if status == HTTPStatus.UNAUTHORIZED:  # 401
        return ApiCallErrorReason.UNAUTHORIZED
    if HTTPStatus.BAD_REQUEST <= status < HTTPStatus.INTERNAL_SERVER_ERROR:  # a 4xx
        return ApiCallErrorReason.REQUEST_REJECTED
    if status >= HTTPStatus.INTERNAL_SERVER_ERROR:  # a 5xx
        return ApiCallErrorReason.SERVER_ERROR
    return ApiCallErrorReason.CALL_FAILED


def _retry_after(rsp: aiohttp.ClientResponse | None) -> float:
    """Return how long to wait before trying again, in seconds (e.g. after a 429).

    That is the period of the response's Retry-After header, else (if it has none, or
    it is not valid) DEFAULT_RETRY_AFTER: the vendor's 429s have not had one.
    """

    if rsp is None or (value := rsp.headers.get(hdrs.RETRY_AFTER)) is None:
        return DEFAULT_RETRY_AFTER

    if value.strip().isdecimal():  # is delay-seconds
        return float(value)

    try:  # is HTTP-date
        dtm = parsedate_to_datetime(value)
    except ValueError:
        return DEFAULT_RETRY_AFTER

    if dtm.tzinfo is None:  # e.g. a zone of -0000
        dtm = dtm.replace(tzinfo=UTC)
    return max(0.0, (dtm - dt.now(tz=UTC)).total_seconds())


def _api_call_failed(
    message: str,
    status: int,
    rsp: aiohttp.ClientResponse | None,
    details: _ApiCallDetails,
) -> exc.ApiCallFailedError:
    """Return the exception for a response that has an HTTP error status.

    A 4xx (other than a 401 or a 429) means the vendor rejected the request (e.g. a 400
    with SystemModeChangeTimeUntilNotSet, or a 404), and trying again will not help.
    A 401 is left to higher layers (see AbstractAuth.request()).
    """

    reason = _reason(status)

    if reason is ApiCallErrorReason.RATE_LIMITED:  # 429 (the class's default reason)
        return exc.ApiRateLimitExceededError(
            message, status, retry_after=_retry_after(rsp), response=rsp, **details
        )
    if reason is ApiCallErrorReason.REQUEST_REJECTED:  # (the class's default reason)
        return exc.ApiCallRejectedError(message, status=status, response=rsp, **details)
    return exc.ApiCallFailedError(
        message, status=status, reason=reason, response=rsp, **details
    )


class AbstractAuth(ABC):
    """A class to provide to access the Resideo TCC API.

    It manages the credential (an access token, or a session id) of its requests: if
    the vendor rejects one that should be valid (a 401), it is cleared (so another is
    fetched), and the request is made again (once). So a 401 that is raised means that
    the request was not allowed (e.g. an id that is not the user's).
    """

    _url_base: StrOrURL

    # a URL that is open to any authenticated user: so its 401 is of the credential
    _URL_PROBE: ClassVar[str]
    _CREDENTIAL: ClassVar[str]  # its name, e.g. "access_token" (for log messages)

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        /,
        *,
        logger: logging.Logger,
        _hostname: str | None = None,
    ) -> None:
        """A class for interacting with the Resideo TCC API."""

        self.websession: Final = websession

        self._logger: Final = logger
        self._hostname: Final = _hostname or HOSTNAME

    def __str__(self) -> str:
        """Return a string representation of the object."""
        return f"{self.__class__.__name__}(base='{self.url_base}')"

    @property
    def hostname(self) -> str:
        """Return the hostname used for GET/PUT requests."""
        return self._hostname

    @property
    def url_base(self) -> StrOrURL:
        """Return the URL base used for GET/PUT requests."""
        return self._url_base

    async def get[T](self, url: StrOrURL, /, schema: Validator[T]) -> T:
        """Call the vendor's TCC API with a GET.

        A schema is required; it is used to convert datetimes and strEnums from the
        vendor's format after getting.
        """

        response: _TccResponse = await self.request(HTTPMethod.GET, url)

        try:
            return schema(response)
        except vol.Invalid as err:
            raise exc.BadApiResponseError(
                f"GET {url}: response failed validation: {err}",
            ) from err

    async def put(
        self,
        url: StrOrURL,
        /,
        json: Mapping[str, object],
        *,
        schema: Validator[Mapping[str, object]] | None = None,
    ) -> _TccResponse:  # NOTE: not _EvoSchemaT
        """Call the vendor's TCC API with a PUT.

        A schema is optional and any vol.Invalid is merely logged as a warning.
        """

        payload: Mapping[str, object] = json

        if schema:
            try:
                payload = schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"PUT {url}: payload failed validation: {err}")

        return await self.request(HTTPMethod.PUT, url, json=payload)

    async def request(
        self,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        *,
        json: Mapping[str, object] | None = None,
    ) -> _TccResponse:
        """Make a request to the vendor's RESTful API (which does not use snake_case).

        Converts JSON keys to/from snake_case/camelCase as required.

        Helper functions are used to convert datetimes and strEnums to the vendor's
        format before putting.
        """

        if json is not None:
            json = convert_dtms_to_utc_str(json)
            json = convert_str_enums_to_pascal_case(json)
            json = convert_keys_to_camel_case(json)

        # if valid, this is the credential that is sent (without yielding first)
        credential = self._credential_in_use()

        try:
            response = await self._make_request(method, url, json=json)
        except exc.AuthenticationFailedError:  # was unable to authenticate
            raise
        except exc.ApiCallFailedError as err:
            # a 401 is either of the credential (it was rejected), or of the request
            # (e.g. no access to that loc_id): if the latter, raise it
            if (
                err.status != HTTPStatus.UNAUTHORIZED  # 401
                or not await self._is_credential_rejected(url)
            ):
                raise

            self._logger.warning(
                f"The {self._CREDENTIAL} has been rejected (will re-authenticate): {err}"
            )
            self._clear_rejected_credential(credential)

            # with another credential, a 401 is of the request (or it was rejected too)
            response = await self._make_request(method, url, json=json)

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(
                f"{method} {self.url_base}/{url}: {redact_secrets(response)}"
            )

        return convert_keys_to_snake_case(response)

    @abstractmethod
    async def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Ensure the authorization header is valid.

        This could take the form of an access token, or a session ID.
        """

    @abstractmethod
    def _credential_in_use(self) -> str | None:
        """Return the credential that the next request will send, if it is valid.

        Else None (as the next request will fetch another).
        """

    @abstractmethod
    def _clear_rejected_credential(self, rejected: str | None) -> None:
        """Clear the credential that was rejected (so another is fetched).

        Unless another task has since refreshed it, so as not to clear the new one.
        """

    async def _is_credential_rejected(self, url: StrOrURL) -> bool:
        """Return True if a 401 of a URL was because the credential was rejected.

        A 401 is either because the credential was rejected, or because the user has no
        access to that URL (e.g. to that location). As the probe URL is open to all
        authenticated users, a 401 from it can only be due to the former.

        If that can't be determined (e.g. the probe is a 5xx), raise the probe's error.
        """

        if url == self._URL_PROBE:
            return True

        try:
            await self._make_request(HTTPMethod.GET, self._URL_PROBE)
        except exc.AuthenticationFailedError:  # was unable to authenticate
            raise
        except exc.ApiCallFailedError as err:
            if err.status != HTTPStatus.UNAUTHORIZED:  # 401
                raise
            return True

        return False

    async def _make_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> _TccResponse:
        """Make a GET/PUT request and return the response (a dict or a list).

        Will raise an exception if the request is not successful.
        """

        rsp: aiohttp.ClientResponse | None = None  # to prevent unbound error

        url = f"{self.url_base}/{url}"
        headers = await self._headers(kwargs.pop("headers", {}))

        try:
            rsp = await self._request(method, url, headers=headers, **kwargs)
            assert rsp is not None  # mypy hint

            await rsp.read()  # so we can use rsp.json()/rsp.text(), below
            rsp.raise_for_status()

            # can't assert content_length != 0 with aioresponses, so skip that check
            if rsp.content_type != ContentType.JSON:  # usu. "text/plain", "text/html"
                raise exc.ApiCallFailedError(
                    f"{method} {url}: response is not JSON: {await _payload(rsp)}",
                    reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                    response=rsp,
                )

            raw = await rsp.json()
            if raw is None:  # an unanticipated edge-case
                raise exc.ApiCallFailedError(
                    f"{method} {url}: response is null",
                    reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                    response=rsp,
                )
            response: _TccResponse = raw

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise exc.ApiCallFailedError(
                f"{method} {url}: response is not valid JSON: {await _payload(rsp)}",
                reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                response=rsp,
            ) from err

        # An invalid access_token / session_id will cause a 401 and we'd need to
        # re-authenticate; unfortunately, other scenarios cause 401s (e.g. wrong
        # usr_id/loc_id in URL). So leave it up to the consumer to detect/handle
        # such 401s as they can tell if was well-known URL (e.g. without usr_id)

        except aiohttp.ClientResponseError as err:
            if hint := ERR_MSG_LOOKUP_BASE.get(err.status):
                self._logger.error(hint)  # noqa: TRY400

            msg = f"{err.status} {err.message}"
            if rsp:
                msg += f", response={await _payload(rsp)}"

            raise _api_call_failed(
                f"{method} {url}: {msg}", err.status, rsp, await _details(rsp)
            ) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            self._logger.error(HINT_CHECK_NETWORK)  # noqa: TRY400

            raise exc.ApiCallFailedError(
                f"{method} {url}: {err}",
                reason=ApiCallErrorReason.CONNECTION_FAILED,
                response=rsp,  # usu. None
            ) from err

        else:
            return response

        finally:
            if rsp is not None:
                rsp.release()

    async def _request(  # dev/test wrapper
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Wrap the request to the ClientSession (useful for dev/test)."""
        return await self.websession.request(method, url, **kwargs)
