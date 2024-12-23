"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import voluptuous as vol

from evohome import exceptions as exc
from evohome.helpers import (
    convert_keys_to_camel_case,
    convert_keys_to_snake_case,
    obscure_secrets,
)

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL


HOSTNAME: Final = "tccna.resideo.com"

# No need to indicate "Content-Type" as default is "charset=utf-8", with:
# - POST: "Content-Type": "application/json"                  (default)
# - GETs: "Content-Type": "application/x-www-form-urlencoded" (not required)
# - PUTs: "Content-Type": "application/json"                  (as used here)

HEADERS_BASE = {
    "Accept": "application/json",
    "Connection": "Keep-Alive",
}
HEADERS_CRED = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
}


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both url_auth & url_base
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test only?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}


async def _payload(r: aiohttp.ClientResponse | None) -> str | None:
    if r is None:
        return None
    try:
        return await r.text()
    except aiohttp.ClientPayloadError:
        return None
    except aiohttp.ClientError:
        return None


class CredentialsManagerBase:
    """A base class for managing the credentials used for HTTP authentication."""

    def __init__(
        self,
        client_id: str,
        secret: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialise the session manager."""

        self._client_id = client_id
        self._secret = secret
        self.websession = websession

        self.hostname = _hostname or HOSTNAME
        self.logger = logger or logging.getLogger(__name__)

        self._was_authenticated = False  # True once credentials are proven validated

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(client_id='{self.client_id}, hostname='{self.hostname}')"
        )

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    async def _post_request(self, url: StrOrURL, /, **kwargs: Any) -> dict[str, Any]:
        """Make an authentication request to the Resideo TCC RESTful API.

        Raises an exception if the authentication is not successful.
        """

        rsp: aiohttp.ClientResponse | None = None

        try:
            rsp = await self.websession.post(url, **kwargs)
            assert rsp is not None  # mypy

            rsp.raise_for_status()

            # can't assert content_length != 0 with aioresponses, so skip that check
            if rsp.content_type != "application/json":  # usu. "text/plain", "text/html"
                raise exc.AuthenticationFailedError(
                    f"Authenticator response is not JSON: {await _payload(rsp)}"
                )

            if (response := await rsp.json()) is None:  # an unanticipated edge-case
                raise exc.AuthenticationFailedError("Authenticator response is null")

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is not JSON: {await _payload(rsp)}"
            ) from err

        except aiohttp.ClientResponseError as err:
            # if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
            #     raise exc.AuthenticationFailedError(hint, status=err.status) from err
            msg = f"{err.status} {err.message}, response={await _payload(rsp)}"
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {msg}", status=err.status
            ) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}",
            ) from err

        else:
            return response  # type: ignore[no-any-return]

        finally:
            if rsp is not None:
                rsp.release()


class AbstractAuth(ABC):
    """A class to provide to access the Resideo TCC API."""

    _url_base: StrOrURL

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the Resideo TCC API."""

        self.websession: Final = websession
        self.hostname: Final = _hostname or HOSTNAME
        self.logger: Final = logger or logging.getLogger(__name__)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(base='{self.url_base}')"

    @property
    def url_base(self) -> StrOrURL:
        """Return the URL base used for GET/PUT."""
        return self._url_base

    async def get(
        self, url: StrOrURL, /, schema: vol.Schema | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Call the vendor's TCC API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        response = await self.request(HTTPMethod.GET, url)

        if schema:
            try:
                response = schema(response)
            except vol.Invalid as err:
                self.logger.warning(f"GET {url}: payload may be invalid: {err}")

        return response  # type: ignore[return-value]

    async def put(
        self,
        url: StrOrURL,
        /,
        json: dict[str, Any],
        *,
        schema: vol.Schema | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the vendor's API with a PUT.

        Optionally checks the payload JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        if schema:
            try:
                schema(json)
            except vol.Invalid as err:
                self.logger.warning(f"PUT {url}: payload may be invalid: {err}")

        return await self.request(HTTPMethod.PUT, url, json=json)  # type: ignore[return-value]

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the vendor's TCC RESTful API.

        Converts keys to/from snake_case as required.
        """

        if method == HTTPMethod.PUT and "json" in kwargs:
            kwargs["json"] = convert_keys_to_camel_case(kwargs["json"])

        response = await self._make_request(method, url, **kwargs)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"{method} {url}: {obscure_secrets(response)}")

        if method == HTTPMethod.GET:
            return convert_keys_to_snake_case(response)
        return response

    @abstractmethod
    async def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Ensure the authorization header is valid.

        This could take the form of an access token, or a session id.
        """

    async def _make_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a GET/PUT request to the Resideo TCC RESTful API.

        Raises an exception if the request is not successful.
        """

        rsp: aiohttp.ClientResponse | None = None

        headers = await self._headers(kwargs.pop("headers", {}))

        try:
            rsp = await self.websession.request(
                method, f"{self.url_base}/{url}", headers=headers, **kwargs
            )
            assert rsp is not None  # mypy

            rsp.raise_for_status()

            # can't assert content_length != 0 with aioresponses, so skip that check
            if rsp.content_type != "application/json":  # usu. "text/plain", "text/html"
                raise exc.ApiRequestFailedError(
                    f"{method} {url}: response is not JSON: {await _payload(rsp)}"
                )

            if (response := await rsp.json()) is None:  # an unanticipated edge-case
                raise exc.ApiRequestFailedError(f"{method} {url}: response is null")

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise exc.ApiRequestFailedError(
                f"{method} {url}: response is not JSON: {await _payload(rsp)}"
            ) from err

        except aiohttp.ClientResponseError as err:
            # if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
            #     raise exc.ApiRequestFailedError(hint, status=err.status) from err
            msg = f"{err.status} {err.message}, response={await _payload(rsp)}"
            raise exc.ApiRequestFailedError(
                f"{method} {url}: {msg}", status=err.status
            ) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.ApiRequestFailedError(
                f"{method} {url}: {err}",
            ) from err

        else:
            return response  # type: ignore[no-any-return]

        finally:
            if rsp is not None:
                rsp.release()
