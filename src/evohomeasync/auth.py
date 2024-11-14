#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, Never, NewType, TypedDict

import aiohttp
import voluptuous as vol

from . import exceptions as exc
from .schema import (
    SZ_LATEST_EULA_ACCEPTED,
    SZ_SESSION_ID as S2_SESSION_ID,
    SZ_USER_INFO as S2_USER_INFO,
    SessionResponseT,
    UserAccountResponse,
)

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL

_UserIdT = NewType("_UserIdT", int)

_UserDataT = NewType("_UserDataT", dict[str, str | UserAccountResponse])
_LocnDataT = NewType("_LocnDataT", dict[str, Any])


# For docs, enter this App ID on the following website under 'Session login':
#  - https://mytotalconnectcomfort.com/WebApi/Help/LogIn
_APPLICATION_ID: Final = "91db1612-73fd-4500-91b2-e63b069b185c"
#

HOSTNAME: Final = "tccna.honeywell.com"

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
    "SessionId": None,
}

SZ_SESSION_ID: Final = "session_id"
SZ_SESSION_ID_EXPIRES: Final = "session_id_expires"


class SessionIdT(TypedDict):
    session_id: str
    session_id_expires: str  # dt.isoformat()


class _RequestContextManager:
    """A context manager for an aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ):
        """Initialize the request context manager."""

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
        """Return the actual result."""
        return await self.websession.request(self.method, self.url, **self.kwargs)


class AbstractSessionManager(ABC):
    """An ABC for managing the session id used for HTTP authentication."""

    _session_id: str
    _session_expires: dt  # TODO: should be in Auth class?
    #

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
        self._session_expires = dt.min
        #

    # @property
    # def user_info(self) -> str:

    @property
    def session_id(self) -> str:
        """Return the session id."""
        return self._session_id

    @property
    def session_id_expires(self) -> dt:
        """Return the expiration datetime of the session id."""
        return self._session_expires

    def is_session_id_valid(self) -> bool:
        """Return True if the session id is valid."""
        return self.session_id_expires > dt.now() + td(seconds=15)

    @abstractmethod
    async def save_session_id(self) -> None:
        """Save the (serialized) session id to a cache."""

    def _import_session_id(self, session: SessionIdT) -> None:
        """Deserialize the session id from a dictionary."""
        self._session_id = session[SZ_SESSION_ID]
        self._session_expires = dt.fromisoformat(session[SZ_SESSION_ID_EXPIRES])
        #

    def _export_session_id(self) -> SessionIdT:
        """Serialize the session id to a dictionary."""
        return {
            SZ_SESSION_ID: self._session_id,
            SZ_SESSION_ID_EXPIRES: self._session_expires.isoformat(),
            #
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

        # await self.save_session_id()

        self._logger.debug(f" - session_id = {self._session_id}")
        self._logger.debug(f" - session_id_expires = {self._session_expires}")
        self._logger.debug(f" - user_info = {self._user_info}")

    async def _request_session_id(self, credentials: dict[str, str]) -> None:
        """Obtain an session id using the supplied credentials.

        The credentials are the user's client_id/secret.
        """

        url = f"https://{self._hostname}/WebAPI/api/session"

        response: SessionResponseT = await self._post_session_id_request(
            url, headers=HEADERS_AUTH, data=credentials
        )

        # try:  # the dict _should_ be the expected schema...
        #     _ = SCH_SESSION_RESPONSE(response)
        # except vol.Invalid as err:
        #     self._logger.debug(
        #         f"Response JSON may be invalid: POST {url}: {err})
        #     )

        try:
            self._session_id: str = response[S2_SESSION_ID]
            self._session_expires = dt.now() + td(minutes=15)
            self._user_info: UserAccountResponse = response[S2_USER_INFO]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Invalid response from server: {err}"
            ) from err

        if response.get(SZ_LATEST_EULA_ACCEPTED):
            self._logger.warning("The latest EULA has not been accepted by the user")

    async def _post_session_id_request(
        self, url: StrOrURL, **kwargs: Any
    ) -> SessionResponseT:
        """Obtain a session id via a POST to the vendor's web API.

        Raise AuthenticationFailedError if unable to obtain a session id.
        """

        try:
            async with self._websession.post(url, **kwargs) as rsp:
                rsp.raise_for_status()

                self._was_authenticated = True  # i.e. the credentials are valid
                return await rsp.json()  # type: ignore[no-any-return]

        except aiohttp.ContentTypeError as err:
            #
            #
            content = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Server response is not JSON: POST {url}: {content}"
            ) from err

        except aiohttp.ClientResponseError as err:
            #
            raise exc.AuthenticationFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class Auth(AbstractSessionManager):
    """A class to provide to access the Resideo TCC API."""

    _user_data: _UserDataT | dict[Never, Never]
    _full_data: list[_LocnDataT]

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str = HOSTNAME,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v0 Resideo TCC API."""

        super().__init__(
            username, password, websession, _hostname=_hostname, logger=logger
        )

        self._full_data = []
        self._user_data = {}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(base='{self._url_base}')"

    @property
    def _url_base(self) -> StrOrURL:
        """Return the URL base used for GET/PUT."""
        return f"https://{self._hostname}/WebAPI/api"

    async def get(
        self, url: StrOrURL, schema: vol.Schema | None = None
    ) -> dict[str, Any]:
        """Call the Resideo TCC API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        content: dict[str, Any]

        content = await self._request(  # type: ignore[assignment]
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
        json: dict[str, Any] | str,
        schema: vol.Schema | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the Resideo TCC API with a PUT (POST is only used for authentication).

        Optionally checks the request JSON against the expected schema and logs a
        warning if it doesn't match (NB: does not raise a vol.Invalid).
        """

        content: dict[str, Any] | list[dict[str, Any]]

        if schema:
            try:
                _ = schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"Payload JSON may be invalid: PUT {url}: {err}")

        content = await self._request(  # type: ignore[assignment]
            HTTPMethod.PUT, f"{self._url_base}/{url}", json=json
        )

        return content

    async def _request(  # wrapper for self.request()
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Handle Auth failures when making a request to the RESTful API."""

        # async with self._websession(method, url, **kwargs) as rsp:
        async with await self.request(method, url, **kwargs) as rsp:
            response_text = await rsp.text()  # why can't I move this below the if?

            # if 401/unauthorized, may need to refresh session_id (expires in 15 mins?)
            if rsp.status != HTTPStatus.UNAUTHORIZED:  # or _dont_reauthenticate:
                return rsp

            # TODO: use response.content_type to determine whether to use .json()
            if "code" not in response_text:  # don't use .json() yet: may be plain text
                return rsp

            response_json = await rsp.json()
            if response_json[0]["code"] != "Unauthorized":
                return rsp

            # NOTE: I cannot recall if this is needed, or if it causes a bug
            # if S2_SESSION_ID not in self._headers:  # no value trying to re-authenticate
            #     return response  # ...because: the user credentials must be invalid

            self._logger.debug(f"Session now expired/invalid ({self._session_id})...")
            self._headers = {
                "content-type": "application/json"
            }  # remove the session_id

            _, rsp = await self.get_user_data()  # Get a fresh session_id
            assert self._session_id is not None  # mypy hint

            self._logger.debug(f"... success: new session_id = {self._session_id}")
            self._headers[S2_SESSION_ID] = self._session_id

            if "session" in str(url):  # retry not needed for /session
                return rsp

            # NOTE: this is a recursive call, used only after re-authenticating
            rsp = await self.request(
                method, url, kwargs=kwargs, _dont_reauthenticate=True
            )
            return rsp

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """Make a request to the Resideo TCC RESTful API."""

        headers = kwargs.pop("headers", None) or HEADERS_BASE

        if not headers.get(S2_SESSION_ID):
            headers[S2_SESSION_ID] = await self.get_session_id()

        return await _RequestContextManager(
            self._websession, method, url, **kwargs, headers=headers
        )

    async def save_session_id(self) -> None:
        """Save the (serialized) session id to a cache."""
        raise NotImplementedError
