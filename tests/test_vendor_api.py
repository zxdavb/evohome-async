#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations


from datetime import datetime as dt
from http import HTTPStatus
import pytest
import pytest_asyncio

import evohomeasync2 as evo
from evohomeasync2 import URL_BASE

from . import mocked_server as mock

from .helpers import aiohttp, extract_oauth_tokens  # aiohttp may be mocked
from .helpers import credentials as _credentials
from .helpers import session as _session


_global_oauth_tokens: tuple[str, str, dt] = None, None, None


@pytest.fixture()
def credentials():
    return _credentials()


@pytest_asyncio.fixture
async def session():
    try:
        yield _session()
    finally:
        await _session().close()


async def instantiate_client(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    # Authentication
    await client._basic_login()
    _global_oauth_tokens = extract_oauth_tokens(client)

    return client


async def _test_usr_account(
    username: str, password: str, session: None | aiohttp.ClientSession = None
) -> None:
    """Test /userAccount"""

    client = await instantiate_client(username, password, session=session)

    url = "userAccount"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    response, content = await client._client("PUT", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        # assert content["message"].startswith("The requested resource does not")

    url = "userXxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:  # TODO: move, as is not a test specific to this URL, but a general test
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("The requested resource does not")


async def _test_usr_location(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
) -> None:
    """Test location/installationInfo?userId={userId}"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    url = f"location/installationInfo?userId={client.account_info['userId']}"
    # url += "&includeTemperatureControlSystems=True"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    response, content = await client._client("PUT", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        # assert content["message"].startswith("The requested resource does not")

    url += "&includeTemperatureControlSystems=True"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    url = "location/installationInfo"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("No HTTP resource was found")

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("No HTTP resource was found")

    url = "location/installationInfo?userId=xxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 400: Bad Request
        assert exc.status == HTTPStatus.BAD_REQUEST
        # assert content["message"].startswith("Request was bad formatted")


@pytest.mark.asyncio
async def test_usr_account(
    credentials: tuple[str, str], session: aiohttp.ClientSession | mock.ClientSession
) -> None:
    """Test /userAccount"""

    await _test_usr_account(*credentials, session=session)


@pytest.mark.asyncio
async def test_usr_location(
    credentials: tuple[str, str], session: aiohttp.ClientSession | mock.ClientSession
) -> None:
    """Test /location/installationInfo"""

    await _test_usr_location(*credentials, session=session)
