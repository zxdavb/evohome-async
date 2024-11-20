#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import base64
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Generator
from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, TypedDict

import aiohttp
import voluptuous as vol

from . import exceptions as exc
from .schemas import convert_keys_to_snake_case, obfuscate as _obfuscate

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL

    from .schemas import _EvoDictT, _EvoSchemaT  # pragma: no cover


_APPLICATION_ID: Final = base64.b64encode(
    b"4a231089-d2b6-41bd-a5eb-16a0a422b999:"  # fmt: off
    b"1a15cdb8-42de-407b-add0-059f92c530cb"
).decode("utf-8")

HOSTNAME: Final = "tccna.honeywell.com"

HEADERS_AUTH = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
    "Authorization": "Basic " + _APPLICATION_ID,
}
HEADERS_BASE = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "",  # falsey value will invoke get_access_token()
}

SZ_USERNAME: Final = "Username"
SZ_PASSWORD: Final = "Password"

SZ_ACCESS_TOKEN: Final = "access_token"
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"
SZ_EXPIRES_IN: Final = "expires_in"
SZ_REFRESH_TOKEN: Final = "refresh_token"


SCH_OAUTH_TOKEN: Final = vol.Schema(
    {
        vol.Required(SZ_ACCESS_TOKEN): vol.All(str, _obfuscate),
        vol.Required(SZ_EXPIRES_IN): int,  # 1800 seconds
        vol.Required(SZ_REFRESH_TOKEN): vol.All(str, _obfuscate),
        vol.Required("token_type"): str,
        vol.Optional("scope"): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
    }
)

CREDS_REFRESH_TOKEN: Final = {
    "grant_type": "refresh_token",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
    "refresh_token": "",
}

CREDS_USER_PASSWORD: Final = {
    "grant_type": "password",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # EMEA-V1-Get-Current-User-Account",
    "Username": "",
    "Password": "",
}


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both url_auth & url_base
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}

_ERR_MSG_LOOKUP_AUTH: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # POST url_auth
    HTTPStatus.BAD_REQUEST: "Invalid user credentials (check the username/password)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid URL?)",
    HTTPStatus.UNAUTHORIZED: "Invalid access token (dev/test only)",
}

_ERR_MSG_LOOKUP_BASE: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # GET/PUT url_base
    HTTPStatus.BAD_REQUEST: "Bad request (invalid data/json?)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid entity type?)",
    HTTPStatus.UNAUTHORIZED: "Unauthorized (expired access token/unknown entity id?)",
}


class AuthTokensT(TypedDict):
    access_token: str
    access_token_expires: str  # dt.isoformat()
    refresh_token: str


class AuthTokenResponseT(TypedDict):
    access_token: str
    expires_in: int  # number of seconds
    refresh_token: str


class AbstractTokenManager(ABC):
    """An ABC for managing the auth tokens used for HTTP authentication."""

    _access_token: str
    _access_token_expires: dt
    _refresh_token: str

    def __init__(
        self,
        client_id: str,
        secret: str,
        websession: aiohttp.ClientSession,
        /,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the token manager."""

        self._client_id = client_id
        self._secret = secret
        self._websession = websession

        self._hostname = _hostname or HOSTNAME
        self._logger = logger or logging.getLogger(__name__)

        # set True once the credentials are validated the first time
        self._was_authenticated = False

        # the following is specific to auth tokens (vs session id)...
        self._clear_auth_tokens()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(client_id='{self.client_id}')"

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    def _clear_auth_tokens(self) -> None:
        """Clear the auth tokens."""

        self._access_token = ""
        self._access_token_expires = dt.min
        self._refresh_token = ""

    @property
    def refresh_token(self) -> str:
        """Return the refresh token."""
        return self._refresh_token

    @property
    def access_token(self) -> str:
        """Return the access token."""
        return self._access_token

    @property
    def access_token_expires(self) -> dt:
        """Return the expiration datetime of the access token."""
        return self._access_token_expires

    def is_access_token_valid(self) -> bool:
        """Return True if the access token is valid."""
        return self.access_token_expires > dt.now() + td(seconds=15)

    @abstractmethod
    async def save_access_token(self) -> None:
        """Save the (serialized) authentication tokens to a cache."""

    def _import_auth_tokens(self, tokens: AuthTokensT) -> None:
        """Deserialize the token data from a dictionary."""
        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _export_auth_tokens(self) -> AuthTokensT:
        """Serialize the token data to a dictionary."""
        return {
            SZ_ACCESS_TOKEN: self._access_token,
            SZ_ACCESS_TOKEN_EXPIRES: self._access_token_expires.isoformat(),
            SZ_REFRESH_TOKEN: self._refresh_token,
        }

    async def get_access_token(self) -> str:
        """Return a valid access token.

        If required, fetch a new token via the vendor's web API.
        """

        if not self.is_access_token_valid():  # may be invalid for other reasons
            self._logger.warning(
                "Missing/Expired/Invalid access_token, re-authenticating."
            )
            await self._update_access_token()

        return self.access_token

    async def _update_access_token(self) -> None:
        """Update the access token and save it to the store/cache."""

        if self._refresh_token:
            self._logger.warning("Authenticating with the refresh_token...")

            credentials = {SZ_REFRESH_TOKEN: self.refresh_token}

            try:
                await self._request_access_token(CREDS_REFRESH_TOKEN | credentials)

            except exc.AuthenticationFailedError as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # e.g. invalid tokens
                    raise

                self._logger.warning(" - invalid/expired refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            self._logger.warning("Authenticating with username/password...")

            credentials = {SZ_USERNAME: self._client_id, SZ_PASSWORD: self._secret}

            # allow underlying exceptions through (as client_id/secret invalid)...
            await self._request_access_token(CREDS_USER_PASSWORD | credentials)
            self._was_authenticated = True

        await self.save_access_token()

        self._logger.debug(f" - access_token = {self.access_token}")
        self._logger.debug(f" - access_token_expires = {self.access_token_expires}")
        self._logger.debug(f" - refresh_token = {self.refresh_token}")

    async def _request_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using the supplied credentials.

        The credentials are either a refresh token or the user's client_id/secret.
        """

        url = f"https://{self._hostname}/Auth/OAuth/Token"

        response: AuthTokenResponseT = await self._post_access_token_request(
            url, headers=HEADERS_AUTH, data=credentials
        )

        try:  # the dict _should_ be the expected schema...
            SCH_OAUTH_TOKEN(response)  # can't use this result, due to obsfucation

        except vol.Invalid as err:
            self._logger.debug(f"Response JSON may be invalid: POST {url}: {err}")

        try:
            self._access_token = response[SZ_ACCESS_TOKEN]
            self._access_token_expires = dt.now() + td(seconds=response[SZ_EXPIRES_IN])
            self._refresh_token = response[SZ_REFRESH_TOKEN]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Invalid response from server: {err}"
            ) from err

        # if response.get(SZ_LATEST_EULA_ACCEPTED):

    async def _post_access_token_request(
        self, url: StrOrURL, **kwargs: Any
    ) -> AuthTokenResponseT:
        """Obtain an access token via a POST to the vendor's web API.

        Raise AuthenticationFailedError if unable to obtain an access token.
        """

        try:
            async with self._websession.post(url, **kwargs) as rsp:
                rsp.raise_for_status()

                self._was_authenticated = True  # i.e. the credentials are valid
                return await rsp.json()  # type: ignore[no-any-return]

        except aiohttp.ContentTypeError as err:
            # <title>Authorize error <h1>Authorization failed
            # <p>The authorization server have encoutered an error while processing...  # codespell:ignore encoutered
            content = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Server response is not JSON: POST {url}: {content}"
            ) from err

        except aiohttp.ClientResponseError as err:
            hint = _ERR_MSG_LOOKUP_AUTH.get(err.status) or str(err)
            raise exc.AuthenticationFailedError(hint, status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class _RequestContextManager:
    """A context manager for an aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        access_token_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ):
        """Initialize the request context manager."""

        self._get_access_token = access_token_getter
        self.websession = websession
        self.method = method
        self.url = url
        self.kwargs = kwargs

    async def __aenter__(self) -> aiohttp.ClientResponse:
        """Async context manager entry."""
        self._response = await self._await_impl()
        return self._response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if self._response:
            self._response.release()
            await self._response.wait_for_close()

    def __await__(self) -> Generator[Any, Any, aiohttp.ClientResponse]:
        """Make this class awaitable."""
        return self._await_impl().__await__()

    async def _await_impl(self) -> aiohttp.ClientResponse:
        """Make an aiohttp request to the vendor's servers.

        Will handle authorisation by inserting an access token into the header.
        """

        headers: dict[str, str] = self.kwargs.pop("headers", "") or HEADERS_BASE

        if not headers.get("Authorization"):
            headers["Authorization"] = "bearer " + await self._get_access_token()

        return await self.websession.request(
            self.method, self.url, headers=headers, **self.kwargs
        )


class Auth:
    """A class for interacting with the Resideo TCC API."""

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str = HOSTNAME,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v2 Resideo TCC API."""

        self._token_manager = token_manager
        self._websession: Final = websession
        self._hostname: Final = _hostname
        self._logger: Final = logger or logging.getLogger(__name__)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(base='{self._url_base}')"

    @property
    def _url_base(self) -> StrOrURL:
        """Return the URL base used for GET/PUT."""
        return f"https://{self._hostname}/WebAPI/emea/api/v1/"

    async def get(self, url: StrOrURL, schema: vol.Schema | None = None) -> _EvoSchemaT:
        """Call the Resideo TCC API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        content: _EvoSchemaT

        content = await self.request(  # type: ignore[assignment]
            HTTPMethod.GET, f"{self._url_base}/{url}"
        )

        if schema:
            try:
                content = schema(content)
            except vol.Invalid as err:
                self._logger.warning(f"Response JSON may be invalid: GET {url}: {err}")

        return content

    async def put(
        self,
        url: StrOrURL,
        json: _EvoDictT,
        schema: vol.Schema | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the vendor's API with a PUT.

        Optionally checks the payload JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        content: dict[str, Any] | list[dict[str, Any]]

        if schema:
            try:
                schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"Payload JSON may be invalid: PUT {url}: {err}")

        content = await self.request(  # type: ignore[assignment]
            HTTPMethod.PUT, f"{self._url_base}/{url}", json=json
        )

        return content

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Resideo TCC RESTful API.

        Converts keys to/from snake_case as required.
        """

        # TODO: if method == HTTPMethod.PUT and "json" in kwargs:
        #     kwargs["json"] = convert_keys_to_camel_case(kwargs["json"])

        content = await self._request(method, url, **kwargs)

        if method == HTTPMethod.GET:
            return convert_keys_to_snake_case(content)
        return content

    async def _request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Resideo TCC RESTful API.

        Checks for ClientErrors and handles Auth failures appropriately.

        Handles when auth tokens are rejected by server (i.e. not expired, but otherwise
        deemed invalid by the server).
        """

        async def _content(
            response: aiohttp.ClientResponse,
        ) -> dict[str, Any] | list[dict[str, Any]] | str:
            """Return the content of the response."""

            if not response.content_length:
                raise exc.RequestFailedError(
                    f"Invalid response (no content): {response}"
                )

            if response.content_type != "application/json":
                # assume "text/plain" or "text/html"
                return await response.text()

            content: dict[str, Any] = await response.json()
            return content

        def _raise_for_status(response: aiohttp.ClientResponse) -> None:
            """Raise an exception if the response is not OK."""

            try:
                response.raise_for_status()

            except aiohttp.ClientResponseError as err:
                if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                    raise exc.RequestFailedError(hint, status=err.status) from err
                raise exc.RequestFailedError(str(err), status=err.status) from err

            except aiohttp.ClientError as err:  # e.g. ClientConnectionError
                raise exc.RequestFailedError(str(err)) from err

        # async with self._raw_request(method, url, **kwargs) as rsp:
        #     if rsp.status == HTTPStatus.OK:
        #         return await _content(rsp)

        #     if (  # if 401/unauthorized, refresh access token and retry
        #         rsp.status != HTTPStatus.UNAUTHORIZED
        #         or rsp.content_type != "application/json"
        #     ):
        #         _raise_for_status(rsp)

        #     response_json = await rsp.json()
        #     try:
        #         if response_json[0]["code"] == "Unauthorized":
        #             pass
        #     except LookupError:
        #         _raise_for_status(rsp)

        # if self._token_manager.is_access_token_valid():
        #     self._logger.warning("access token was rejected, will clear it and retry")

        # self._token_manager._clear_auth_tokens()  # TODO: private method

        async with self._raw_request(method, url, **kwargs) as rsp:
            _raise_for_status(rsp)

            return await _content(rsp)

    def _raw_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> _RequestContextManager:
        """Return a context handler that can make the request."""

        return _RequestContextManager(
            self._token_manager.get_access_token,
            self._websession,
            method,
            url,
            **kwargs,
        )
