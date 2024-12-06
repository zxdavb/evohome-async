#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime as dt, timedelta as td
from typing import TYPE_CHECKING, Any, Final, TypedDict

import aiohttp
import voluptuous as vol

from evohome.auth import HOSTNAME, AbstractAuth, AbstractRequestContextManager
from evohome.helpers import convert_keys_to_snake_case

from . import exceptions as exc
from .schemas import SCH_USER_SESSION_RESPONSE, SZ_SESSION_ID as S2_SESSION_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from http import HTTPMethod

    from aiohttp.typedefs import StrOrURL

    from .schemas import EvoSessionDictT, EvoUserAccountDictT, TccSessionResponseT


# For docs, enter this App ID on the following website under 'Session login':
#  - https://mytotalconnectcomfort.com/WebApi/Help/LogIn
_APPLICATION_ID: Final = "91db1612-73fd-4500-91b2-e63b069b185c"
#

HEADERS_AUTH = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
}
HEADERS_BASE = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "SessionId": "",  # falsey value will invoke get_session_id()
}

SZ_SESSION_ID: Final = "session_id"
SZ_SESSION_ID_EXPIRES: Final = "session_id_expires"
SZ_USER_INFO: Final = "user_info"


class SessionIdEntryT(TypedDict):
    session_id: str
    session_id_expires: str  # dt.isoformat()


class AbstractSessionManager(ABC):
    """An ABC for managing the session id used for HTTP authentication."""

    _session_id: str
    _session_id_expires: dt  # TODO: should be in Auth class?
    _user_info: EvoUserAccountDictT | None  # TODO: should not publicise?

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
        self._websession = websession

        self._hostname = _hostname or HOSTNAME
        self._logger = logger or logging.getLogger(__name__)

        # set True once the credentials are validated the first time
        self._was_authenticated = False

        # the following is specific to session id (vs auth tokens)...
        self._clear_session_id()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(client_id='{self.client_id}')"

    @property
    def client_id(self) -> str:
        """Return the client id used for HTTP authentication."""
        return self._client_id

    def _clear_session_id(self) -> None:
        """Clear the session id."""

        self._session_id = ""
        self._session_id_expires = dt.min.replace(tzinfo=UTC)

    @property
    def session_id(self) -> str:
        """Return the session id."""
        return self._session_id

    @property
    def session_id_expires(self) -> dt:
        """Return the expiration datetime of the session id."""
        return self._session_id_expires

    @property
    def user_info(self) -> EvoUserAccountDictT | None:
        """Return the user account information."""
        return self._user_info

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
            self._logger.warning(
                "Missing/Expired/Invalid session_id, re-authenticating."
            )
            await self._update_session_id()

        return self.session_id

    async def _update_session_id(self) -> None:
        self._logger.warning("Authenticating with username/password...")

        credentials = {
            "applicationId": _APPLICATION_ID,
            "username": self._client_id,
            "password": self._secret,
        }

        # allow underlying exceptions through (as client_id/secret invalid)...
        await self._request_session_id(credentials)
        self._was_authenticated = True

        await self.save_session_id()

        self._logger.debug(f" - session_id = {self.session_id}")
        self._logger.debug(f" - session_id_expires = {self.session_id_expires}")
        self._logger.debug(f" - user_info = {self.user_info}")

    async def _request_session_id(self, credentials: dict[str, str]) -> None:
        """Obtain an session id using the supplied credentials.

        The credentials are the user's client_id/secret.
        """

        url = f"https://{self._hostname}/WebAPI/api/session"

        response: TccSessionResponseT = await self._post_session_id_request(
            url,
            headers=HEADERS_AUTH,
            data=credentials,  # NOTE: is camelCase
        )

        try:  # the dict _should_ be the expected schema...
            self._logger.debug(f"POST {url}: {SCH_USER_SESSION_RESPONSE(response)}")

        except vol.Invalid as err:
            self._logger.warning(f"Response JSON may be invalid: POST {url}: {err}")

        session: EvoSessionDictT = convert_keys_to_snake_case(response)  # type:ignore[assignment]

        try:
            self._session_id: str = session[SZ_SESSION_ID]
            self._session_id_expires = dt.now(tz=UTC) + td(minutes=15)
            self._user_info = session[SZ_USER_INFO]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Invalid response from server: {err}"
            ) from err

        if session.get("latest_eula_accepted"):
            self._logger.warning("The latest EULA has not been accepted by the user")

    async def _post_session_id_request(  # no method, as POST only
        self, url: StrOrURL, /, **kwargs: Any
    ) -> TccSessionResponseT:
        """Obtain a session id via a POST to the vendor's web API.

        Raise AuthenticationFailedError if unable to obtain a session id.
        """

        try:
            async with self._websession.post(url, **kwargs) as rsp:
                rsp.raise_for_status()

                self._was_authenticated = True  # i.e. the credentials are valid
                return await rsp.json()  # type:ignore[no-any-return]

        except aiohttp.ContentTypeError as err:
            #
            #
            response = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Server response is not JSON: POST {url}: {response}"
            ) from err

        except aiohttp.ClientResponseError as err:
            # TODO: add a hint for 401 (Unauthorized), others
            raise exc.AuthenticationFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class _RequestContextManager(AbstractRequestContextManager):
    """A context manager for authorized aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        session_id_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ) -> None:
        """Initialize the request context manager."""
        super().__init__(websession, method, url, **kwargs)

        self._get_session_id = session_id_getter

    async def _await_impl(self) -> aiohttp.ClientResponse:
        """Make an aiohttp request to the vendor's servers.

        Will handle authorisation by inserting a session id into the header.
        """

        headers: dict[str, str] = self.kwargs.pop("headers", "") or HEADERS_BASE

        if not headers.get(S2_SESSION_ID):
            headers[S2_SESSION_ID] = await self._get_session_id()

        return await self.websession.request(
            self.method, self.url, headers=headers, **self.kwargs
        )


class Auth(AbstractAuth):
    """A class to provide to access the v0 Resideo TCC API."""

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v0 Resideo TCC API."""
        super().__init__(websession, _hostname=_hostname, logger=logger)

        self._url_base = f"https://{self._hostname}/WebAPI/api"
        self._session_manager = session_manager

    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        """Raise an exception if the response is not OK."""

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            # if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
            #     raise exc.RequestFailedError(hint, status=err.status) from err
            raise exc.ApiRequestFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.ApiRequestFailedError(str(err)) from err

    def _raw_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> _RequestContextManager:
        """Return a context handler that can make the request."""

        return _RequestContextManager(
            self._session_manager.get_session_id,
            self._websession,
            method,
            url,
            **kwargs,
        )
