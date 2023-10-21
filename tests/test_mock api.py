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
from evohomeasync2.schema import (
    SCH_DHW_STATUS,
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_ZONE_STATUS,
)
from evohomeasync2.schema import (  # noqa: F401
    DhwState,
    SystemMode,
    ZoneMode,
    DHW_STATES,
    SYSTEM_MODES,
    ZONE_MODES,
)
from evohomeasync2.schema.const import SZ_MODE
from evohomeasync2.schema.schedule import SCH_SCHEDULE_PUT

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


async def _test_vendor_api_basics(
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
    # STEP 2: User account,  GET /userAccount...
    assert client.account_info is None

    await client.user_account(force_update=False)  # will update as no access_token

    assert SCH_USER_ACCOUNT(client._user_account)
    assert client.account_info == client._user_account

    await client.user_account()  # wont update as access_token is valid
    # await client.user_account(force_update=True)  # will update as forced

    #
    # STEP 3: Installation, GET /location/installationInfo?userId={userId}
    assert client.locations == []
    assert client.installation_info is None

    await client._installation(refresh_status=False)  # not client.installation()

    assert SCH_FULL_CONFIG(client._full_config)  # an array of locations
    assert client.installation_info == client._full_config

    # assert isinstance(client.system_id, str)  # only if one TCS
    assert client.locations

    await client.installation()  # not client._installation()
    # await client.installation(force_update=True)  # will update as forced

    #
    # STEP 4: Status, GET /location/{locationId}/status
    for loc in client.locations:
        loc_status = await loc.refresh_status()
        assert SCH_LOCN_STATUS(loc_status)

    pass


async def _test_vendor_api_sched_(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
):
    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    #
    # STEP 0: Instantiation...
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    #
    # STEP 1: Initial authentication, retrieve config & status
    await client.login()  # invokes await client.installation()
    _global_oauth_tokens = extract_oauth_tokens(client)

    #
    # STEP 2: GET & PUT /{_type}/{_id}/schedule
    if dhw := client._get_single_heating_system().hotwater:
        schedule = await dhw.get_schedule()
        assert SCH_SCHEDULE_PUT(schedule)
        await dhw.set_schedule(schedule)

    if zone := client._get_single_heating_system()._zones[0]:
        schedule = await zone.get_schedule()
        assert SCH_SCHEDULE_PUT(schedule)
        await zone.set_schedule(schedule)

    pass


async def _test_vendor_api_status(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
):
    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    #
    # STEP 0: Instantiation...
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    #
    # STEP 1: Initial authentication, retrieve config & status
    await client.login()  # invokes await client.installation()
    _global_oauth_tokens = extract_oauth_tokens(client)

    #
    # STEP 2: GET /{_type}/{_id}/status
    if dhw := client._get_single_heating_system().hotwater:
        dhw_status = await dhw._refresh_status()
        assert SCH_DHW_STATUS(dhw_status)

    if zone := client._get_single_heating_system()._zones[0]:
        zone_status = await zone._refresh_status()
        assert SCH_ZONE_STATUS(zone_status)

    pass


async def _test_vendor_api_system(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession | mock.ClientSession = None,
):
    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    #
    # STEP 0: Instantiation...
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    #
    # STEP 1: Initial authentication, retrieve config & status
    await client.login()  # invokes await client.installation()
    _global_oauth_tokens = extract_oauth_tokens(client)

    #
    # STEP 2: GET /{_type}/{_id}/status
    try:
        tcs = client._get_single_heating_system()
    except evo.SingleTcsError:
        tcs = client.locations[0].gateways[0].control_systems[0]

    mode = tcs.systemModeStatus[SZ_MODE]
    assert mode in SYSTEM_MODES

    await tcs.set_mode(SystemMode.AWAY)
    await client._installation(refresh_status=True)

    await tcs.set_mode(mode)

    pass


@pytest.mark.asyncio
async def test_vendor_api_basics(
    credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
):
    username, password = credentials

    await _test_vendor_api_basics(username, password, session=session)


@pytest.mark.asyncio
async def test_vendor_api_sched_(
    credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
):
    username, password = credentials

    await _test_vendor_api_sched_(username, password, session=session)


@pytest.mark.asyncio
async def test_vendor_api_status(
    credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
):
    username, password = credentials

    await _test_vendor_api_status(username, password, session=session)


@pytest.mark.asyncio
async def test_vendor_api_system(
    credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
):
    username, password = credentials

    await _test_vendor_api_system(username, password, session=session)
