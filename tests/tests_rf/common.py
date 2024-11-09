#!/usr/bin/env python3
"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from pathlib import Path
from typing import Any, Final, TypeVar

import aiohttp
import pytest
import voluptuous as vol

import evohomeasync as evo1
import evohomeasync2 as evo2
from evohomeasync2.auth import URL_BASE as URL_BASE_2, Auth

from .const import _DBG_DISABLE_STRICT_ASSERTS, _DBG_USE_REAL_AIOHTTP

_FNC = TypeVar("_FNC", bound=Callable[..., Any])


# Global flag to indicate if AuthenticationFailedError has been encountered
global_auth_failed = False


# decorator to skip remaining tests if an AuthenticationFailedError is encountered
def skipif_auth_failed(fnc: _FNC) -> _FNC:
    """Decorator to skip tests if AuthenticationFailedError is encountered."""

    @functools.wraps(fnc)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        global global_auth_failed

        if global_auth_failed:
            pytest.skip("Unable to authenticate")

        try:
            return await fnc(*args, **kwargs)

        except (
            evo1.AuthenticationFailedError,
            evo2.AuthenticationFailedError,
        ) as err:
            if not _DBG_USE_REAL_AIOHTTP:
                raise

            global_auth_failed = True
            pytest.fail(f"Unable to authenticate: {err}")

    return wrapper  # type: ignore[return-value]


# version 1 helpers ###################################################################


class SessionManager(evo1.Auth):
    """An evohomeasync session manager."""

    def __init__(
        self,
        client_id: str,
        secret: str,
        websession: aiohttp.ClientSession,
        /,
        token_cache: Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the session manager."""
        super().__init__(client_id, secret, websession, **kwargs)

        self._token_cache: Final = token_cache

    async def save_session_id(self) -> None:
        """Save the (serialized) session id to a cache."""

    async def load_session_id(self) -> None:
        """Save the (serialized) session id from a cache."""


async def should_work_v1(
    evo: evo1.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list | str:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    # unlike _make_request(), make_request() incl. raise_for_status()
    response = await evo.auth.request(method, url, data=json)
    response.raise_for_status()

    # TODO: perform this transform in the broker
    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

    assert response.content_type == content_type, content

    if response.content_type != "application/json":
        assert isinstance(content, str), content  # mypy
        return content

    assert isinstance(content, dict | list), content  # mypy
    return schema(content) if schema else content


async def should_fail_v1(
    evo: evo1.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict | list | str | None:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    try:
        # unlike _make_request(), make_request() incl. raise_for_status()
        response = await evo.auth.request(method, url, data=json)
        response.raise_for_status()

    except aiohttp.ClientResponseError as err:
        assert err.status == status, err.status
    else:
        assert False, response.status

    if _DBG_DISABLE_STRICT_ASSERTS:
        return None

    # TODO: perform this transform in the broker
    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

    assert response.content_type == content_type, content

    if isinstance(content, dict):
        assert "message" in content, content
    elif isinstance(content, list):
        assert "message" in content[0], content[0]
    elif isinstance(content, str):
        pass
    else:
        assert False, response.content_type

    return content  # type: ignore[no-any-return]


# version 2 helpers ###################################################################


async def should_work(
    evo: evo2.EvohomeClientNew,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list | str:
    """Make a HTTP request and check it succeeds as expected.

    Used to validate the faked server against a 'real' server.
    """

    response = await evo.auth.request(method, f"{URL_BASE_2}/{url}", json=json)

    content = await Auth._content(response)
    assert response.content_type == content_type, content

    if response.content_type != "application/json":
        assert isinstance(content, str), content  # mypy
        return content

    assert isinstance(content, dict | list), content  # mypy
    return schema(content) if schema else content


async def should_fail(
    evo: evo2.EvohomeClientNew,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict | list | str | None:
    """Make a HTTP request and check it fails as expected.

    Used to validate the faked server against a 'real' server.
    """

    try:  # beware if JSON not passed in (i.e. is None, c.f. should_work())
        response = await evo.auth.request(method, f"{URL_BASE_2}/{url}", json=json)

    except aiohttp.ClientResponseError:
        assert False  # err.status == status, err.status
    else:
        assert response.status == status, response.status

    if _DBG_DISABLE_STRICT_ASSERTS:
        return None

    content = await Auth._content(response)
    assert response.content_type == content_type, content

    if isinstance(content, dict):
        assert status in (
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), content
        assert "message" in content, content  # sometimes "code" too

    elif isinstance(content, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,  # CommTaskNotFound
            HTTPStatus.UNAUTHORIZED,
        ), content
        assert "message" in content[0], content[0]  # sometimes "code" too

    elif isinstance(content, str):  # 404
        assert status in (HTTPStatus.NOT_FOUND,), status

    else:
        assert False, response.content_type

    assert isinstance(content, dict | list | str), content

    return content


async def wait_for_comm_task_v2(evo: evo2.EvohomeClientNew, task_id: str) -> bool:
    """Wait for a communication task (API call) to complete."""

    # invoke via:
    # async with asyncio.timeout(2):
    #     await wait_for_comm_task()

    await asyncio.sleep(0.5)

    url = f"commTasks?commTaskId={task_id}"

    while True:
        response = await should_work(evo, HTTPMethod.GET, url)
        assert isinstance(response, dict | list), response

        task = response[0] if isinstance(response, list) else response

        if task["state"] == "Succeeded":
            return True

        if task["state"] in ("Created", "Running"):
            await asyncio.sleep(0.3)
            continue

        raise RuntimeError(f"Unexpected state: {task['state']}")
