#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the updated Evohome TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, TypedDict

import aiohttp
import voluptuous as vol

from . import exceptions as exc
from .const import (
    AUTH_HEADER,
    AUTH_HEADER_ACCEPT,
    AUTH_PAYLOAD,
    AUTH_URL,
    CREDS_REFRESH_TOKEN,
    CREDS_USER_PASSWORD,
    URL_BASE,
    URL_HOST,
)
from .schema import (
    SCH_OAUTH_TOKEN,
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_EXPIRES_IN,
    SZ_REFRESH_TOKEN,
)

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL

    from .schema import _EvoDictT, _EvoSchemaT  # pragma: no cover


_LOGGER: Final = logging.getLogger(__name__)


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both OAUTH_URL & URL_BASE
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}

_ERR_MSG_LOOKUP_AUTH: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # POST OAUTH_URL
    HTTPStatus.BAD_REQUEST: "Invalid user credentials (check the username/password)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid URL?)",
    HTTPStatus.UNAUTHORIZED: "Invalid access token (dev/test only)",
}

_ERR_MSG_LOOKUP_BASE: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # GET/PUT URL_BASE
    HTTPStatus.BAD_REQUEST: "Bad request (invalid data/json?)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid entity type?)",
    HTTPStatus.UNAUTHORIZED: "Unauthorized (expired access token/unknown entity id?)",
}

SZ_USERNAME: Final = "Username"  # TODO: is camelCase (and not PascalCase) OK?
SZ_PASSWORD: Final = "Password"


class OAuthTokenData(TypedDict):
    access_token: str
    expires_in: int  # number of seconds
    refresh_token: str


class _EvoTokenData(TypedDict):
    access_token: str
    access_token_expires: str  # dt.isoformat()
    refresh_token: str


class AbstractTokenManager(ABC):
    """Abstract class to manage an OAuth access token and its refresh token."""

    _access_token: str
    _access_token_expires: dt
    _refresh_token: str

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
    ) -> None:
        """Initialize the token manager."""

        self._user_credentials = {
            SZ_USERNAME: username,
            SZ_PASSWORD: password,
        }

        self.websession = websession

        self._auth_tokens_clear()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(username='{self.username}')"

    @property
    def access_token(self) -> str:
        """Return the access_token."""
        return self._access_token

    @property
    def access_token_expires(self) -> dt:
        """Return the access_token_expires."""
        return self._access_token_expires

    @property
    def refresh_token(self) -> str:
        """Return the refresh_token."""
        return self._refresh_token

    @property
    def username(self) -> str:
        """Return the username."""
        return self._user_credentials[SZ_USERNAME]

    def _auth_tokens_clear(self) -> None:
        """Reset the token data to its falsy state."""
        self._access_token = ""
        self._access_token_expires = dt.min
        self._refresh_token = ""

    def _auth_tokens_from_api(self, tokens: OAuthTokenData) -> None:
        """Convert the token data from the vendor's API to the internal format."""
        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.now() + td(seconds=tokens[SZ_EXPIRES_IN])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _deserialize_auth_tokens(self, tokens: _EvoTokenData) -> None:
        """Deserialize the token data from a dictionary."""
        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _serialize_auth_tokens(self) -> _EvoTokenData:
        """Serialize the token data to a dictionary."""
        return {
            SZ_ACCESS_TOKEN: self.access_token,
            SZ_ACCESS_TOKEN_EXPIRES: self.access_token_expires.isoformat(),
            SZ_REFRESH_TOKEN: self.refresh_token,
        }

    def is_token_data_valid(self) -> bool:
        """Return True if we have a valid access token."""
        return bool(self.access_token) and self.access_token_expires > dt.now()

    async def get_access_token(self) -> str:
        """Return a valid access token.

        If required, fetch a new token via the vendor's web API.
        """

        if not self.is_token_data_valid():  # TODO: but may be invalid for other reasons
            _LOGGER.warning("Missing/Expired/Invalid access_token, re-authenticating.")
            await self._update_access_token()

        return self.access_token

    async def _update_access_token(self) -> None:
        """Update the access token and save it to the store/cache."""

        if self._refresh_token:
            _LOGGER.warning("Authenticating with the refresh_token...")

            try:
                await self._obtain_access_token(
                    CREDS_REFRESH_TOKEN | {SZ_REFRESH_TOKEN: self.refresh_token}
                )

            except exc.AuthenticationFailed as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # e.g. invalid tokens
                    raise

                _LOGGER.warning(" - invalid/expired refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            _LOGGER.warning("Authenticating with username/password...")

            await self._obtain_access_token(
                CREDS_USER_PASSWORD | self._user_credentials
            )

        await self.save_access_token()

        _LOGGER.debug(f" - refresh_token = {self.refresh_token}")
        _LOGGER.debug(f" - access_token = {self.access_token}")
        _LOGGER.debug(f" - access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using the supplied credentials.

        The credentials are either a refresh token or the client_id/secret.
        """

        token_data = await self._post_access_token_request(
            AUTH_URL,
            data=AUTH_PAYLOAD | credentials,
            headers=AUTH_HEADER,
        )

        try:  # the access token _should_ be valid...
            _ = SCH_OAUTH_TOKEN(token_data)  # can't use this result, due to obsfucation
        except vol.Invalid as err:
            _LOGGER.warning(
                f"Response JSON may be invalid: POST {AUTH_URL}: vol.Invalid({err})"
            )

        try:
            self._auth_tokens_from_api(token_data)

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailed(
                f"Invalid response from server: {err}"
            ) from err

    async def _post_access_token_request(
        self, url: str, **kwargs: Any
    ) -> OAuthTokenData:
        """Obtain an access token via the vendor's web API."""

        try:
            async with self.websession.post(url, **kwargs) as response:
                response.raise_for_status()

                return await response.json()  # type: ignore[no-any-return]

        except aiohttp.ContentTypeError as err:
            # <title>Authorize error <h1>Authorization failed
            # <p>The authorization server have encoutered an error while processing...  # codespell:ignore encoutered
            content = await response.text()
            raise exc.AuthenticationFailed(
                f"Server response is not JSON: {HTTPMethod.POST} {AUTH_URL}: {content}"
            ) from err

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_AUTH.get(err.status):
                raise exc.AuthenticationFailed(hint, status=err.status) from err
            raise exc.AuthenticationFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailed(str(err)) from err

    @abstractmethod
    async def save_access_token(self) -> None:  # HA: api
        """Save the access token to a cache."""


class AbstractAuth(ABC):  # APIs esposed by/for HA
    def __init__(self, websession: aiohttp.ClientSession, host: str) -> None:
        """Initialize the auth."""
        self.websession = websession
        self.host = host

    @abstractmethod
    async def get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(  # type: ignore[no-untyped-def]
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ):
        """Make a request to the Evohome TCC API."""

        headers = kwargs.pop("headers", None) or {
            "Accept": AUTH_HEADER_ACCEPT,
            "Content-Type": "application/json",
        }
        headers["Authorization"] = "bearer " + await self.get_access_token()

        return self.websession.request(method, url, **kwargs, headers=headers)


class Auth(AbstractAuth):
    """A class for interacting with the Evohome TCC API."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        token_manager: AbstractTokenManager,
        logger: logging.Logger,
    ) -> None:
        """A class for interacting with the v2 Evohome TCC API."""

        super().__init__(websession, URL_HOST)

        self.token_manager = token_manager
        self._logger = logger

    async def get_access_token(self) -> str:
        """Return a valid access token."""
        return await self.token_manager.get_access_token()

    async def _request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Evohome TCC API."""

        async with await self.request(method, url, **kwargs) as response:
            try:
                response.raise_for_status()

            except aiohttp.ClientResponseError as err:
                if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                    raise exc.RequestFailed(hint, status=err.status) from err
                raise exc.RequestFailed(str(err), status=err.status) from err

            except aiohttp.ClientError as err:  # e.g. ClientConnectionError
                raise exc.RequestFailed(str(err)) from err

            return await self._content(response)

    @staticmethod
    async def _content(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Return the content of the response."""

        if not response.content_length:
            return None

        if response.content_type != "application/json":
            # assume "text/plain" or "text/html"
            return await response.text()

        content: dict[str, Any] = await response.json()
        return content

    async def get(self, url: StrOrURL, schema: vol.Schema | None = None) -> _EvoSchemaT:
        """Call the Evohome TCC API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match (NB: does not raise a vol.Invalid).
        """

        content: _EvoSchemaT

        content = await self._request(  # type: ignore[assignment]
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )

        if schema:
            try:
                content = schema(content)
            except vol.Invalid as err:
                self._logger.warning(
                    f"Response JSON may be invalid: GET {url}: vol.Invalid({err})"
                )

        return content

    async def put(
        self, url: StrOrURL, json: _EvoDictT | str, schema: vol.Schema | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the Evohome TCC API with a PUT (POST is only used for authentication).

        Optionally checks the request JSON against the expected schema and logs a
        warning if it doesn't match (NB: does not raise a vol.Invalid).
        """

        content: dict[str, Any] | list[dict[str, Any]]

        if schema:
            try:
                _ = schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"Request JSON may be invalid: PUT {url}: {err}")

        content = await self._request(  # type: ignore[assignment]
            HTTPMethod.PUT, f"{URL_BASE}/{url}", json=json
        )

        return content
