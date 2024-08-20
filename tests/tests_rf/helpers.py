#!/usr/bin/env python3
"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from http import HTTPMethod, HTTPStatus
from pathlib import Path
from typing import Final

import voluptuous as vol

import evohomeasync as evo1
import evohomeasync2 as evo2
from evohomeasync2.client import TOKEN_CACHE, TokenManager
from evohomeasync2.const import URL_BASE as URL_BASE_2

from . import _DEBUG_DISABLE_STRICT_ASSERTS, _DEBUG_USE_REAL_AIOHTTP

if _DEBUG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .mocked_server import aiohttp  # type: ignore[no-redef]

    # so we don't pollute a real token cache with fake tokens
    TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tst")  # type: ignore[misc]


_LOGGER = logging.getLogger(__name__)


# version 1 helpers ###################################################################


_global_session_id: str | None = None  # session_id


async def instantiate_client_v1(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> evo1.EvohomeClient:
    """Instantiate a client, and logon to the vendor API."""

    global _global_session_id

    # Instantiation, NOTE: No API calls invoked during instantiation
    evo = evo1.EvohomeClient(
        username,
        password,
        session=session,
        session_id=_global_session_id,
    )

    # Authentication
    await evo._populate_user_data()
    _global_session_id = evo.broker.session_id

    return evo


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
    response = await evo.broker._make_request(method, url, data=json)
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
        response = await evo.broker._make_request(method, url, data=json)
        response.raise_for_status()

    except aiohttp.ClientResponseError as err:
        assert err.status == status, err.status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
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

_global_token_manager: TokenManager | None = None


async def instantiate_client_v2(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession,
    dont_login: bool = False,
) -> evo2.EvohomeClient:
    """Instantiate a client, and logon to the vendor API (cache any tokens)."""

    global _global_token_manager

    if (
        not _global_token_manager
        or _global_token_manager.username != user_credentials[0]
    ):
        _global_token_manager = TokenManager(
            *user_credentials, session, token_cache=TOKEN_CACHE
        )

    await _global_token_manager._load_access_token()

    # Instantiation, NOTE: No API calls invoked during instantiation
    evo = evo2.EvohomeClient(_global_token_manager, session=session)

    # Authentication - dont use evo.broker._login() as
    if dont_login:
        await evo.broker._basic_login()  # will force token refresh
    else:
        await evo.login()  # will use cached tokens, if able
        # will also call evo.user_account(), evo.installation()

    await _global_token_manager.save_access_token(evo)

    return evo


async def should_work(
    evo: evo2.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list | str:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response, content = await evo.broker._client(
        method, f"{URL_BASE_2}/{url}", json=json
    )
    response.raise_for_status()

    assert response.content_type == content_type, content

    if response.content_type != "application/json":
        assert isinstance(content, str), content  # mypy
        return content

    assert isinstance(content, dict | list), content  # mypy
    return schema(content) if schema else content


async def should_fail(
    evo: evo2.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict | list | str | None:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response, content = await evo.broker._client(
        method, f"{URL_BASE_2}/{url}", json=json
    )

    try:
        response.raise_for_status()

    except aiohttp.ClientResponseError as err:
        assert err.status == status, err.status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
        return None

    assert response.content_type == content_type, response.content_type

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

    return content


async def wait_for_comm_task_v2(evo: evo2.EvohomeClient, task_id: str) -> bool | None:
    """Wait for a communication task (API call) to complete."""

    # invoke via:
    # async with asyncio.timeout(2):
    #     await wait_for_comm_task()

    await asyncio.sleep(0.5)

    url = f"commTasks?commTaskId={task_id}"

    while True:
        response = await should_work(evo, HTTPMethod.GET, url)
        assert isinstance(response, dict | list), response
        if response["state"] == "Succeeded":  # type: ignore[call-overload]
            return True
        if response["state"] in ("Created", "Running"):  # type: ignore[call-overload]
            await asyncio.sleep(0.3)
            continue
        else:
            # raise RuntimeError(f"Unexpected state: {response['state']}")
            _LOGGER.warning(f"Unexpected state: {response['state']}")  # type: ignore[call-overload]
