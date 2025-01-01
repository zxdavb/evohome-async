"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from typing import TYPE_CHECKING, Any, Final, TypedDict

import voluptuous as vol

from evohome.auth import (
    _ERR_MSG_LOOKUP_BOTH,
    HEADERS_BASE,
    HEADERS_CRED,
    AbstractAuth,
    CredentialsManagerBase,
)
from evohome.helpers import convert_keys_to_snake_case

from . import exceptions as exc
from .schemas import TCC_POST_USR_SESSION

if TYPE_CHECKING:
    import logging
    from collections.abc import Awaitable, Callable

    import aiohttp
    from aiohttp.typedefs import StrOrURL

    from .schemas import EvoSessionDictT, EvoUserAccountDictT, TccSessionResponseT


# For API docs, enter this App ID on the following website under 'Session login':
#  - https://mytotalconnectcomfort.com/WebApi/Help/LogIn
_APPLICATION_ID: Final = "91db1612-73fd-4500-91b2-e63b069b185c"
#

SZ_SESSION_ID: Final = "session_id"
SZ_SESSION_ID_EXPIRES: Final = "session_id_expires"
SZ_USER_INFO: Final = "user_info"

# POST authentication url (i.e. /WebAPI/api/session)
_ERR_MSG_LOOKUP_CRED = _ERR_MSG_LOOKUP_BOTH
URL_CRED: Final = "WebAPI/api/session"

# GET/PUT resource url (i.e. /WebAPI/api/...)
_ERR_MSG_LOOKUP_BASE = _ERR_MSG_LOOKUP_BOTH
URL_BASE: Final = "WebAPI/api"


class SessionIdEntryT(TypedDict):
    session_id: str
    session_id_expires: str  # dt.isoformat()


class AbstractSessionManager(CredentialsManagerBase, ABC):
    """An ABC for managing the session id used for HTTP authentication."""

    _session_id: str
    _session_id_expires: dt
    _user_info: EvoUserAccountDictT | None

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

        super().__init__(
            client_id, secret, websession, _hostname=_hostname, logger=logger
        )
        self._clear_session_id()

    def _clear_session_id(self) -> None:
        """Clear the session id (set to falsey state)."""

        self._session_id = ""
        self._session_id_expires = dt.min.replace(tzinfo=UTC)  # don't need local TZ

    @property
    def session_id(self) -> str:
        """Return the session id."""
        return self._session_id

    @property
    def session_id_expires(self) -> dt:
        """Return the expiration datetime of the session id."""
        return self._session_id_expires

    def is_session_id_valid(self) -> bool:
        """Return True if the session id is valid."""
        return self._session_id_expires > dt.now(tz=UTC) + td(seconds=15)

    @abstractmethod
    async def save_session_id(self) -> None:
        """Save the (serialized) session id to a cache."""

    def _import_session_id(self, session: SessionIdEntryT) -> None:
        """Deserialize the session id from a dictionary."""
        self._session_id = session[SZ_SESSION_ID]
        self._session_id_expires = dt.fromisoformat(session[SZ_SESSION_ID_EXPIRES])

    def _export_session_id(self) -> SessionIdEntryT:
        """Serialize the session id to a dictionary."""
        return {
            SZ_SESSION_ID_EXPIRES: self._session_id_expires.isoformat(),
            SZ_SESSION_ID: self._session_id,
        }

    async def get_session_id(self) -> str:
        """Return a valid session id.

        If required, fetch a new session id via the vendor's web API.
        """

        if not self.is_session_id_valid():  # may be invalid for other reasons
            self.logger.debug(
                "Null/Expired/Invalid session_id, will re-authenticate..."
            )
            await self._update_session_id()

        return self.session_id

    async def _update_session_id(self) -> None:
        self.logger.debug("Authenticating with client_id/secret")

        credentials = {
            "applicationId": _APPLICATION_ID,
            "username": self._client_id,
            "password": self._secret,
        }

        # allow underlying exceptions through (as client_id/secret invalid)...
        await self._request_session_id(credentials)
        self._was_authenticated = True

        await self.save_session_id()

        self.logger.debug(f" - session_id = {self.session_id}")
        self.logger.debug(f" - session_id_expires = {self.session_id_expires}")
        self.logger.debug(f" - user_info = {self._user_info}")

    async def _request_session_id(self, credentials: dict[str, str]) -> None:
        """Obtain an session id using the supplied credentials.

        The credentials are the user's client_id/secret.
        Will raise AuthenticationFailedError if unable to obtain a session id.
        """

        url = f"https://{self.hostname}/{URL_CRED}"

        response: TccSessionResponseT = await self._post_session_id_request(
            url,
            headers=HEADERS_CRED,
            data=credentials,  # NOTE: is camelCase
        )

        try:  # the dict _should_ be the expected schema...
            self.logger.debug(
                f"POST {url}: {TCC_POST_USR_SESSION(response)}"  # should be obfuscated
            )

        except vol.Invalid as err:
            self.logger.warning(f"POST {url}: payload may be invalid: {err}")

        session: EvoSessionDictT = convert_keys_to_snake_case(response)  # type:ignore[assignment]

        try:
            self._session_id: str = session[SZ_SESSION_ID]
            self._session_id_expires = dt.now(tz=UTC) + td(minutes=15)
            self._user_info = session[SZ_USER_INFO]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Authenticator response is invalid: {err}, payload={response}"
            ) from err

        self._was_authenticated = True  # i.e. the credentials are valid

        if session.get("latest_eula_accepted"):
            self.logger.warning("The latest EULA has not been accepted by the user")

    async def _post_session_id_request(  # dev/test wrapper (also typing)
        self, url: StrOrURL, /, **kwargs: Any
    ) -> TccSessionResponseT:
        """Wrap the POST request to the vendor's TCC RESTful API."""
        return await self._post_request(url, **kwargs)  # type: ignore[return-value]


class Auth(AbstractAuth):
    """A class to provide to access the v0 Resideo TCC API."""

    def __init__(
        self,
        session_id_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v0 Resideo TCC API."""

        super().__init__(websession, _hostname=_hostname, logger=logger)

        self._url_base = f"https://{self.hostname}/{URL_BASE}"
        self._get_session_id = session_id_getter

    async def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Ensure the authorization header has a valid session id."""

        headers = HEADERS_BASE | (headers or {})
        return headers | {
            "sessionId": await self._get_session_id(),
        }
