#!/usr/bin/env python3
"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TypedDict

import voluptuous as vol

import evohomeasync as evo1
import evohomeasync2 as evo2
from evohomeasync2.const import URL_BASE as URL_BASE_2
from evohomeasync2.schema.account import (
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_REFRESH_TOKEN,
)

from . import _DEBUG_DISABLE_STRICT_ASSERTS, _DEBUG_USE_REAL_AIOHTTP

if _DEBUG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .mocked_server import aiohttp  # type: ignore[no-redef]


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
) -> dict | list:
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

    if schema:  # and response.content_type == "application/json"
        return schema(content)
    return content


async def should_fail_v1(
    evo: evo1.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    try:
        # unlike _make_request(), make_request() incl. raise_for_status()
        response = await evo.broker._make_request(method, url, data=json)
        response.raise_for_status()

    except aiohttp.ClientResponseError as exc:
        assert exc.status == status, exc.status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
        return response

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

    return content


# version 2 helpers ###################################################################


class OAuthTokensT(TypedDict):
    refresh_token: str | None
    access_token: str | None
    access_token_expires: dt | None


# OAuth tokens used by EvohomeClient2
_global_oauth_tokens: OAuthTokensT = {
    SZ_REFRESH_TOKEN: None,
    SZ_ACCESS_TOKEN: None,
    SZ_ACCESS_TOKEN_EXPIRES: None,
}


def update_oauth_tokens(evo: evo2.EvohomeClient) -> None:
    """Save the global OAuth tokens for later use (for EvohomeClient2).

    The tokens are used to stop tests from exceeding rate limits of authentication APIs.
    """

    global _global_oauth_tokens

    old_dict = _global_oauth_tokens.copy()

    _global_oauth_tokens[SZ_REFRESH_TOKEN] = evo.refresh_token
    _global_oauth_tokens[SZ_ACCESS_TOKEN] = evo.access_token
    _global_oauth_tokens[SZ_ACCESS_TOKEN_EXPIRES] = evo.access_token_expires

    if _global_oauth_tokens != old_dict:
        _LOGGER.warning("BEFORE: %s", old_dict)
        _LOGGER.warning("AFTER_: %s", _global_oauth_tokens)


async def instantiate_client(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession,
    dont_login: bool = False,
) -> evo2.EvohomeClient:
    """Instantiate a client, and logon to the vendor API (cache any tokens)."""

    global _global_oauth_tokens

    # Instantiation, NOTE: No API calls invoked during instantiation
    evo = evo2.EvohomeClient(
        *user_credentials,
        session=session,
        **_global_oauth_tokens,
    )

    # Authentication - dont use evo.broker._login() as
    if dont_login:
        await evo.broker._basic_login()  # will force token refresh
    else:
        await evo.login()  # will use cached tokens, if able
        # will also call evo.user_account(), evo.installation()

    update_oauth_tokens(evo)

    return evo


async def should_work(
    evo: evo2.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response, content = await evo.broker._client(
        method, f"{URL_BASE_2}/{url}", json=json
    )

    response.raise_for_status()

    assert response.content_type == content_type, content

    if schema:
        return schema(content)

    assert isinstance(content, dict | list), content
    return content


async def should_fail(
    evo: evo2.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    # if method == HTTPMethod.GET:
    #     content = await evo.broker.get(
    # else:
    #     content = await evo.broker.put(

    response, content = await evo.broker._client(
        method, f"{URL_BASE_2}/{url}", json=json
    )

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status, exc.status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
        return response

    assert response.content_type == content_type, response.content_type

    if isinstance(content, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,  # CommTaskNotFound
            HTTPStatus.UNAUTHORIZED,
        ), content
        assert "message" in content[0], content[0]  # sometimes "code" too

    elif isinstance(content, dict):
        assert status in (
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), content
        assert "message" in content, content  # sometimes "code" too

    elif isinstance(content, str):  # 404
        assert status in (HTTPStatus.NOT_FOUND,), status

    else:
        assert False, response.status

    return response


async def wait_for_comm_task(
    evo: evo2.EvohomeClient,
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
