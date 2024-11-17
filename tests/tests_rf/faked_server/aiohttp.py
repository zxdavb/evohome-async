#!/usr/bin/env python3
"""A hacked aiohttp to provide a faked server."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from enum import EnumCheck, StrEnum, verify
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from asyncio.streams import _ReaduntilBuffer

    from .const import _bodyT, _methodT, _statusT, _urlT
    from .vendor import FakedServer


_DEFAULT_LIMIT = 2**16  # 64 KiB


@verify(EnumCheck.UNIQUE)
class hdrs(StrEnum):  # a la aiohttp
    METH_GET = "GET"
    METH_POST = "POST"
    METH_PUT = "PUT"


class StreamReader(asyncio.StreamReader):
    """A faked StreamReader."""

    _buffer = bytearray()

    def __init__(
        self, limit: int = _DEFAULT_LIMIT, loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        pass

    async def read(self, n: int = -1) -> bytes:
        """Read up to `n` bytes from the stream."""
        raise NotImplementedError

    async def readline(self) -> bytes:
        """Read chunk of data from the stream until newline (b'\n') is found."""
        return await self.readuntil(b"\n")

    async def readexactly(self, n: int) -> bytes:
        """Read exactly `n` bytes."""
        raise NotImplementedError

    async def readuntil(self, separator: _ReaduntilBuffer = b"\n") -> bytes:
        """Read data from the stream until ``separator`` is found."""
        raise NotImplementedError

    async def __aenter__(self, *args: Any, **kwargs: Any) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


class ClientError(Exception):
    """A faked ClientError."""


class ClientResponseError(ClientError):
    """A faked ClientResponseError."""

    def __init__(
        self, msg: str, /, *, status: int | None = None, **kwargs: Any
    ) -> None:
        super().__init__(msg)
        self.status = status
        self.message = msg


class ContentTypeError(ClientResponseError):
    """ContentType found is not valid."""


class ClientTimeout:
    """A faked ClientTimeout."""

    def __init__(self, /, *, total: float | None = None, **kwargs: Any) -> None:
        self.total: float = total or 30


class ClientSession:
    """A faked ClientSession."""

    def __init__(
        self, /, *, timeout: ClientTimeout | None = None, **kwargs: Any
    ) -> None:
        self._timeout = timeout or ClientTimeout()

        # this is required, so no .get()
        self._faked_server: FakedServer = kwargs["faked_server"]

    def request(self, method: hdrs, url: str, **kwargs: Any) -> ClientResponse:
        """Perform HTTP request."""
        if method == hdrs.METH_GET:
            return self.get(url, **kwargs)
        if method == hdrs.METH_PUT:
            return self.put(url, **kwargs)
        if method == hdrs.METH_POST:
            return self.post(url, **kwargs)
        raise NotImplementedError

    def get(self, url: str, **kwargs: Any) -> ClientResponse:
        assert not {k: v for k, v in kwargs.items() if k != "headers" and v is not None}
        return ClientResponse(hdrs.METH_GET, url, session=self)  # type: ignore[arg-type]

    def put(
        self, url: str, /, *, data: Any = None, json: Any = None, **kwargs: Any
    ) -> ClientResponse:
        assert not {k: v for k, v in kwargs.items() if k != "headers"}
        return ClientResponse(hdrs.METH_PUT, url, data=data or json, session=self)  # type: ignore[arg-type]

    def post(self, url: str, /, *, data: Any = None, **kwargs: Any) -> ClientResponse:
        assert not {k: v for k, v in kwargs.items() if k != "headers"}
        return ClientResponse(hdrs.METH_POST, url, data=data, session=self)  # type: ignore[arg-type]

    async def close(self) -> None:
        pass


class ClientResponse:
    """A faked ClientResponse."""

    charset: str = "utf-8"

    def __init__(
        self,
        method: _methodT,
        url: _urlT,
        /,
        *,
        data: str | None = None,
        json: dict[str, Any] | None = None,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> None:
        self.method = method
        self.url = url
        self.session = session

        assert self.session is not None  # mypy
        self._faked_server = self.session._faked_server

        self.status: _statusT = None  # type: ignore[assignment]
        self._body: _bodyT | None = None

        # self.content = StreamReader(
        #     self._faked_server.request(method, url, data=data or json)
        # )
        self._body = self._faked_server.request(method, url, data=data or json)
        self.status = self._faked_server.status  # type: ignore[assignment]

    def raise_for_status(self) -> None:
        if self.status >= 300:
            raise ClientResponseError(
                f"{self.method} {self.url}: {self.status}", status=self.status
            )

    @property
    def content_length(self) -> int | None:
        if self._body is None:
            return None
        if self.content_type == "text/plain":
            return len(self._body)
        return len(str(self._body))

    @property
    def content_type(self) -> str | None:
        """Return the Content-Type header of the response."""

        # if isinstance(self._body, bytes):
        #     return "application/octet-stream"
        if isinstance(self._body, (dict | list)):
            return "application/json"
        if not isinstance(self._body, str):
            raise NotImplementedError
        if self._body.strip().startswith("<html>"):
            return "text/html"
        return "text/plain"

    async def text(self, /, **kwargs: Any) -> str:  # assumes is JSON or plaintext
        """Return the response body as text."""
        if self.content_type == "application/json":
            return json.dumps(self._body)
        if self.content_type in ("text/html", "text/plain"):
            return str(self._body)
        raise NotImplementedError

    async def json(
        self, /, **kwargs: Any
    ) -> dict | list:  # assumes is JSON or plaintext
        """Return the response body as json (a dict)."""
        if self.content_type == "application/json":
            return self._body  # type: ignore[return-value]
        assert not isinstance(self._body, (dict | list))  # mypy
        return json.loads(self._body)  # type: ignore[no-any-return]

    async def __aenter__(self, *args: Any, **kwargs: Any) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def __await__(self) -> Generator[Any, Any, Self]:
        """Make this class awaitable."""
        return self._await_impl().__await__()

    async def _await_impl(self) -> Self:
        """Return the actual result."""
        return self

    async def wait_for_close(self) -> None:
        """Wait for the response to close."""
        pass

    def release(self) -> None:
        """Release the response."""
        pass
