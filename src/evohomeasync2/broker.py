#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the updated Evohome API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, NotRequired, TypedDict

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
)
from .schema import (
    SCH_OAUTH_TOKEN,
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_EXPIRES_IN,
    SZ_REFRESH_TOKEN,
)

if TYPE_CHECKING:
    from . import EvohomeClient
    from .schema import _EvoDictT, _EvoListT, _EvoSchemaT


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


class OAuthTokenData(TypedDict):
    access_token: str
    expires_in: int  # number of seconds
    refresh_token: str


class _EvoTokenData(TypedDict):
    access_token: str
    access_token_expires: str  # dt.isoformat()
    refresh_token: str
    username: NotRequired[str]


class AbstractTokenManager(ABC):
    """Abstract class to manage an OAuth access token and its refresh token."""

    access_token: str
    access_token_expires: dt
    refresh_token: str

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
    ) -> None:
        """Initialize the token manager."""

        self._credentials = {
            "Username": username,
            "Password": password,
        }  # TODO: are only ever PascalCase?

        self.websession = websession

        self._token_data_reset()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(username='{self.username}')"

    @property
    def username(self) -> str:
        """Return the username."""
        return self._credentials["Username"]

    @property  # TODO: remove this whan no longer needed
    def _password(self) -> str:
        """Return the username."""
        return self._credentials["Password"]

    def _token_data_reset(self) -> None:
        self.access_token = ""
        self.access_token_expires = dt.min
        self.refresh_token = ""

    def _token_data_from_dict(self, tokens: _EvoTokenData) -> None:
        self.access_token = tokens[SZ_ACCESS_TOKEN]
        self.access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self.refresh_token = tokens[SZ_REFRESH_TOKEN]

    # HACK: sometimes using evo, not self
    def _token_data_as_dict(self, evo: EvohomeClient | None) -> _EvoTokenData:
        x = evo.broker if evo is not None else self  # TODO: remove evo

        return {
            SZ_ACCESS_TOKEN: x.access_token,  # type: ignore[misc]
            SZ_ACCESS_TOKEN_EXPIRES: x.access_token_expires.isoformat(),
            SZ_REFRESH_TOKEN: x.refresh_token,
        }

    async def is_token_data_valid(self) -> bool:
        """Return True if we have a valid access token."""
        return bool(self.access_token) and self.access_token_expires > dt.now()

    async def fetch_access_token(self) -> None:  # HA api
        """Ensure the access token is valid.

        If required, fetch a new token via the vendor's web API.
        """

        if self.is_token_data_valid():
            return

        _LOGGER.warning("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = ""
        self.access_token_expires = dt.min

        if self.refresh_token:
            _LOGGER.warning("Authenticating with the refresh_token...")
            credentials = {SZ_REFRESH_TOKEN: self.refresh_token}

            try:
                await self._obtain_access_token(**(CREDS_REFRESH_TOKEN | credentials))

            except exc.AuthenticationFailed as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # e.g. invalid tokens
                    raise

                _LOGGER.warning("Likely Invalid refresh_token, will try user_id/secret")
                self.refresh_token = ""

        if not self.refresh_token:
            _LOGGER.warning("Authenticating with username/password...")
            await self._obtain_access_token(**(CREDS_USER_PASSWORD | self._credentials))

        # await self.save_access_token()

        _LOGGER.warning(f"refresh_token = {self.refresh_token}")
        _LOGGER.warning(f"access_token = {self.access_token}")
        _LOGGER.warning(f"access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, **kwargs: Any) -> aiohttp.ClientResponse:
        """Obtain an access token via the vendor's web API.

        Use the refresh token, if able, otherwise utilize the user's credentials.
        """

        try:
            response = await self._request(HTTPMethod.POST, AUTH_URL, **kwargs)
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_AUTH.get(err.status):
                raise exc.AuthenticationFailed(hint, status=err.status) from err
            raise exc.AuthenticationFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailed(str(err)) from err

        if response.content_type != "application/json":  # or likely "text/html"
            # <title>Authorize error <h1>Authorization failed
            # <p>The authorization server have encoutered an error while processing...
            content = await response.text()
            raise exc.AuthenticationFailed(
                f"Server response is not JSON: {HTTPMethod.POST} {AUTH_URL}: {content}"
            )

        return response

    async def _request(
        self, method: HTTPMethod, url: str, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        # The credentials can be either a refresh token or username

        async with self.websession.request(
            method, url, headers=AUTH_HEADER, json=kwargs["credentials"]
        ) as response:
            return response

    @abstractmethod
    async def save_access_token(self) -> None:  # HA: api
        """Save the access token to a cache."""


class Broker:
    """A class for interacting with the Evohome API."""

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        session: aiohttp.ClientSession,
        logger: logging.Logger,
    ) -> None:
        """A class for interacting with the v2 Evohome API."""

        self._credentials = token_manager._credentials

        self.refresh_token = token_manager.refresh_token
        self.access_token = token_manager.access_token
        self.access_token_expires = token_manager.access_token_expires

        self.token_manager = token_manager
        self._session = session
        self._logger = logger

    async def _client(
        self,
        method: HTTPMethod,
        url: str,
        /,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> tuple[aiohttp.ClientResponse, None | str | _EvoDictT | _EvoListT]:
        """Wrapper for aiohttp.ClientSession()."""

        assert self._session is not None  # mypy hint

        if headers is None:
            headers = await self._headers()

        if method == HTTPMethod.GET:
            _session_method = self._session.get
            kwargs = {"headers": headers}

        elif method == HTTPMethod.POST:
            _session_method = self._session.post
            kwargs = {"headers": headers, "data": data}  # type: ignore[dict-item]

        elif method == HTTPMethod.PUT:
            _session_method = self._session.put
            # headers["Content-Type"] = "application/json"
            kwargs = {"headers": headers, "json": json}  # type: ignore[dict-item]

        async with _session_method(url, **kwargs) as response:  # type: ignore[arg-type]
            if not response.content_length:
                content = None
                _LOGGER.info(f"{method} {url} ({response.status}) = {content}")

            elif response.content_type == "application/json":
                content = await response.json()
                _LOGGER.info(f"{method} {url} ({response.status}) = {content}")

            else:  # assume "text/plain" or "text/html"
                content = await response.text()
                _LOGGER.info(f"{method} {url} ({response.status}) = {content}")

            return response, content  # FIXME: is messy to return response

    async def _headers(self) -> dict[str, str]:
        """Ensure the Authorization Header has a valid Access Token."""

        if not self.access_token or not self.access_token_expires:
            await self._basic_login()

        elif self.access_token_expires < dt.now():
            await self._basic_login()

        assert isinstance(self.access_token, str)  # mypy

        return {
            "Accept": AUTH_HEADER_ACCEPT,
            "Authorization": "bearer " + self.access_token,
            "Content-Type": "application/json",
        }

    async def _basic_login(self) -> None:
        """Obtain a new access token from the vendor (as it is invalid, or expired).

        First, try using the refresh token, if one is available, otherwise authenticate
        using the user credentials.
        """

        self._logger.debug("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = self.access_token_expires = None

        if self.refresh_token:
            self._logger.debug("Authenticating with the refresh_token...")
            credentials = {SZ_REFRESH_TOKEN: self.refresh_token}

            try:
                await self._obtain_access_token(CREDS_REFRESH_TOKEN | credentials)  # type: ignore[arg-type]

            except exc.AuthenticationFailed as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # e.g. invalid tokens
                    raise

                self._logger.warning(
                    "Likely Invalid refresh_token (will try username/password)"
                )
                self.refresh_token = None

        if not self.refresh_token:
            self._logger.debug("Authenticating with username/password...")
            await self._obtain_access_token(CREDS_USER_PASSWORD | self._credentials)  # type: ignore[arg-type]

        _LOGGER.debug(f"refresh_token = {self.refresh_token}")
        _LOGGER.debug(f"access_token = {self.access_token}")
        _LOGGER.debug(f"access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, credentials: dict[str, int | str]) -> None:
        """Obtain an access token using either the refresh token or user credentials."""

        response: aiohttp.ClientResponse
        content: dict[str, int | str]

        try:
            response, content = await self._client(  # type: ignore[assignment]
                HTTPMethod.POST,
                AUTH_URL,
                data=AUTH_PAYLOAD | credentials,
                headers=AUTH_HEADER,
            )
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_AUTH.get(err.status):
                raise exc.AuthenticationFailed(hint, status=err.status) from err
            raise exc.AuthenticationFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailed(str(err)) from err

        if response.content_type != "application/json":  # is likely "text/html"
            # <title>Authorize error <h1>Authorization failed
            # <p>The authorization server have encoutered an error while processing...
            raise exc.AuthenticationFailed(
                f"Invalid response from server: POST {AUTH_URL}: {content}"
            )

        try:  # the access token _should_ be valid...
            _ = SCH_OAUTH_TOKEN(content)  # can't use result, due to obsfucated values
        except vol.Invalid as err:
            self._logger.warning(
                f"Response JSON may be invalid: POST {AUTH_URL}: vol.Invalid({err})"
            )

        try:
            self.access_token = content[SZ_ACCESS_TOKEN]  # type: ignore[assignment]
            self.access_token_expires = (
                dt.now() + td(seconds=content[SZ_EXPIRES_IN] - 15)  # type: ignore[operator]
            )
            self.refresh_token = content[SZ_REFRESH_TOKEN]  # type: ignore[assignment]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailed(
                f"Invalid response from server: {err}"
            ) from err

    async def get(self, url: str, schema: vol.Schema | None = None) -> _EvoSchemaT:
        """Call the RESTful API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match (NB: does not raise a vol.Invalid).
        """

        response: aiohttp.ClientResponse
        content: _EvoSchemaT

        try:
            response, content = await self._client(  # type: ignore[assignment]
                HTTPMethod.GET, f"{URL_BASE}/{url}"
            )
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                raise exc.RequestFailed(hint, status=err.status) from err
            raise exc.RequestFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.RequestFailed(str(err)) from err

        if schema:
            try:
                content = schema(content)
            except vol.Invalid as err:
                self._logger.warning(
                    f"Response JSON may be invalid: GET {url}: vol.Invalid({err})"
                )

        return content

    async def put(
        self, url: str, json: _EvoDictT | str, schema: vol.Schema | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the RESTful API with a PUT.

        Optionally checks the request JSON against the expected schema and logs a
        warning if it doesn't match (NB: does not raise a vol.Invalid).
        """

        response: aiohttp.ClientResponse
        content: dict[str, Any] | list[dict[str, Any]]

        if schema:
            try:
                _ = schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"Request JSON may be invalid: PUT {url}: {err}")

        try:
            response, content = await self._client(  # type: ignore[assignment]
                HTTPMethod.PUT,
                f"{URL_BASE}/{url}",
                json=json,  # type: ignore[arg-type]
            )
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                raise exc.RequestFailed(hint, status=err.status) from err
            raise exc.RequestFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.RequestFailed(str(err)) from err

        return content
