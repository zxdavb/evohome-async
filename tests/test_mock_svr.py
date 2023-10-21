#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config, status & schedule schemas."""
from __future__ import annotations

import aiohttp
from datetime import datetime as dt
import pytest
import pytest_asyncio

import evohomeasync2 as evo
import mocked_server as mock

from .helpers import credentials as _credentials
from .helpers import session as _session
from .helpers import extract_oauth_tokens


_global_oauth_tokens: tuple[str, str, dt] = None, None, None


@pytest.fixture()
def credentials():
    return _credentials()


@pytest_asyncio.fixture
async def session():
    try:
        yield _session
    finally:
        await _session.close()


async def _test_vendor_api(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
):
    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    #
    # STEP 0: Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    #
    # STEP 1: Authentication (isolated from client.login()), POST /Auth/OAuth/Token
    await client._basic_login()
    _global_oauth_tokens = extract_oauth_tokens(client)

    assert isinstance(client.access_token, str)
    assert isinstance(client.access_token_expires, dt)
    assert isinstance(client.refresh_token, str)

    access_token = client.access_token
    refresh_token = client.refresh_token

    await client._headers()

    # The above should not cause a re-authentication, so...
    assert client.access_token == access_token
    assert client.refresh_token == refresh_token

    #
    # STEP 1A: Re-Authentication: more likely to cause 429: Too Many Requests
    if isinstance(session, aiohttp.ClientSession):
        access_token = client.access_token
        refresh_token = client.refresh_token

    #     await client._basic_login()  # re-authenticate using refresh_token

    #     assert True or client.access_token != access_token  # TODO: mocked_server wont do this
    #     assert True or client.refresh_token != refresh_token  # TODO: mocked_server wont do this

    #


@pytest.mark.asyncio
async def test_vendor_api(
    credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
):
    username, password = credentials

    await _test_vendor_api(username, password, session=session)
