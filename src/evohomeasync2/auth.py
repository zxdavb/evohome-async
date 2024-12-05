#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import base64
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import voluptuous as vol

from evohome.auth import HOSTNAME, AbstractAuth, AbstractRequestContextManager
from evohome.helpers import convert_keys_to_snake_case, obfuscate

from . import exceptions as exc

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiohttp.typedefs import StrOrURL

    from .schemas.typedefs import (
        EvoAuthTokensDictT as AccessTokenEntryT,
        TccAuthTokensResponseT as AuthTokenResponseT,
    )


_APPLICATION_ID: Final = base64.b64encode(
    b"4a231089-d2b6-41bd-a5eb-16a0a422b999:"  # fmt: off
    b"1a15cdb8-42de-407b-add0-059f92c530cb"
).decode("utf-8")

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

SZ_ACCESS_TOKEN: Final = "access_token"
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"
SZ_EXPIRES_IN: Final = "expires_in"
SZ_REFRESH_TOKEN: Final = "refresh_token"


SCH_OAUTH_TOKEN: Final = vol.Schema(
    {
        vol.Required(SZ_ACCESS_TOKEN): vol.All(str, obfuscate),
        vol.Required(SZ_EXPIRES_IN): int,  # 1800 seconds
        vol.Required(SZ_REFRESH_TOKEN): vol.All(str, obfuscate),
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
        self._clear_access_token()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(client_id='{self.client_id}')"

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    def _clear_access_token(self) -> None:
        """Clear the auth tokens."""

        self._access_token = ""
        self._access_token_expires = dt.min.replace(tzinfo=UTC)
        self._refresh_token = ""  # TODO: remove this?

    @property
    def access_token(self) -> str:
        """Return the access token."""
        return self._access_token

    @property
    def access_token_expires(self) -> dt:
        """Return the expiration datetime of the access token."""
        return self._access_token_expires

    @property
    def refresh_token(self) -> str:
        """Return the refresh token."""
        return self._refresh_token

    def is_access_token_valid(self) -> bool:
        """Return True if the access token is valid."""
        return self._access_token_expires > dt.now(tz=UTC) + td(seconds=15)

    @abstractmethod
    async def save_access_token(self) -> None:
        """Save the (serialized) authentication tokens to a cache."""

    def _import_access_token(self, tokens: AccessTokenEntryT) -> None:
        """Deserialize the token data from a dictionary."""
        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _export_access_token(self) -> AccessTokenEntryT:
        """Serialize the token data to a dictionary."""
        return {
            SZ_ACCESS_TOKEN_EXPIRES: self._access_token_expires.isoformat(),
            SZ_ACCESS_TOKEN: self._access_token,
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

            credentials = {SZ_REFRESH_TOKEN: self._refresh_token}

            try:
                await self._request_access_token(CREDS_REFRESH_TOKEN | credentials)

            except exc.AuthenticationFailedError as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # 400, e.g. invalid tokens
                    raise

                self._logger.warning(" - invalid/expired refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            self._logger.warning("Authenticating with username/password...")

            # NOTE: the keys are case-sensitive: 'Username' and 'Password'
            credentials = {"Username": self._client_id, "Password": self._secret}

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
            url,
            headers=HEADERS_AUTH,
            data=credentials,  # NOTE: is snake_case
        )

        try:  # the dict _should_ be the expected schema...
            self._logger.debug(f"POST {url}: {SCH_OAUTH_TOKEN(response)}")

        except vol.Invalid as err:
            self._logger.warning(f"Response JSON may be invalid: POST {url}: {err}")

        tokens: AuthTokenResponseT = convert_keys_to_snake_case(response)

        try:
            self._access_token = tokens[SZ_ACCESS_TOKEN]
            self._access_token_expires = dt.now(tz=UTC) + td(
                seconds=tokens[SZ_EXPIRES_IN]
            )
            self._refresh_token = tokens[SZ_REFRESH_TOKEN]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Invalid response from server: {err}"
            ) from err

        # if response.get(SZ_LATEST_EULA_ACCEPTED):

    async def _post_access_token_request(  # no method, as POST only
        self, url: StrOrURL, /, **kwargs: Any
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
            response = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Server response is not JSON: POST {url}: {response}"
            ) from err

        except aiohttp.ClientResponseError as err:
            hint = _ERR_MSG_LOOKUP_AUTH.get(err.status) or str(err)
            raise exc.AuthenticationFailedError(hint, status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class _RequestContextManager(AbstractRequestContextManager):
    """A context manager for authorized aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        access_token_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ) -> None:
        """Initialize the request context manager."""
        super().__init__(websession, method, url, **kwargs)

        self._get_access_token = access_token_getter

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


class Auth(AbstractAuth):
    """A class for interacting with the v2 Resideo TCC API."""

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v2 Resideo TCC API."""
        super().__init__(websession, _hostname=_hostname, logger=logger)

        self._url_base = f"https://{self._hostname}/WebAPI/emea/api/v1/"
        self._token_manager = token_manager

    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        """Raise an exception if the response is not OK."""

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                raise exc.RequestFailedError(hint, status=err.status) from err
            raise exc.RequestFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.RequestFailedError(str(err)) from err

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
