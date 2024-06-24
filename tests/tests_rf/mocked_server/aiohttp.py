#!/usr/bin/env python3
"""Hacked aiohttp to provide a mocked server."""

from __future__ import annotations

import asyncio
import json
from enum import EnumCheck, StrEnum, verify
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, Self

if TYPE_CHECKING:
    from asyncio.streams import _ReaduntilBuffer

    from .const import _bodyT, _methodT, _statusT, _urlT
    from .vendor import MockedServer


_DEFAULT_LIMIT = 2**16  # 64 KiB


@verify(EnumCheck.UNIQUE)
class hdrs(StrEnum):  # a la aiohttp
    METH_GET: Final = "GET"
    METH_POST: Final = "POST"
    METH_PUT: Final = "PUT"


class StreamReader(asyncio.StreamReader):
    _buffer = bytearray()

    def __init__(self, limit=_DEFAULT_LIMIT, loop=None):
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

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass


class ClientError(Exception):
    """Base class for client connection errors."""


class ClientResponseError(ClientError):
    """Base class for exceptions that occur after getting a response."""

    def __init__(self, msg, /, *, status: int | None = None, **kwargs) -> None:
        super().__init__(msg)
        self.status = status


class ClientTimeout:
    """"""

    def __init__(self, /, *, total: float | None = None, **kwargs) -> None:
        self.total: float = total or 30


class ClientSession:
    """First-class interface for making HTTP requests."""

    def __init__(self, /, *, timeout: ClientTimeout | None = None, **kwargs) -> None:
        self._timeout = timeout or ClientTimeout()

        # this is required, so no .get()
        self._mocked_server: MockedServer = kwargs["mocked_server"]

    def get(self, url, /, headers: str | None = None):
        return ClientResponse(hdrs.METH_GET, url, session=self)  # type: ignore[arg-type]

    def put(
        self, url, /, *, data: Any = None, json: Any = None, headers: str | None = None
    ):
        return ClientResponse(hdrs.METH_PUT, url, data=data or json, session=self)  # type: ignore[arg-type]

    def post(self, url, /, *, data: Any = None, headers: str | None = None):
        return ClientResponse(hdrs.METH_POST, url, data=data, session=self)  # type: ignore[arg-type]

    async def close(self) -> None:
        pass


class ClientResponse:
    """"""

    charset: str = "utf-8"

    def __init__(
        self,
        method: _methodT,
        url: _urlT,
        /,
        *,
        data: str | None = None,
        json: dict | None = None,
        session: ClientSession | None = None,
        **kwargs,
    ) -> None:
        self.method = method
        self.url = url
        self.session = session

        assert self.session is not None  # mypy
        self._mocked_server = self.session._mocked_server

        self.status: _statusT = None  # type: ignore[assignment]
        self._body: _bodyT | None = None

        # self.content = StreamReader(
        #     self._mocked_server.request(method, url, data=data or json)
        # )
        self._body = self._mocked_server.request(method, url, data=data or json)
        self.status = self._mocked_server.status  # type: ignore[assignment]

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

    async def text(self, /, **kwargs) -> str:  # assumes is JSON or plaintext
        """Return the response body as text."""
        if self.content_type == "application/json":
            return json.dumps(self._body)
        if self.content_type in ("text/html", "text/plain"):
            return self._body
        raise NotImplementedError

    async def json(self, /, **kwargs) -> dict | list:  # assumes is JSON or plaintext
        """Return the response body as json (a dict)."""
        if self.content_type == "application/json":
            return self._body
        assert not isinstance(self._body, (dict | list))  # mypy
        return json.loads(self._body)

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass
