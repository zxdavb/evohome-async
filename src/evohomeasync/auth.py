#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Generator
from datetime import datetime as dt, timedelta as td
from http import HTTPMethod  # , HTTPStatus
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, TypedDict

import aiohttp
import voluptuous as vol

from common.helpers import convert_keys_to_snake_case

from . import exceptions as exc
from .schemas import SCH_USER_SESSION_RESPONSE, SZ_SESSION_ID as S2_SESSION_ID

if TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL

    from .schemas import SessionResponseT, UserAccountResponseT


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
    "SessionId": "",  # falsey value will invoke get_session_id()
}

SZ_SESSION_ID: Final = "session_id"
SZ_SESSION_ID_EXPIRES: Final = "session_id_expires"
SZ_USER_INFO: Final = "user_info"


class SessionIdT(TypedDict):
    session_id: str
    session_id_expires: str  # dt.isoformat()


class AbstractSessionManager(ABC):
    """An ABC for managing the session id used for HTTP authentication."""

    _session_id: str
    _session_expires: dt  # TODO: should be in Auth class?
    _user_info: UserAccountResponseT | None  # TODO: should not publicise?

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

    @property
    def session_id(self) -> str:
        """Return the session id."""
        return self._session_id

    @property
    def session_id_expires(self) -> dt:
        """Return the expiration datetime of the session id."""
        return self._session_expires

    @property
    def user_info(self) -> UserAccountResponseT | None:
        """Return the user account information."""
        return self._user_info

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

        await self.save_session_id()

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

        try:  # the dict _should_ be the expected schema...
            self._logger.debug(f"POST {url}: {SCH_USER_SESSION_RESPONSE(response)}")

        except vol.Invalid as err:
            self._logger.warning(f"Response JSON may be invalid: POST {url}: {err}")

        session: SessionResponseT = convert_keys_to_snake_case(response)

        try:
            self._session_id: str = session[SZ_SESSION_ID]
            self._session_expires = dt.now() + td(minutes=15)
            self._user_info = session[SZ_USER_INFO]

        except (KeyError, TypeError) as err:
            raise exc.AuthenticationFailedError(
                f"Invalid response from server: {err}"
            ) from err

        if session.get("latest_eula_accepted"):
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
            response = await rsp.text()
            raise exc.AuthenticationFailedError(
                f"Server response is not JSON: POST {url}: {response}"
            ) from err

        except aiohttp.ClientResponseError as err:
            #
            raise exc.AuthenticationFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.AuthenticationFailedError(str(err)) from err


class _RequestContextManager:
    """A context manager for an aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        session_id_getter: Callable[[], Awaitable[str]],
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ):
        """Initialize the request context manager."""

        self._get_session_id = session_id_getter
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
        """Make an aiohttp request to the vendor's servers.

        Will handle authorisation by inserting a session id into the header.
        """

        headers: dict[str, str] = self.kwargs.pop("headers", "") or HEADERS_BASE

        if not headers.get(S2_SESSION_ID):
            headers[S2_SESSION_ID] = await self._get_session_id()

        return await self.websession.request(
            self.method, self.url, headers=headers, **self.kwargs
        )


class Auth:
    """A class to provide to access the Resideo TCC API."""

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str = HOSTNAME,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the v0 Resideo TCC API."""

        self._session_manager = session_manager
        self._websession: Final = websession
        self._hostname: Final = _hostname
        self._logger: Final = logger or logging.getLogger(__name__)

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

        response: dict[str, Any]

        response = await self.request(  # type: ignore[assignment]
            HTTPMethod.GET, f"{self._url_base}/{url}"
        )

        if schema:
            try:
                response = schema(response)
            except vol.Invalid as err:
                self._logger.warning(f"Response JSON may be invalid: GET {url}: {err}")

        return response

    async def put(
        self,
        url: StrOrURL,
        json: dict[str, Any],
        schema: vol.Schema | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the vendor's API with a PUT.

        Optionally checks the payload JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        response: dict[str, Any] | list[dict[str, Any]]

        if schema:
            try:
                schema(json)
            except vol.Invalid as err:
                self._logger.warning(f"Payload JSON may be invalid: PUT {url}: {err}")

        response = await self.request(  # type: ignore[assignment]
            HTTPMethod.PUT, f"{self._url_base}/{url}", json=json
        )

        return response

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Resideo TCC RESTful API.

        Converts keys to/from snake_case as required.
        """

        # TODO: if method == HTTPMethod.PUT and "json" in kwargs:
        #     kwargs["json"] = convert_keys_to_camel_case(kwargs["json"])

        response = await self._request(method, url, **kwargs)

        self._logger.debug(f"{method} {url}: {response}")

        if method == HTTPMethod.GET:
            return convert_keys_to_snake_case(response)
        return response

    async def _request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Resideo TCC RESTful API.

        Checks for ClientErrors and handles Auth failures appropriately.

        Handles when session id is rejected by server (i.e. not expired, but otherwise
        deemed invalid by the server).
        """

        async def _content(
            rsp: aiohttp.ClientResponse,
        ) -> dict[str, Any] | list[dict[str, Any]] | str:
            """Return the response from the web server."""

            if not rsp.content_length:
                raise exc.RequestFailedError(f"Invalid response (no content): {rsp}")

            if rsp.content_type != "application/json":
                # assume "text/plain" or "text/html"
                return await rsp.text()

            response: dict[str, Any] = await rsp.json()
            return response

        def _raise_for_status(response: aiohttp.ClientResponse) -> None:
            """Raise an exception if the response is not OK."""

            try:
                response.raise_for_status()

            except aiohttp.ClientResponseError as err:
                # if hint := _ERR_MSG_LOOKUP_BASE.get(err.status):
                #     raise exc.RequestFailedError(hint, status=err.status) from err
                raise exc.RequestFailedError(str(err), status=err.status) from err

            except aiohttp.ClientError as err:  # e.g. ClientConnectionError
                raise exc.RequestFailedError(str(err)) from err

        # async with self._raw_request(method, url, **kwargs) as rsp:
        #     if rsp.status == HTTPStatus.OK:
        #         return _content(rsp)

        #     if (  # if 401/unauthorized, fetch new session_id and retry
        #         rsp.status != HTTPStatus.UNAUTHORIZED
        #         or rsp.content_type != "application/json"
        #     ):
        #         _raise_for_status(rsp)

        #     response = await rsp.json()
        #     try:
        #         # looking for invalid session: Unauthorized not EmailOrPasswordIncorrect
        #         if response[0]["code"] == "Unauthorized":
        #             pass
        #     except LookupError:
        #         _raise_for_status(rsp)

        # if self._session_manager.is_session_id_valid():
        #     self._logger.warning("session id was rejected, will clear it and retry")

        # self._session_manager._clear_session_id()  # TODO: private method

        async with self._raw_request(method, url, **kwargs) as rsp:
            _raise_for_status(rsp)

            return await _content(rsp)

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
