#!/usr/bin/env python3
"""evohomeasync provides an async client for the *original* Evohome TCC API."""

from __future__ import annotations

import logging
from http import HTTPMethod, HTTPStatus
from typing import Any, Final, Never, NewType

import aiohttp

from . import exceptions as exc
from .schema import SZ_SESSION_ID, SZ_USER_ID, SZ_USER_INFO

_SessionIdT = NewType("_SessionIdT", str)
_UserIdT = NewType("_UserIdT", int)

_UserInfoT = NewType("_UserInfoT", dict[str, bool | int | str])
_UserDataT = NewType("_UserDataT", dict[str, _SessionIdT | _UserInfoT])
_LocnDataT = NewType("_LocnDataT", dict[str, Any])


URL_HOST: Final = "https://tccna.honeywell.com"

# For docs, see:
#  - https://mytotalconnectcomfort.com/WebApi/Help/LogIn and enter this Session Login:
_APP_ID: Final = "91db1612-73fd-4500-91b2-e63b069b185c"

_LOGGER: Final = logging.getLogger(__name__)


class Broker:
    """Provide a client to access the Honeywell TCC API (assumes a single TCS)."""

    _user_data: _UserDataT | dict[Never, Never]
    _full_data: list[_LocnDataT]

    def __init__(
        self,
        username: str,
        password: str,
        logger: logging.Logger,
        /,
        *,
        session_id: _SessionIdT | None = None,
        hostname: str | None = None,  # is a URL
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """A class for interacting with the v1 Evohome TCC API."""

        self.username = username  # TODO: remove
        self._logger = logger

        self._session_id: _SessionIdT | None = session_id
        self._user_id: _UserIdT | None = None

        self.hostname: Final = hostname or URL_HOST
        self._session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        self._headers: dict[str, str] = {
            "content-type": "application/json"
        }  # NB: no session_id yet
        self._POST_DATA: Final[dict[str, str]] = {
            "Username": self.username,
            "Password": password,
            "ApplicationId": _APP_ID,
        }

        self._user_data = {}
        self._full_data = []

    @property
    def session_id(self) -> _SessionIdT | None:
        """Return the session id used for HTTP authentication."""
        return self._session_id

    async def populate_user_data(self) -> _UserDataT:
        """Return the latest user data as retrieved from the web."""

        user_data: _UserDataT

        user_data, _ = await self._populate_user_data()
        return user_data

    async def _populate_user_data(self) -> tuple[_UserDataT, aiohttp.ClientResponse]:
        """Return the latest user data as retrieved from the web."""

        url = "session"
        response = await self.make_request(HTTPMethod.POST, url, data=self._POST_DATA)

        self._user_data: _UserDataT = await response.json()
        assert self._user_data != {}

        user_id: _UserIdT = self._user_data[SZ_USER_INFO][SZ_USER_ID]  # type: ignore[assignment, index]
        session_id: _SessionIdT = self._user_data[SZ_SESSION_ID]  # type: ignore[assignment, index]

        self._user_id = user_id
        self._session_id = self._headers[SZ_SESSION_ID] = session_id

        self._logger.info(f"user_data = {self._user_data}")
        return self._user_data, response  # type: ignore[return-value]

    async def populate_full_data(self) -> list[_LocnDataT]:
        """Return the latest location data exactly as retrieved from the web."""

        if not self._user_id:  # not yet authenticated
            # maybe was instantiated with a bad session_id, so must check user_id
            await self.populate_user_data()

        url = f"locations?userId={self._user_id}&allData=True"
        response = await self.make_request(HTTPMethod.GET, url, data=self._POST_DATA)

        self._full_data: list[_LocnDataT] = await response.json()

        self._logger.info(f"full_data = {self._full_data}")
        return self._full_data

    async def _make_request(
        self,
        method: HTTPMethod,
        url: str,
        /,
        *,
        data: dict[str, Any] | None = None,
        _dont_reauthenticate: bool = False,  # used only with recursive call
    ) -> aiohttp.ClientResponse:
        """Perform an HTTP request, with an optional retry if re-authenticated."""

        response: aiohttp.ClientResponse

        if method == HTTPMethod.GET:
            func = self._session.get
        elif method == HTTPMethod.PUT:
            func = self._session.put
        elif method == HTTPMethod.POST:
            func = self._session.post

        url_ = self.hostname + "/WebAPI/api/" + url

        async with func(url_, json=data, headers=self._headers) as response:
            response_text = await response.text()  # why can't I move this below the if?

            # if 401/unauthorized, may need to refresh session_id (expires in 15 mins?)
            if response.status != HTTPStatus.UNAUTHORIZED or _dont_reauthenticate:
                return response

            # TODO: use response.content_type to determine whether to use .json()
            if "code" not in response_text:  # don't use .json() yet: may be plain text
                return response

            response_json = await response.json()
            if response_json[0]["code"] != "Unauthorized":
                return response

            # NOTE: I cannot recall if this is needed, or if it causes a bug
            # if SZ_SESSION_ID not in self._headers:  # no value trying to re-authenticate
            #     return response  # ...because: the user credentials must be invalid

            _LOGGER.debug(f"Session now expired/invalid ({self._session_id})...")
            self._headers = {
                "content-type": "application/json"
            }  # remove the session_id

            _, response = await self._populate_user_data()  # Get a fresh session_id
            assert self._session_id is not None  # mypy hint

            _LOGGER.debug(f"... success: new session_id = {self._session_id}")
            self._headers[SZ_SESSION_ID] = self._session_id

            if "session" in url_:  # retry not needed for /session
                return response

            # NOTE: this is a recursive call, used only after re-authenticating
            response = await self._make_request(
                method, url, data=data, _dont_reauthenticate=True
            )
            return response

    async def make_request(
        self,
        method: HTTPMethod,
        url: str,
        /,
        *,
        data: dict[str, Any] | None = None,
    ) -> aiohttp.ClientResponse:
        """Perform an HTTP request, will authenticate if required."""

        try:
            response = await self._make_request(method, url, data=data)  # ? ClientError
            response.raise_for_status()  # ? ClientResponseError

        # response.method, response.url, response.status, response._body
        # POST,    /session, 429, [{code: TooManyRequests, message: Request count limitation exceeded...}]
        # GET/PUT  /???????, 401, [{code: Unauthorized,    message: Unauthorized}]

        except aiohttp.ClientResponseError as err:
            if response.method == HTTPMethod.POST:  # POST only used when authenticating
                raise exc.AuthenticationFailed(  # includes TOO_MANY_REQUESTS
                    str(err), status=err.status
                ) from err
            if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise exc.RateLimitExceeded(str(err), status=err.status) from err
            raise exc.RequestFailed(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # using response causes UnboundLocalError
            if method == HTTPMethod.POST:  # POST only used when authenticating
                raise exc.AuthenticationFailed(str(err)) from err
            raise exc.RequestFailed(str(err)) from err

        return response
