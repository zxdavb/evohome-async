#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config, status & schedule schemas."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus

import voluptuous as vol

import evohomeasync2 as evohome
from evohomeasync2.const import URL_BASE

from . import _DEBUG_DISABLE_STRICT_ASSERTS, _DEBUG_USE_REAL_AIOHTTP
from .mocked_server import MockedServer

if _DEBUG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .mocked_server import aiohttp  # type: ignore[no-redef]


_LOGGER = logging.getLogger(__name__)


def user_credentials():
    username = os.getenv("PYTEST_USERNAME")
    password = os.getenv("PYTEST_PASSWORD")

    return username, password


def client_session():
    if _DEBUG_USE_REAL_AIOHTTP:
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return aiohttp.ClientSession(mocked_server=MockedServer(None, None))


def extract_oauth_tokens(evo: evohome.EvohomeClient):
    return (
        evo.refresh_token,
        evo.access_token,
        evo.access_token_expires,
    )


async def should_work(
    evo: evohome.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response, content = await evo.broker._client(method, f"{URL_BASE}/{url}", json=json)

    response.raise_for_status()

    assert response.content_type == content_type

    if schema:
        return schema(content)
    return content


async def should_fail(
    evo: evohome.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response, content = await evo.broker._client(method, f"{URL_BASE}/{url}", json=json)

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
        return response

    assert response.content_type == content_type

    if isinstance(content, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,  # CommTaskNotFound
            HTTPStatus.UNAUTHORIZED,
        ), content
        assert "message" in content[0]  # sometimes "code" too

    elif isinstance(content, dict):
        assert status in (
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), content
        assert "message" in content  # sometimes "code" too

    elif isinstance(content, str):  # 404
        assert status in (HTTPStatus.NOT_FOUND,), content

    else:
        assert False, response.status

    return response


async def wait_for_comm_task(
    evo: evohome.EvohomeClient,
    task_id: str,
    timeout: int = 3,
) -> bool | None:
    """Wait for a communication task (API call) to complete."""

    await asyncio.sleep(0.5)

    url = f"commTasks?commTaskId={task_id}"

    start_time = dt.now()
    while True:
        response = await should_work(evo, HTTPMethod.GET, url)
        if response["state"] == "Succeeded":  # type: ignore[call-overload]
            return True
        if (dt.now() - start_time).total_seconds() > timeout:
            return False
        if response["state"] in ("Created", "Running"):  # type: ignore[call-overload]
            await asyncio.sleep(0.3)
            continue
        else:
            # raise RuntimeError(f"Unexpected state: {response['state']}")
            _LOGGER.warning(f"Unexpected state: {response['state']}")  # type: ignore[call-overload]
