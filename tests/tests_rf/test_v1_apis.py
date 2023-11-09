#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations

from http import HTTPMethod, HTTPStatus

import pytest
import pytest_asyncio

import evohomeasync as evo
from evohomeasync.broker import URL_HOST

# FIXME: need v1 schemas
from evohomeasync2.schema import vol  # type: ignore[import-untyped]

from . import _DEBUG_USE_REAL_AIOHTTP, _DISABLE_STRICT_ASSERTS
from .helpers import (
    aiohttp,  # aiohttp may be mocked
    client_session as _client_session,
    user_credentials as _user_credentials,
)

URL_BASE = f"{URL_HOST}/WebAPI/api"


_global_user_data: tuple[dict, str] = None, None


@pytest.fixture()
def user_credentials():
    return _user_credentials()


@pytest_asyncio.fixture
async def session():
    client_session = _client_session()
    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("evohomeasync.client.aiohttp", aiohttp)


async def instantiate_client(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_user_data

    # refresh_token, access_token, access_token_expires = _global_user_data

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        user_data=_global_user_data,
    )

    # Authentication
    await client._populate_user_data()
    _global_user_data = client.user_data

    return client


async def should_work(  # type: ignore[no-any-unimported]
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response = await client._do_request(method, f"{URL_BASE}/{url}", data=json)

    response.raise_for_status()

    assert True or response.content_type == content_type

    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

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

    response = await client._do_request(method, f"{URL_BASE}/{url}", data=json)

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False, response.status

    if _DISABLE_STRICT_ASSERTS:
        return response

    assert True or response.content_type == content_type

    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

    if isinstance(content, dict):
        assert True or "message" in content
    elif isinstance(content, list):
        assert True or "message" in content[0]

    return content


async def _test_client_apis(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_user_data

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        user_data=_global_user_data,
    )

    user_data = await client._populate_user_data()
    assert user_data == client.user_data

    _global_user_data = client.user_data, client.broker.session_id

    full_data = await client._populate_full_data()
    assert full_data == client.full_data

    temps = await client.temperatures()
    assert temps


@pytest.mark.asyncio
async def test_client_apis(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test _populate_user_data() & _populate_full_data()"""

    if not _DEBUG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented")

    try:
        await _test_client_apis(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        pytest.skip("Unable to authenticate")
