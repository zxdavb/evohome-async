#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import voluptuous as vol

from evohome import exceptions as exc
from evohome.helpers import convert_keys_to_camel_case, convert_keys_to_snake_case

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

    import aiohttp
    from aiohttp.typedefs import StrOrURL


HOSTNAME: Final = "tccna.honeywell.com"


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both url_auth & url_base
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test only?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}


class AbstractRequestContextManager(ABC):
    """A context manager for authorized aiohttp request."""

    _response: aiohttp.ClientResponse | None = None

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        method: HTTPMethod,
        url: StrOrURL,
        /,
        **kwargs: Any,
    ) -> None:
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

    @abstractmethod
    async def _await_impl(self) -> aiohttp.ClientResponse:
        """Make an aiohttp request to the vendor's servers."""


class AbstractAuth(ABC):
    """A class to provide to access the Resideo TCC API."""

    _url_base: StrOrURL

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        /,
        *,
        _hostname: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the Resideo TCC API."""

        self.websession: Final = websession
        self.hostname: Final = _hostname or HOSTNAME
        self.logger: Final = logger or logging.getLogger(__name__)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(base='{self.url_base}')"

    @property
    def url_base(self) -> StrOrURL:
        """Return the URL base used for GET/PUT."""
        return self._url_base

    async def get(
        self, url: StrOrURL, /, schema: vol.Schema | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Call the vendor's TCC API with a GET.

        Optionally checks the response JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        response = await self.request(HTTPMethod.GET, url)

        if schema:
            try:
                response = schema(response)
            except vol.Invalid as err:
                self.logger.warning(f"Response JSON may be invalid: GET {url}: {err}")

        assert isinstance(response, dict | list)  # mypy
        return response

    async def put(
        self,
        url: StrOrURL,
        /,
        json: dict[str, Any],
        *,
        schema: vol.Schema | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:  # NOTE: not _EvoSchemaT
        """Call the vendor's API with a PUT.

        Optionally checks the payload JSON against the expected schema and logs a
        warning if it doesn't match.
        """

        if schema:
            try:
                schema(json)
            except vol.Invalid as err:
                self.logger.warning(f"Payload JSON may be invalid: PUT {url}: {err}")

        response = await self.request(HTTPMethod.PUT, url, json=json)

        assert isinstance(response, dict | list)  # mypy
        return response

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the vendor's TCC RESTful API.

        Converts keys to/from snake_case as required.
        """

        if method == HTTPMethod.PUT and "json" in kwargs:
            kwargs["json"] = convert_keys_to_camel_case(kwargs["json"])

        response = await self._request(method, url, **kwargs)

        self.logger.debug(f"{method} {url}: {response}")

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

            if not rsp.content_length or rsp.content_type != "application/json":
                # usually "text/plain", "text/html"
                raise exc.ApiRequestFailedError(
                    f"Server response is invalid (not JSON): {await rsp.text()}"
                )

            if (response := await rsp.json()) is None:  # an unanticipated edge-case
                raise exc.AuthenticationFailedError(
                    f"Server response is null: POST {url}"
                )

            return response  # type: ignore[no-any-return]

        async with self._raw_request(method, f"{self.url_base}/{url}", **kwargs) as rsp:
            self._raise_for_status(rsp)

            return await _content(rsp)

    @abstractmethod
    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        """Raise an exception if the response is not OK."""

    @abstractmethod
    def _raw_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> AbstractRequestContextManager:
        """Return a context handler that can make the request."""
