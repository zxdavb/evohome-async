#!/usr/bin/env python3
"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar

import pytest

import evohomeasync as evo0
import evohomeasync2 as evo2

from ..const import (
    _DBG_DISABLE_STRICT_ASSERTS,
    _DBG_USE_REAL_AIOHTTP,
    URL_BASE_V0,
    URL_BASE_V2,
)

if TYPE_CHECKING:
    import voluptuous as vol

if _DBG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .faked_server import aiohttp  # type: ignore[no-redef]

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
            evo0.AuthenticationFailedError,
            evo2.AuthenticationFailedError,
        ) as err:
            if not _DBG_USE_REAL_AIOHTTP:
                raise

            global_auth_failed = True
            pytest.fail(f"Unable to authenticate: {err}")

    return wrapper  # type: ignore[return-value]


# version 1 helpers ###################################################################


async def should_work_v0(
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list | str:
    """Make a request that is expected to succeed."""

    response: dict | list | str

    async with auth._raw_request(method, f"{URL_BASE_V0}/{url}", json=json) as rsp:
        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            response = await rsp.json()
        else:
            response = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK
        except aiohttp.ClientResponseError as err:
            raise AssertionError(f"status={err.status}: {response}") from err

        assert rsp.content_type == content_type

        if rsp.content_type != "application/json":
            assert isinstance(response, str)  # mypy
            return response

        assert isinstance(response, dict | list)  # mypy
        return schema(response) if schema else response


async def should_fail_v0(
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict | list | str:
    """Make a request that is expected to fail."""

    response: dict | list | str

    rsp = await auth._raw_request(method, f"{URL_BASE_V0}/{url}", data=json)

    # need to do this before raise_for_status()
    if rsp.content_type == "application/json":
        response = await rsp.json()
    else:
        response = await rsp.text()

    assert rsp.content_type == content_type, response

    try:  # beware if JSON not passed in (i.e. is None, c.f. should_work())
        rsp.raise_for_status()
    except aiohttp.ClientResponseError as err:
        assert err.status == status, err.status
    else:
        assert False, rsp.status

    if _DBG_DISABLE_STRICT_ASSERTS:
        return response

    if isinstance(response, dict):
        assert "message" in response, response

    elif isinstance(response, list):
        assert "message" in response[0], response[0]

    elif isinstance(response, str):
        assert status in (HTTPStatus.NOT_FOUND,), status
        # '<!DOCTYPE html PUBLIC ... not found ...'

    else:
        assert False, rsp.content_type

    return response


# version 2 helpers ###################################################################


async def should_work_v2(
    auth: evo2.auth.Auth,
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

    response: dict | list | str

    async with auth._raw_request(method, f"{URL_BASE_V2}/{url}", json=json) as rsp:
        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            response = await rsp.json()
        else:
            response = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK
        except aiohttp.ClientResponseError as err:
            raise AssertionError(f"status={err.status}: {response}") from err

        assert rsp.content_type == content_type, response

        if rsp.content_type != "application/json":
            assert isinstance(response, str)  # mypy
            return response

        assert isinstance(response, dict | list)  # mypy
        return schema(response) if schema else response  # may raise vol.Invalid


async def should_fail_v2(
    auth: evo2.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict | list | str:
    """Make a HTTP request and check it fails as expected.

    Used to validate the faked server against a 'real' server.
    """

    response: dict | list | str

    rsp = await auth._raw_request(method, f"{URL_BASE_V2}/{url}", json=json)

    # need to do this before raise_for_status()
    if rsp.content_type == "application/json":
        response = await rsp.json()
    else:
        response = await rsp.text()

    try:  # beware if JSON not passed in (i.e. is None, c.f. should_work())
        rsp.raise_for_status()
    except aiohttp.ClientResponseError as err:
        assert err.status == status, err.status
    else:
        assert False, rsp.status

    assert rsp.content_type == content_type, response

    if _DBG_DISABLE_STRICT_ASSERTS:
        return response

    if isinstance(response, dict):
        assert status in (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), response
        assert "message" in response, response  # sometimes "code" too

    elif isinstance(response, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,  # CommTaskNotFound
            HTTPStatus.UNAUTHORIZED,
        ), response
        assert "message" in response[0], response[0]  # sometimes "code" too

    elif isinstance(response, str):  # 404
        assert status in (HTTPStatus.NOT_FOUND,), status

    else:
        raise AssertionError(f"status={status}: {response}")

    return response


async def wait_for_comm_task_v2(auth: evo2.auth.Auth, task_id: str) -> bool:
    """Wait for a communication task (API call) to complete."""

    # invoke via:
    # async with asyncio.timeout(2):
    #     await wait_for_comm_task()

    rsp: aiohttp.ClientResponse  # TODO: shouldn't be needed; isn't via async with

    url = f"commTasks?commTaskId={task_id}"

    while True:
        rsp = await auth._raw_request(HTTPMethod.GET, f"{URL_BASE_V2}/{url}")

        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            content = await rsp.json()
        else:
            content = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK
        except aiohttp.ClientResponseError as err:
            raise AssertionError(f"status={err.status}: {content}") from err

        assert rsp.content_type == "application/json", content

        task = rsp[0] if isinstance(rsp, list) else rsp

        if task["state"] == "Succeeded":
            return True

        if task["state"] in ("Created", "Running"):
            await asyncio.sleep(0.3)
            continue

        raise AssertionError(f"Unexpected task state: {task}")
