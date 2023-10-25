#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Hacked aiohttp to provide a mocked server."""
from __future__ import annotations

import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self, Type

import json

from .const import hdrs
from .vendor import MockedServer


if TYPE_CHECKING:
    from .const import _bodyT, _methodT, _statusT, _urlT


_DEFAULT_LIMIT = 2**16  # 64 KiB


class StreamReader(asyncio.StreamReader):
    _buffer: bytearray = b""

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

    async def readuntil(self, separator: bytes = b"\n") -> bytes:
        """Read data from the stream until ``separator`` is found."""
        raise NotImplementedError

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: None | Type[BaseException],
        exc_val: None | BaseException,
        exc_tb: None | TracebackType,
    ) -> None:
        pass


class ClientError(Exception):
    """Base class for client connection errors."""


class ClientResponseError(ClientError):
    """Base class for exceptions that occur after getting a response."""

    def __init__(self, msg, /, *, status: None | int = None, **kwargs) -> None:
        super().__init__(msg)
        self.status: int = status


class ClientTimeout:
    """"""

    def __init__(self, /, *, total: None | float = None, **kwargs) -> None:
        self.total: float = total or 30


class ClientSession:
    """First-class interface for making HTTP requests."""

    def __init__(self, /, *, timeout: None | ClientTimeout = None, **kwargs) -> None:
        self._timeout = timeout or ClientTimeout()

        # this is required, so no .get()
        self._mocked_server: MockedServer = kwargs["mocked_server"]

    def get(self, url, /, headers: None | str = None):
        return ClientResponse(hdrs.METH_GET, url, session=self)

    def put(
        self, url, /, *, data: Any = None, json: Any = None, headers: None | str = None
    ):
        return ClientResponse(hdrs.METH_PUT, url, data=data or json, session=self)

    def post(self, url, /, *, data: Any = None, headers: None | str = None):
        return ClientResponse(hdrs.METH_POST, url, data=data, session=self)

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
        data: None | str = None,
        json: None | str = None,
        session: None | ClientSession = None,
        **kwargs,
    ) -> None:
        self.method = method
        self.url = url
        self.session = session

        self._mocked_server = self.session._mocked_server

        self.status: _statusT = None
        self._body: None | _bodyT = None

        # self.content = StreamReader(
        #     self._mocked_server.request(method, url, data=data or json)
        # )
        self._body = self._mocked_server.request(method, url, data=data or json)
        self.status = self._mocked_server.status

    def raise_for_status(self) -> None:
        if self.status >= 300:
            raise ClientResponseError(
                f"{self.method} {self.url}: {self.status}", status=self.status
            )

    @property
    def content_length(self) -> None | int:
        if self._body is None:
            return None
        if self.content_type == "text/plain":
            return len(self._body)
        return len(str(self._body))

    @property
    def content_type(self) -> None | str:
        """Return the Content-Type header of the response."""
        # if isinstance(self._body, bytes):
        #     return "application/octet-stream"
        if isinstance(self._body, (dict, list)):
            return "application/json"
        if isinstance(self._body, str):
            return "text/plain"

    async def text(self, /, **kwargs) -> str:  # assumes is JSON or plaintext
        """Return the response body as text."""
        if self.content_type == "text/plain":
            return self._body
        return json.dumps(self._body)

    async def json(self, /, **kwargs) -> dict | list:  # assumes is JSON or plaintext
        """Return the response body as json (a dict)."""
        if self.content_type == "application/json":
            return self._body
        return json.loads(self._body)

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: None | Type[BaseException],
        exc_val: None | BaseException,
        exc_tb: None | TracebackType,
    ) -> None:
        pass
