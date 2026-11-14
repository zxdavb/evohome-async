"""Authentication (access token) for the TCC v2 API."""

from __future__ import annotations

import asyncio
import base64
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, TypedDict

import probatio as vol
from aiohttp import hdrs

from _evohome.auth import AbstractAuth, _details_of
from _evohome.const import HEADERS_BASE, HEADERS_CRED, HINT_BAD_CREDS
from _evohome.credentials import CredentialsManagerBase
from _evohome.helpers import convert_keys_to_snake_case, redact

from . import exceptions as exc
from .const import URL_BASE, URL_CRED, URL_USR_ACCOUNT
from .exceptions import ApiCallErrorReason
from .schemas.account import TCC_POST_OAUTH_TOKEN
from .schemas.const import (
    OAUTH_ACCESS_TOKEN,
    OAUTH_EXPIRES_IN,
    OAUTH_GRANT_TYPE,
    OAUTH_PASSWORD,
    OAUTH_REFRESH_TOKEN,
    OAUTH_SCOPE,
    OAUTH_TOKEN_TYPE,
    OAUTH_USERNAME,
    TccOAuthError,
)

if TYPE_CHECKING:
    import aiohttp
    from aiohttp.typedefs import StrOrURL

    from .schemas.account import TccOAuthTokenResponseT
    from .typedefs import EvoAuthTokensResponseT


_APPLICATION_ID: Final = base64.b64encode(
    b"4a231089-d2b6-41bd-a5eb-16a0a422b999:"
    b"1a15cdb8-42de-407b-add0-059f92c530cb"
).decode("utf-8")  # fmt: off

_SCOPE: Final = "EMEA-V1-Basic EMEA-V1-Anonymous"


# TODO: deprecate, then remove in v4: use the OAUTH_* equivalents
SZ_EXPIRES_IN: Final = OAUTH_EXPIRES_IN
SZ_SCOPE: Final = OAUTH_SCOPE
SZ_TOKEN_TYPE: Final = OAUTH_TOKEN_TYPE


# the keys of the (serialized) token cache, EvoAccessTokenEntryT (not the vendor's)
SZ_ACCESS_TOKEN: Final = "access_token"  # noqa: S105
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"  # noqa: S105
SZ_REFRESH_TOKEN: Final = "refresh_token"  # noqa: S105


class EvoAccessTokenEntryT(TypedDict):
    """Dict for storing/restoring auth tokens to/from a store."""

    access_token: str
    access_token_expires: str  # dt.isoformat()
    refresh_token: str


# TODO: deprecate, then remove in v4: use schemas.account.TCC_POST_OAUTH_TOKEN
SCH_OAUTH_TOKEN: Final = TCC_POST_OAUTH_TOKEN  # not used internally

CREDS_REFRESH_TOKEN: Final = {
    OAUTH_GRANT_TYPE: "refresh_token",
    OAUTH_SCOPE: _SCOPE,
    OAUTH_REFRESH_TOKEN: "",
}

CREDS_USER_PASSWORD: Final = {
    OAUTH_GRANT_TYPE: "password",
    OAUTH_SCOPE: _SCOPE,  # EMEA-V1-Get-Current-User-Account
    OAUTH_USERNAME: "",
    OAUTH_PASSWORD: "",
}


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
        logger: logging.Logger | None = None,
        _hostname: str | None = None,
    ) -> None:
        """Initialize the token manager."""

        logger = logger or logging.getLogger(__name__)

        super().__init__(
            client_id, secret, websession, logger=logger, _hostname=_hostname
        )
        self.clear_access_token()  # initialise the attrs

        self._token_lock = asyncio.Lock()
        self._token_fetches = 0  # completed fetches, so waiters can share a failure
        self._token_error: exc.EvohomeError | None = None

    def clear_access_token(self) -> None:
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

        Concurrent callers share a single fetch. If that fetch fails, the callers that
        were waiting on it raise the same exception (rather than each trying again);
        later callers will try again.
        """

        if self.is_token_valid():  # although may be rejected for other reasons
            return self.access_token

        fetches = self._token_fetches

        async with self._token_lock:
            if fetches != self._token_fetches and self._token_error is not None:
                raise self._token_error

            if not self.is_token_valid():  # it may have been refreshed meanwhile
                self._token_error = None
                try:
                    await self.fetch_access_token()
                except exc.EvohomeError as err:
                    self._token_error = err
                    raise
                finally:
                    self._token_fetches += 1

                await self.save_access_token()

        return self.access_token

    def is_token_valid(self) -> bool:
        """Return True if the access token is valid (the server may still reject it)."""
        return self._access_token_expires > dt.now(tz=UTC) + td(seconds=15)

    async def fetch_access_token(self) -> None:
        """Update the access token and save it to the store/cache."""

        self._logger.debug("Fetching access_token...")

        if self._refresh_token:
            self._logger.debug(" - authenticating with the refresh_token")

            credentials = {OAUTH_REFRESH_TOKEN: self._refresh_token}

            try:
                await self._fetch_access_token(CREDS_REFRESH_TOKEN | credentials)

            except exc.AuthenticationFailedError as err:
                if err.status != HTTPStatus.BAD_REQUEST:  # 400, e.g. invalid tokens
                    raise

                self._logger.debug("Expired/invalid refresh_token")
                self._refresh_token = ""

        if not self._refresh_token:
            self._logger.debug(" - authenticating with client_id/secret")

            credentials = {
                OAUTH_USERNAME: self._client_id,
                OAUTH_PASSWORD: self._secret,
            }

            try:  # check here if the user credentials are invalid...
                await self._fetch_access_token(CREDS_USER_PASSWORD | credentials)

            except exc.AuthenticationFailedError as err:
                if TccOAuthError.INVALID_GRANT not in err.message:
                    raise
                self._logger.error(HINT_BAD_CREDS)  # noqa: TRY400
                # status will be: HTTPStatus.BAD_REQUEST, 400
                raise exc.BadUserCredentialsError(
                    f"{err}",
                    status=err.status,
                    response=err.response,
                    **_details_of(err.details),  # e.g. the vendor's error code
                ) from err

            self._was_authenticated = True

        # access_token is short-lived (but not safe to log refresh_token here)...
        self._logger.debug(f" - access_token = {redact(self.access_token)}")
        self._logger.debug(f" - access_token_expires = {self.access_token_expires}")

    async def _fetch_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using the supplied credentials.

        The credentials are either a refresh token or the user's client_id/secret.
        Will raise AuthenticationFailedError if unable to obtain an access token.
        """

        url = f"https://{self.hostname}/{URL_CRED}"

        response: TccOAuthTokenResponseT = await self._post_access_token_request(
            url,
            headers=HEADERS_CRED | {hdrs.AUTHORIZATION: "Basic " + _APPLICATION_ID},
            data=credentials,  # NOTE: is form-encoded, so its keys are as-is
        )

        try:  # the dict _should_ be the expected schema...
            self._logger.debug(
                f"POST {url}: {TCC_POST_OAUTH_TOKEN(response)}"  # secrets are redacted via validator
            )

        except vol.Invalid as err:
            self._logger.warning(f"POST {url}: payload may be invalid: {err}")

        tokens: EvoAuthTokensResponseT = convert_keys_to_snake_case(response)

        try:
            self._access_token = tokens[OAUTH_ACCESS_TOKEN]
            self._access_token_expires = dt.now(tz=UTC) + td(
                seconds=tokens[OAUTH_EXPIRES_IN]
            )
            self._refresh_token = tokens[OAUTH_REFRESH_TOKEN]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {response}: {err.__class__.__name__}: {err}",
                reason=ApiCallErrorReason.AUTH_RESPONSE_INVALID,
            ) from err

        self._was_authenticated = True  # i.e. the credentials are valid

        # TODO: determine if this API support this 'feature'
        # if response.get("latest_eula_accepted") is False:
        #     self._logger.warning("The latest EULA has not been accepted by the user")

    async def _post_access_token_request(  # dev/test wrapper (also typing)
        self, url: StrOrURL, /, **kwargs: Any
    ) -> TccOAuthTokenResponseT:
        """Wrap the POST request to the vendor's TCC RESTful API."""
        return await self._post_request(url, **kwargs)  # type: ignore[return-value]

    @abstractmethod
    async def save_access_token(self) -> None:
        """Save the (serialized) access token (and expiry dtm, refresh token).

        Should ideally confirm the access token is valid before saving.
        """

    def _import_access_token(self, tokens: EvoAccessTokenEntryT) -> None:
        """Extract the token data from a (serialized) dictionary.

        Deprecated: use import_access_token().
        """
        self.import_access_token(tokens)

    def import_access_token(self, tokens: EvoAccessTokenEntryT, /) -> None:
        """Restore the access token (its expiry, the refresh token) from a dict."""

        self._access_token = tokens[SZ_ACCESS_TOKEN]
        self._access_token_expires = dt.fromisoformat(tokens[SZ_ACCESS_TOKEN_EXPIRES])
        self._refresh_token = tokens[SZ_REFRESH_TOKEN]

    def _export_access_token(self) -> EvoAccessTokenEntryT:
        """Convert the token data to a (serialized) dictionary.

        Deprecated: use export_access_token().
        """
        return self.export_access_token()

    def export_access_token(self) -> EvoAccessTokenEntryT:
        """Return the access token (its expiry, the refresh token) as a dict."""

        return {
            SZ_ACCESS_TOKEN_EXPIRES: self._access_token_expires.isoformat(),
            SZ_ACCESS_TOKEN: self._access_token,
            SZ_REFRESH_TOKEN: self._refresh_token,
        }


class Auth(AbstractAuth):
    """A class for interacting with the v2 Resideo TCC API."""

    _URL_PROBE = URL_USR_ACCOUNT
    _CREDENTIAL = "access_token"

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        websession: aiohttp.ClientSession,
        /,
        *,
        logger: logging.Logger | None = None,
        _hostname: str | None = None,
    ) -> None:
        """A class for interacting with the v2 Resideo TCC API."""

        logger = logger or logging.getLogger(__name__)

        super().__init__(websession, logger=logger, _hostname=_hostname)

        self._token_manager: Final = token_manager
        self._access_token = token_manager.get_access_token
        self._url_base = f"https://{self.hostname}/{URL_BASE}"

    async def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Ensure the authorization header has a valid access token."""

        headers = HEADERS_BASE | (headers or {})
        return headers | {
            hdrs.AUTHORIZATION: "bearer " + await self._access_token(),
        }

    def _credential_in_use(self) -> str | None:
        """Return the access token that the next request will send, if it is valid."""

        if not self._token_manager.is_token_valid():
            return None
        return self._token_manager.access_token

    def _clear_rejected_credential(self, rejected: str | None) -> None:
        """Clear the access token that was rejected, unless since refreshed."""

        if rejected is None or self._token_manager.access_token == rejected:
            self._token_manager.clear_access_token()
