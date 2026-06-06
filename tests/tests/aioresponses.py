"""Minimal aioresponses-compatible mocker for aiohttp.ClientSession.

Drop-in replacement for the aioresponses library, limited to the subset of its
API used by this test suite. The interface is intentionally identical so that
reverting to the real aioresponses package only requires changing the import.

Motivation: aioresponses constructs aiohttp.ClientResponse directly. aiohttp
3.14 made stream_writer a required constructor argument, breaking that approach.
This mocker avoids the problem by returning a duck-typed stub instead.
"""

from __future__ import annotations

import json
from collections import defaultdict
from http import HTTPMethod, HTTPStatus
from typing import Any, Self
from unittest.mock import patch

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL


class _MockResponse:
    """Duck-typed aiohttp.ClientResponse stub."""

    def __init__(self, method: str, url: str, status: int, payload: Any) -> None:
        self.method = method
        self.url = URL(url)
        self.status = status
        self._payload = payload
        self.content_type = "application/json"
        self.headers: CIMultiDictProxy[str] = CIMultiDictProxy(CIMultiDict())

    async def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    async def json(self, *, content_type: str | None = "application/json") -> Any:
        return self._payload

    async def text(self) -> str:
        return json.dumps(self._payload)

    def release(self) -> None:
        pass

    def raise_for_status(self) -> None:
        if self.status >= 400:  # noqa: PLR2004
            raise aiohttp.ClientResponseError(
                aiohttp.RequestInfo(
                    url=self.url,
                    method=self.method,
                    headers=CIMultiDictProxy(CIMultiDict()),
                    real_url=self.url,
                ),
                history=(),
                status=self.status,
                message=HTTPStatus(self.status).phrase,
            )


class AioResponses:
    """Minimal aioresponses-compatible context manager.

    Usage mirrors the real aioresponses library:

        with aioresponses() as rsp:
            rsp.post(url, status=200, payload={...})
            ...
            rsp.assert_called_once_with(url, HTTPMethod.POST, headers=..., data=...)
    """

    def __init__(self) -> None:
        self._registered: dict[tuple[str, str], list[_MockResponse]] = defaultdict(list)
        self.requests: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self._patcher: Any = None

    def _key(self, method: str | HTTPMethod, url: str | URL) -> tuple[str, str]:
        return (str(method).upper(), str(URL(str(url))))

    def __enter__(self) -> Self:
        self._patcher = patch(
            "aiohttp.client.ClientSession._request",
            side_effect=self._handle_request,
        )
        self._patcher.start()
        return self

    def __exit__(self, *args: object) -> None:
        if self._patcher is not None:
            self._patcher.stop()

    async def _handle_request(
        self,
        method: str,
        str_or_url: str | URL,
        **kwargs: Any,
    ) -> _MockResponse:
        key = self._key(method, str_or_url)
        self.requests[key].append(kwargs)

        if self._registered[key]:
            return self._registered[key].pop(0)

        raise aiohttp.ClientConnectionError(
            f"Connection refused: {method} {str_or_url}"
        )

    def _register(
        self,
        method: str,
        url: str,
        *,
        status: int | HTTPStatus = HTTPStatus.OK,
        payload: Any = None,
    ) -> None:
        key = self._key(method, url)
        self._registered[key].append(
            _MockResponse(method.upper(), url, int(status), payload)
        )

    def get(
        self, url: str, *, status: int | HTTPStatus = HTTPStatus.OK, payload: Any = None
    ) -> None:
        self._register("GET", url, status=status, payload=payload)

    def post(
        self, url: str, *, status: int | HTTPStatus = HTTPStatus.OK, payload: Any = None
    ) -> None:
        self._register("POST", url, status=status, payload=payload)

    def _call_matches(self, actual: dict[str, Any], expected: dict[str, Any]) -> bool:
        return all(actual.get(k) == v for k, v in expected.items())

    def assert_called_once_with(
        self, url: str, method: str | HTTPMethod, **kwargs: Any
    ) -> None:
        total = sum(len(calls) for calls in self.requests.values())
        assert total == 1, f"Expected exactly 1 call, got {total}"
        self.assert_any_call(url, method, **kwargs)

    def assert_called_with(
        self, url: str, method: str | HTTPMethod, **kwargs: Any
    ) -> None:
        self.assert_any_call(url, method, **kwargs)

    def assert_any_call(
        self, url: str, method: str | HTTPMethod, **kwargs: Any
    ) -> None:
        key = self._key(method, url)
        calls = self.requests.get(key, [])
        assert calls, f"No calls made to {method} {url}"
        assert any(self._call_matches(c, kwargs) for c in calls), (
            f"No call to {method} {url} matched kwargs {kwargs}.\nActual: {calls}"
        )


aioresponses = AioResponses
