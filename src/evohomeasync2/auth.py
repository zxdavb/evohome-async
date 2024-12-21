"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import base64
import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import voluptuous as vol

from evohome.auth import _ERR_MSG_LOOKUP_BOTH, HOSTNAME, AbstractAuth
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

SZ_ACCESS_TOKEN: Final = "access_token"  # noqa: S105
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"  # noqa: S105
SZ_EXPIRES_IN: Final = "expires_in"
SZ_REFRESH_TOKEN: Final = "refresh_token"  # noqa: S105


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


# POST url_auth, authentication url (i.e. /Auth/OAuth/Token)
_ERR_MSG_LOOKUP_AUTH: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {
    HTTPStatus.BAD_REQUEST: "Invalid user credentials (check the username/password)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid URL?)",
    HTTPStatus.UNAUTHORIZED: "Invalid access token (dev/test only?)",
}
URL_AUTH: Final = "Auth/OAuth/Token"

# GET/PUT url_base, authorization url (e.g. /"WebAPI/emea/api/v1/...)
_ERR_MSG_LOOKUP_BASE: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {
    HTTPStatus.BAD_REQUEST: "Bad request (invalid data/json?)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid entity type?)",
    HTTPStatus.UNAUTHORIZED: "Unauthorized (expired access token/unknown entity id?)",
}
URL_BASE: Final = "WebAPI/emea/api/v1"


class AbstractTokenManager(ABC):
    """An ABC for managing the auth tokens used for HTTP authentication."""

    _access_token: str
    _access_token_expires: dt
    _refresh_token: str = ""

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
        self.websession = websession

        self.hostname = _hostname or HOSTNAME
        self.logger = logger or logging.getLogger(__name__)

        self._was_authenticated = False  # True once credentials are proven validated

        self._clear_access_token()

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(client_id='{self.client_id}, hostname='{self.hostname}')"
        )

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    def _clear_access_token(self) -> None:
        """Clear the auth tokens (set to falsey state)."""

        self._access_token = ""
        self._access_token_expires = dt.min.replace(tzinfo=UTC)  # don't need local TZ

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
            self.logger.warning("Null/Expired/Invalid access_token, re-authenticating.")
            await self._update_access_token()

        return self.access_token

    async def _update_access_token(self) -> None:
        """Update the access token and save it to the store/cache."""

        if self._refresh_token:
            self.logger.warning("Authenticating with the refresh_token...")

            credentials = {SZ_REFRESH_TOKEN: self._refresh_token}

            try:
                await self._request_access_token(CREDS_REFRESH_TOKEN | credentials)

            except exc.AuthenticationFailedError as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # 400, e.g. invalid tokens
                    raise

                self.logger.warning(" - expired/invalid refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            self.logger.warning("Authenticating with client_id/secret...")

            # NOTE: the keys are case-sensitive: 'Username' and 'Password'
            credentials = {"Username": self._client_id, "Password": self._secret}

            # allow underlying exceptions through (as client_id/secret invalid)...
            await self._request_access_token(CREDS_USER_PASSWORD | credentials)
            self._was_authenticated = True

        await self.save_access_token()

        self.logger.debug(f" - access_token = {self.access_token}")
        self.logger.debug(f" - access_token_expires = {self.access_token_expires}")
        self.logger.debug(f" - refresh_token = {self.refresh_token}")

    async def _request_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using the supplied credentials.

        The credentials are either a refresh token or the user's client_id/secret.
        """

        url = f"https://{self.hostname}/{URL_AUTH}"

        response: AuthTokenResponseT = await self._post_access_token_request(
            url,
            headers=HEADERS_AUTH,
            data=credentials,  # NOTE: is snake_case
        )

        try:  # the dict _should_ be the expected schema...
            self.logger.debug(  # tokens will be obfuscated
                f"POST {url}: {SCH_OAUTH_TOKEN(response)}"
            )

        except vol.Invalid as err:
            self.logger.warning(
                f"Authenticator response may be invalid: POST {url}: {err}"
            )

        tokens: AuthTokenResponseT = convert_keys_to_snake_case(response)

        try:
            self._access_token = tokens[SZ_ACCESS_TOKEN]
            self._access_token_expires = dt.now(tz=UTC) + td(
                seconds=tokens[SZ_EXPIRES_IN]
            )
            self._refresh_token = tokens[SZ_REFRESH_TOKEN]

        except (KeyError, TypeError) as err:
            self.logger.error(f"Authenticator response is invalid: {tokens}")  # noqa: TRY400
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}"
            ) from err

        self._was_authenticated = True  # i.e. the credentials are valid

        # if response.get(SZ_LATEST_EULA_ACCEPTED):

    async def _post_access_token_request(  # no method, as POST only
        self, url: StrOrURL, /, **kwargs: Any
    ) -> AuthTokenResponseT:
        """Obtain an access token via a POST to the vendor's web API.

        Raise AuthenticationFailedError if unable to obtain an access token.
        """

        try:
            async with self.websession.post(url, **kwargs) as rsp:
                rsp.raise_for_status()

                if (response := await rsp.json()) is None:  # an unexpected edge-case
                    raise exc.AuthenticationFailedError(
                        f"Authenticator response is null: POST {url}"
                    )
                return response  # type: ignore[no-any-return]

        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            # <title>Authorize error <h1>Authorization failed
            # <p>The authorization server have encoutered an error while processing...  # codespell:ignore encoutered
            response = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Authenticator response is not JSON: POST {url}: {response}"
            ) from err

        except aiohttp.ClientResponseError as err:
            hint = _ERR_MSG_LOOKUP_AUTH.get(err.status) or str(err)
            raise exc.AuthenticationFailedError(hint, status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class Auth(AbstractAuth):
    """A class for interacting with the v2 Resideo TCC API."""

    def __init__(
        self,
        access_token_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v2 Resideo TCC API."""
        super().__init__(websession, _hostname=_hostname, logger=logger)

        self._url_base = f"https://{self.hostname}/{URL_BASE}"
        self._get_access_token = access_token_getter

    async def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Ensure the authorization header has a valid access token."""
        return (headers or HEADERS_BASE) | {
            "Authorization": "bearer " + await self._get_access_token()
        }

    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        """Raise an exception if the response is not < 400."""

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                raise exc.ApiRequestFailedError(hint, status=err.status) from err
            raise exc.ApiRequestFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.ApiRequestFailedError(str(err)) from err
