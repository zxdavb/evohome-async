"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import voluptuous as vol

from evohome.auth import AbstractAuth
from evohome.const import HEADERS_BASE, HEADERS_CRED, HINT_BAD_CREDS
from evohome.credentials import CredentialsManagerBase
from evohome.helpers import convert_keys_to_snake_case, obfuscate

from . import exceptions as exc

if TYPE_CHECKING:
    import logging

    import aiohttp
    from aiohttp.typedefs import StrOrURL

    from .schemas.typedefs import (
        EvoAuthTokensDictT as AccessTokenEntryT,
        TccAuthTokensResponseT as AuthTokenResponseT,  # TCC is snake_case anyway
    )


_APPLICATION_ID: Final = base64.b64encode(
    b"4a231089-d2b6-41bd-a5eb-16a0a422b999:"  # fmt: off
    b"1a15cdb8-42de-407b-add0-059f92c530cb"
).decode("utf-8")


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


# POST authentication url (i.e. /Auth/OAuth/Token)
URL_CRED: Final = "Auth/OAuth/Token"

# GET/PUT resource url (e.g. /WebAPI/emea/api/v1/...)
URL_BASE: Final = "WebAPI/emea/api/v1"


class AbstractTokenManager(CredentialsManagerBase, ABC):
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

        super().__init__(
            client_id, secret, websession, _hostname=_hostname, logger=logger
        )
        self._clear_access_token()  # initialise the attrs

    def _clear_access_token(self) -> None:
        """Clear the auth tokens attrs (set to falsey state)."""

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

    async def get_access_token(self) -> str:  # convenience wrapper
        """Return a valid access token.

        If required, fetch (and save) a new token via the vendor's web API.
        """

        if not self.is_token_valid():  # although may be rejected for other reasons
            await self.fetch_access_token()
            await self.save_access_token()

        return self.access_token

    def is_token_valid(self) -> bool:
        """Return True if the access token is valid (the server may still reject it)."""
        return self._access_token_expires > dt.now(tz=UTC) + td(seconds=15)

    async def fetch_access_token(self) -> None:
        """Update the access token and save it to the store/cache."""

        self.logger.debug("Fetching access_token...")

        if self._refresh_token:
            self.logger.debug(" - authenticating with the refresh_token")

            credentials = {SZ_REFRESH_TOKEN: self._refresh_token}

            try:
                await self._fetch_access_token(CREDS_REFRESH_TOKEN | credentials)

            except exc.AuthenticationFailedError as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # 400, e.g. invalid tokens
                    raise

                self.logger.debug("Expired/invalid refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            self.logger.debug(" - authenticating with client_id/secret")

            credentials = {
                # NOTE: the keys are case-sensitive: 'Username' and 'Password'
                "Username": self._client_id,
                "Password": self._secret,
            }

            try:  # check here if the user credentials are invalid...
                await self._fetch_access_token(CREDS_USER_PASSWORD | credentials)

            except exc.AuthenticationFailedError as err:
                if "invalid_grant" not in err.message:
                    raise
                self.logger.error(HINT_BAD_CREDS)  # noqa: TRY400
                # status will be: HTTPStatus.BAD_REQUEST, 400
                raise exc.BadUserCredentialsError(f"{err}", status=err.status) from err

            self._was_authenticated = True

        self.logger.debug(f" - access_token = {self.access_token}")
        self.logger.debug(f" - access_token_expires = {self.access_token_expires}")
        self.logger.debug(f" - refresh_token = {self.refresh_token}")

    async def _fetch_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using the supplied credentials.

        The credentials are either a refresh token or the user's client_id/secret.
        Will raise AuthenticationFailedError if unable to obtain an access token.
        """

        url = f"https://{self.hostname}/{URL_CRED}"

        response: AuthTokenResponseT = await self._post_access_token_request(
            url,
            headers=HEADERS_CRED | {"Authorization": "Basic " + _APPLICATION_ID},
            data=credentials,  # NOTE: is snake_case
        )

        try:  # the dict _should_ be the expected schema...
            self.logger.debug(
                f"POST {url}: {SCH_OAUTH_TOKEN(response)}"  # should be obfuscated
            )

        except vol.Invalid as err:
            self.logger.warning(f"POST {url}: payload may be invalid: {err}")

        tokens: AuthTokenResponseT = convert_keys_to_snake_case(response)

        try:
            self._access_token = tokens[SZ_ACCESS_TOKEN]
            self._access_token_expires = dt.now(tz=UTC) + td(
                seconds=tokens[SZ_EXPIRES_IN]
            )
            self._refresh_token = tokens[SZ_REFRESH_TOKEN]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}, payload={response}"
            ) from err

        self._was_authenticated = True  # i.e. the credentials are valid

        # if response.get(SZ_LATEST_EULA_ACCEPTED):

    async def _post_access_token_request(  # dev/test wrapper (also typing)
        self, url: StrOrURL, /, **kwargs: Any
    ) -> AuthTokenResponseT:
        """Wrap the POST request to the vendor's TCC RESTful API."""
        return await self._post_request(url, **kwargs)  # type: ignore[return-value]

    @abstractmethod
    async def save_access_token(self) -> None:
        """Save the (serialized) access token (and expiry dtm, refresh token).

        Should ideally confirm the access token is valid before saving.
        """

    def _import_access_token(self, tokens: AccessTokenEntryT) -> None:
        """Extract the token data from a (serialized) dictionary."""

        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _export_access_token(self) -> AccessTokenEntryT:
        """Convert the token data to a (serialized) dictionary."""

        return {
            SZ_ACCESS_TOKEN_EXPIRES: self._access_token_expires.isoformat(),
            SZ_ACCESS_TOKEN: self._access_token,
            SZ_REFRESH_TOKEN: self._refresh_token,
        }


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

        self._access_token = token_manager.get_access_token
        self._url_base = f"https://{self.hostname}/{URL_BASE}"

    async def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Ensure the authorization header has a valid access token."""

        headers = HEADERS_BASE | (headers or {})
        return headers | {
            "Authorization": "bearer " + await self._access_token(),
        }
