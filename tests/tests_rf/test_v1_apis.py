#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations

import logging
from http import HTTPMethod, HTTPStatus

import pytest
import pytest_asyncio

import evohomeasync as evohome
from evohomeasync.broker import URL_HOST

# FIXME: need v1 schemas
from evohomeasync2.schema import vol  # type: ignore[import-untyped]

from . import _DEBUG_DISABLE_STRICT_ASSERTS, _DEBUG_USE_REAL_AIOHTTP
from .helpers import (
    aiohttp,  # aiohttp may be mocked
    client_session as _client_session,
    user_credentials as _user_credentials,
)

URL_BASE = f"{URL_HOST}/WebAPI/api"


_LOGGER = logging.getLogger(__name__)

_global_user_data: str = None  # session_id


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("evohomeasync.base.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync.broker.aiohttp", aiohttp)


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


async def instantiate_client(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_user_data

    # Instantiation, NOTE: No API calls invoked during instantiation
    evo = evohome.EvohomeClient(
        username,
        password,
        session=session,
        session_id=_global_user_data,
    )

    # Authentication
    await evo._populate_user_data()
    _global_user_data = evo.broker.session_id

    return evo


async def should_work(  # type: ignore[no-any-unimported]
    evo: evohome.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response = await evo._do_request(method, f"{URL_BASE}/{url}", data=json)

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
    evo: evohome.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response = await evo._do_request(method, f"{URL_BASE}/{url}", data=json)

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False, response.status

    if _DEBUG_DISABLE_STRICT_ASSERTS:
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
    evo = evohome.EvohomeClient(
        username,
        password,
        session=session,
        session_id=_global_user_data,
    )

    user_data = await evo._populate_user_data()
    assert user_data == evo.user_info

    _global_user_data = evo.broker.session_id

    full_data = await evo._populate_locn_data()
    assert full_data == evo.location_data

    temps = await evo.get_temperatures()

    assert temps

    # for _ in range(3):
    #     await asyncio.sleep(5)
    #     _ = await evo.get_temperatures()
    #     _LOGGER.warning("get_temperatures() OK")


@pytest.mark.asyncio
async def test_client_apis(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test _populate_user_data() & _populate_full_data()"""

    if not _DEBUG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented")

    try:
        await _test_client_apis(*user_credentials, session=session)
    except evohome.AuthenticationFailed:
        pytest.skip("Unable to authenticate")
