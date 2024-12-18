"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import voluptuous as vol

from evohome import exceptions as exc
from evohome.helpers import (
    convert_keys_to_camel_case,
    convert_keys_to_snake_case,
    obscure_secrets,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

    from aiohttp.typedefs import StrOrURL


HOSTNAME: Final = "tccna.resideo.com"


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both url_auth & url_base
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test only?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}


class RequestContextManager:
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

    async def _await_impl(self) -> aiohttp.ClientResponse:
        """Make an aiohttp request to the vendor's servers.

        Assumes there are valid credentials in the header.
        """

        return await self.websession.request(self.method, self.url, **self.kwargs)


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

        return response  # type: ignore[return-value]

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

        return await self.request(HTTPMethod.PUT, url, json=json)  # type: ignore[return-value]

    async def request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the vendor's TCC RESTful API.

        Converts keys to/from snake_case as required.
        """

        if method == HTTPMethod.PUT and "json" in kwargs:
            kwargs["json"] = convert_keys_to_camel_case(kwargs["json"])

        response = await self._request(method, url, **kwargs)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"{method} {url}: {obscure_secrets(response)}")

        if method == HTTPMethod.GET:
            return convert_keys_to_snake_case(response)
        return response

    async def _request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        """Make a request to the Resideo TCC RESTful API.

        Checks for authentication failures and other ClientErrors.
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

        headers = await self._headers(kwargs.pop("headers", {}))

        async with self._raw_request(
            method, f"{self.url_base}/{url}", headers=headers, **kwargs
        ) as rsp:
            self._raise_for_status(rsp)

            return await _content(rsp)

    @abstractmethod
    async def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Ensure the authorization header is valid.

        This could take the form of an access token, or a session id.
        """

    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        """Raise an exception if the response is not < 400."""

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as err:
            raise exc.ApiRequestFailedError(str(err), status=err.status) from err

        except aiohttp.ClientError as err:  # e.g. ClientConnectionError
            raise exc.ApiRequestFailedError(str(err)) from err

    def _raw_request(
        self, method: HTTPMethod, url: StrOrURL, /, **kwargs: Any
    ) -> RequestContextManager:
        """Return a context handler that can make the request."""

        return RequestContextManager(
            self.websession,
            method,
            url,
            **kwargs,
        )
