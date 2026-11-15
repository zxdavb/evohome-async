"""Credentials management for the TCC v1 and v2 APIs."""

from __future__ import annotations

import json
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import aiohttp

from . import exceptions as exc
from .auth import (
    _SZ_CODE,
    _ApiCallDetails,
    _details,
    _errors,
    _payload,
    _reason,
    _retry_after,
)
from .const import (
    ERR_MSG_LOOKUP_BASE,
    HINT_BAD_CREDS,
    HINT_CHECK_NETWORK,
    HOSTNAME,
    ContentType,
)
from .exceptions import ApiCallErrorReason

if TYPE_CHECKING:
    import logging
    from collections.abc import Mapping

    from aiohttp.typedefs import StrOrURL


# the vendor's values that say a request was refused for the user's credentials
_S1_BAD_CREDENTIALS: Final = "EmailOrPasswordIncorrect"  # v1: its error code
_S2_INVALID_GRANT: Final = "invalid_grant"  # v2: its (OAuth) error code
_S2_GRANT_TYPE: Final = "grant_type"  # v2: a key of its request's (form) data
_S2_CREDENTIALS_GRANT: Final = "password"  # v2: the grant type of a client_id/secret


async def _failed_auth_error(
    err: aiohttp.ClientResponseError,
    rsp: aiohttp.ClientResponse | None,
    details: _ApiCallDetails,
    /,
    *,
    bad_credentials: bool,
) -> exc.AuthenticationFailedError:
    """Return the error of a failed authentication request (v1 or v2), by its response.

    It is a BadUserCredentialsError if the request was refused for the user's
    credentials, e.g. v1's EmailOrPasswordIncorrect (a 401), or v2's invalid_grant (a
    400) of a password grant (but not of a refresh token).
    """

    msg = f"{err.status} {err.message}, response={await _payload(rsp)}"
    errors = await _errors(rsp)  # v1: e.g. [{"code": "TooManyRequests", ...}]

    if err.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
        return exc.AuthRateLimitExceededError(
            f"Authenticator response is invalid: {msg}",
            err.status,
            retry_after=_retry_after(rsp),
            response=rsp,
            errors=errors,
            **details,
        )

    if bad_credentials:
        return exc.BadUserCredentialsError(
            f"Authenticator response is invalid: {msg}",
            status=err.status,
            response=rsp,
            errors=errors,
            **details,
        )

    return exc.AuthenticationFailedError(
        f"Authenticator response is invalid: {msg}",
        status=err.status,
        reason=_reason(err.status),
        response=rsp,
        errors=errors,
        **details,
    )


class CredentialsManagerBase:
    """A base class for managing the credentials used for HTTP authentication."""

    def __init__(
        self,
        client_id: str,
        secret: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        logger: logging.Logger,
        _hostname: str | None = None,
    ) -> None:
        """Initialise the session manager."""

        self._client_id = client_id
        self._secret = secret
        self.websession: Final = websession

        self._logger = logger
        self._hostname: Final = _hostname or HOSTNAME

        self._was_authenticated = False  # True once credentials are proven valid

    def __str__(self) -> str:
        """Return a string representation of the object."""
        return (
            f"{self.__class__.__name__}"
            f"(client_id='{self.client_id}', hostname='{self.hostname}')"
        )

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    @property
    def hostname(self) -> str:
        """Return the hostname used for HTTP authentication."""
        return self._hostname

    def _is_bad_credentials(self, data: Mapping[str, str], code: str | None) -> bool:
        """Return True if a failed request (v1 or v2) was refused for the user's credentials.

        Not overridden per API: one manager may serve both (e.g. the CLI's, or HA's).

        v1: its only request is with the user's client_id/secret, so its code is enough.
        v2: only a password grant has them; an invalid_grant of a refresh token means only
        that the refresh token is invalid (so the client_id/secret are used instead).
        """

        if (
            code == _S2_INVALID_GRANT
            and data.get(_S2_GRANT_TYPE) == _S2_CREDENTIALS_GRANT
        ):
            return True
        return code == _S1_BAD_CREDENTIALS

    async def _post_request(self, url: StrOrURL, /, **kwargs: Any) -> dict[str, Any]:
        """POST an authentication request and return the response (a dict).

        Will raise an exception if the authentication is not successful (a
        BadUserCredentialsError if it was refused for the user's credentials).
        """

        rsp: aiohttp.ClientResponse | None = None  # to prevent unbound error

        try:
            rsp = await self._request(HTTPMethod.POST, url, **kwargs)
            assert rsp is not None  # mypy hint

            await rsp.read()  # so we can use rsp.json()/rsp.text(), below
            rsp.raise_for_status()

            # can't assert content_length != 0 with aioresponses, so skip that check
            if rsp.content_type != ContentType.JSON:  # usu. "text/plain", "text/html"
                raise exc.AuthenticationFailedError(
                    f"Authenticator response is not JSON: {await _payload(rsp)}",
                    reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                    response=rsp,
                )

            raw = await rsp.json()
            if raw is None:  # an unanticipated edge-case
                raise exc.AuthenticationFailedError(
                    "Authenticator response is null",
                    reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                    response=rsp,
                )
            response: dict[str, Any] = raw

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is not valid JSON: {await _payload(rsp)}",
                reason=ApiCallErrorReason.RESPONSE_NOT_JSON,
                response=rsp,
            ) from err

        except aiohttp.ClientResponseError as err:
            details = await _details(rsp)  # e.g. {"code": "invalid_grant"}
            bad_creds = self._is_bad_credentials(
                kwargs.get("data", {}), details.get(_SZ_CODE)
            )
            error = await _failed_auth_error(
                err, rsp, details, bad_credentials=bad_creds
            )

            if isinstance(error, exc.BadUserCredentialsError):
                hint: str | None = HINT_BAD_CREDS
            else:
                hint = ERR_MSG_LOOKUP_BASE.get(err.status)
            if hint:
                self._logger.error(hint)  # noqa: TRY400

            raise error from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            self._logger.error(HINT_CHECK_NETWORK)  # noqa: TRY400

            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}",
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
