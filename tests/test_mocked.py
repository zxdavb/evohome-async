#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""

import aiohttp
from datetime import datetime as dt
import os
from pathlib import Path
import pytest

import evohomeasync2 as evohome

from mocked_server import aiohttp as mocked_aiohttp
from evohomeasync2.schema import SCH_FULL_CONFIG, SCH_LOCN_STATUS, SCH_USER_ACCOUNT


TEST_DIR = Path(__file__).resolve().parent
WORK_DIR = f"{TEST_DIR}/mocked"


async def _test_vendor_api_calls(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mocked_aiohttp.ClientSession = None,
):
    #
    # STEP 0: Instantiation, NOTE: No API calls invoked during instntiation
    client = evohome.EvohomeClient(username, password, session=session)

    #
    # STEP 1: Authentication (isolated from client.login()), POST /Auth/OAuth/Token
    assert client.access_token is None
    assert client.access_token_expires is None
    assert client.refresh_token is None

    await client._basic_login()

    assert isinstance(client.access_token, str)
    assert isinstance(client.access_token_expires, dt)
    assert isinstance(client.refresh_token, str)

    access_token = client.access_token
    refresh_token = client.refresh_token

    await client._headers()

    assert client.access_token == access_token
    assert client.refresh_token == refresh_token

    if isinstance(session, aiohttp.ClientSession):
        access_token = client.access_token
        refresh_token = client.refresh_token

        await client._basic_login()  # re-authenticate using refresh_token

        assert client.access_token != access_token  # TODO: mocked_server wont do this
        assert client.refresh_token != refresh_token  # TODO: mocked_server wont do this

    #
    # STEP 2: User account,  GET /userAccount...
    assert client.account_info is None

    await client.user_account(force_update=False)  # will update as no access_token

    assert SCH_USER_ACCOUNT(client._user_account)
    assert client.account_info == client._user_account

    await client.user_account()  # wont update as access_token is valid
    await client.user_account(force_update=True)  # will update as forced

    #
    # STEP 3: Installation, GET /location/installationInfo?userId={userId}
    assert client.locations is None
    assert client.installation_info is None

    await client._installation(update_status=False)

    assert SCH_FULL_CONFIG(client._full_config)  # an array of locations
    assert client.installation_info == client._full_config

    assert isinstance(client.system_id, str)
    assert client.locations

    #
    # STEP 4: Status, GET /location/{locationId}/status
    for loc in client.locations:
        loc_status = await loc.status()
        assert SCH_LOCN_STATUS(loc_status)


@pytest.mark.asyncio
async def test_vendor_api_calls():
    username = os.getenv("PYTEST_USERNAME") or "user@gmail.com"
    password = os.getenv("PYTEST_PASSWORD") or "P@ssw0rd!23"

    mocked_server = mocked_aiohttp.MockedServer(None, None)
    session = mocked_aiohttp.ClientSession(mocked_server=mocked_server)

    # session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    try:
        await _test_vendor_api_calls(username, password, session=session)
    finally:
        await session.close()
