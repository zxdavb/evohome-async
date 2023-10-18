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
from evohomeasync2.schema import (
    SCH_DHW_STATUS,
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_ZONE_STATUS,
)


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
    # STEP 2: User account,  GET /userAccount...
    assert client.account_info is None

    await client.user_account(force_update=False)  # will update as no access_token

    assert SCH_USER_ACCOUNT(client._user_account)
    assert client.account_info == client._user_account

    await client.user_account()  # wont update as access_token is valid
    await client.user_account(force_update=True)  # will update as forced

    #
    # STEP 3: Installation, GET /location/installationInfo?userId={userId}
    assert client.locations == []
    assert client.installation_info is None

    await client._installation(refresh_status=False)

    assert SCH_FULL_CONFIG(client._full_config)  # an array of locations
    assert client.installation_info == client._full_config

    assert isinstance(client.system_id, str)
    assert client.locations

    #
    # STEP 4: Status, GET /location/{locationId}/status
    for loc in client.locations:
        loc_status = await loc.refresh_status()
        assert SCH_LOCN_STATUS(loc_status)

    #
    # STEP 6: Status, GET /domesticHotWater/{dhwId}/status?
    if dhw := client._get_single_heating_system().hotwater:
        dhw_status = await dhw.refresh_status()
        assert SCH_DHW_STATUS(dhw_status)

    #
    # STEP 5: Status, GET /temperatureZone/{ZoneId}/status?
    if zone := client._get_single_heating_system()._zones[0]:
        zone_status = await zone.refresh_status()
        assert SCH_ZONE_STATUS(zone_status)


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
