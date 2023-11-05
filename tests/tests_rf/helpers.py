#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config, status & schedule schemas."""
from __future__ import annotations

import asyncio
from datetime import datetime as dt
import logging
import os
from http import HTTPMethod, HTTPStatus

import evohomeasync2 as evo
from evohomeasync2.const import URL_BASE
from evohomeasync2.schema import vol  # voluptuous

from . import _DISABLE_STRICT_ASSERTS, _DEBUG_USE_MOCK_AIOHTTP
from . import mocked_server as mock


if _DEBUG_USE_MOCK_AIOHTTP:
    from .mocked_server import aiohttp
else:
    import aiohttp


_LOGGER = logging.getLogger(__name__)


def user_credentials():
    username = os.getenv("PYTEST_USERNAME")
    password = os.getenv("PYTEST_PASSWORD")

    # with open() as f:
    #     lines = f.readlines()
    # username = lines[0].strip()
    # password = lines[1].strip()

    return username, password


def client_session():
    if not _DEBUG_USE_MOCK_AIOHTTP:
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return aiohttp.ClientSession(mocked_server=mock.MockedServer(None, None))


def extract_oauth_tokens(client: evo.EvohomeClient):
    return (
        client.refresh_token,
        client.access_token,
        client.access_token_expires,
    )


async def should_work(
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response, content = await client._broker._client(
        method, f"{URL_BASE}/{url}", json=json
    )

    response.raise_for_status()

    assert response.content_type == content_type

    if schema:
        return schema(content)
    return content


async def should_fail(
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response, content = await client._broker._client(
        method, f"{URL_BASE}/{url}", json=json
    )

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False, response.status

    if _DISABLE_STRICT_ASSERTS:
        return response

    assert response.content_type == content_type

    if isinstance(content, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
        ), response.status
        assert "message" in content[0]  # sometimes "code" too

    elif isinstance(content, dict):
        assert status in (
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), response.status
        assert "message" in content  # sometimes "code" too

    elif isinstance(content, str):  # 404
        assert status in (HTTPStatus.NOT_FOUND,), response.status

    else:
        assert False, response.status

    return response


async def wait_for_comm_task(
    client: evo.EvohomeClient,
    task_id: str,
    timeout: int = 3,
) -> None:
    """Wait for a communication task (API call) to complete."""

    await asyncio.sleep(0.5)

    url = f"commTasks?commTaskId={task_id}"

    start_time = dt.now()
    while True:
        response = await should_work(client, HTTPMethod.GET, url)
        if response["state"] == "Succeeded":
            return True
        if (dt.now() - start_time).total_seconds() > timeout:
            return False
        if response["state"] in ("Created", "Running"):
            await asyncio.sleep(0.3)
            continue
        else:
            # raise RuntimeError(f"Unexpected state: {response['state']}")
            _LOGGER.warning(f"Unexpected state: {response['state']}")
