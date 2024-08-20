#!/usr/bin/env python3
"""evohome-async - validate the evohome-async APIs (methods)."""

from __future__ import annotations

from datetime import datetime as dt

import pytest

import evohomeasync2 as evo2
from evohomeasync2.schema import (
    SCH_DHW_STATUS,
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_ZONE_STATUS,
    SYSTEM_MODES,
    SystemMode,
)
from evohomeasync2.schema.const import SZ_MODE
from evohomeasync2.schema.schedule import SCH_PUT_SCHEDULE_DHW, SCH_PUT_SCHEDULE_ZONE
from evohomeasync2.zone import Zone

from . import _DEBUG_USE_REAL_AIOHTTP, mocked_server as mock
from .helpers import aiohttp, instantiate_client_v2

#######################################################################################


async def _test_basics_apis(evo: evo2.EvohomeClient) -> None:
    """Test authentication, `user_account()` and `installation()`."""

    #
    # STEP 1: Authentication (isolated from evo.login()), POST /Auth/OAuth/Token
    assert isinstance(evo.token_manager.access_token, str)
    assert isinstance(evo.token_manager.access_token_expires, dt)
    assert isinstance(evo.token_manager.refresh_token, str)

    if not _DEBUG_USE_REAL_AIOHTTP:
        assert evo.token_manager.access_token == "ncWMqPh2yGgAqc..."
        assert evo.token_manager.refresh_token == "Ryx9fL34Z5GcNV..."

    access_token = evo.token_manager.access_token
    refresh_token = evo.token_manager.refresh_token

    await evo.broker._headers()

    # The above should not cause a re-authentication, so...
    assert evo.token_manager.access_token == access_token
    assert evo.token_manager.refresh_token == refresh_token

    #
    # STEP 1A: Re-Authentication: more likely to cause 429: Too Many Requests
    if isinstance(evo.broker._session, aiohttp.ClientSession):
        access_token = evo.token_manager.access_token
        refresh_token = evo.token_manager.refresh_token

    #     await evo._basic_login()  # re-authenticate using refresh_token

    #     assert True or evo.token_manager.access_token != access_token  # TODO: mocked_server wont do this
    #     assert True or evo.token_manager.refresh_token != refresh_token  # TODO: mocked_server wont do this

    #
    # STEP 2: User account,  GET /userAccount...
    assert evo.account_info is None

    await evo.user_account(force_update=False)  # will update as no access_token

    assert SCH_USER_ACCOUNT(evo._user_account)
    assert evo.account_info == evo._user_account

    await evo.user_account()  # wont update as access_token is valid
    # await evo.user_account(force_update=True)  # will update as forced

    #
    # STEP 3: Installation, GET /location/installationInfo?userId={userId}
    assert evo.locations == []
    assert evo.installation_info is None

    await evo._installation(refresh_status=False)  # not evo.installation()

    assert SCH_FULL_CONFIG(evo._full_config)  # an array of locations
    assert evo.installation_info == evo._full_config

    # assert isinstance(evo.system_id, str)  # only if one TCS
    assert evo.locations

    await evo.installation()  # not evo._installation()
    # await evo.installation(force_update=True)  # will update as forced

    #
    # STEP 4: Status, GET /location/{locationId}/status
    for loc in evo.locations:
        loc_status = await loc.refresh_status()
        assert SCH_LOCN_STATUS(loc_status)

    pass


async def _test_sched__apis(evo: evo2.EvohomeClient) -> None:
    """Test `get_schedule()` and `get_schedule()`."""

    #
    # STEP 1: retrieve base data
    await evo.user_account()
    await evo.installation()

    #
    # STEP 2: GET & PUT /{_type}/{_id}/schedule
    if dhw := evo._get_single_tcs().hotwater:
        schedule = await dhw.get_schedule()
        assert SCH_PUT_SCHEDULE_DHW(schedule)
        await dhw.set_schedule(schedule)

    zone: Zone | None

    if (zone := evo._get_single_tcs()._zones[0]) and zone._id != mock.GHOST_ZONE_ID:
        schedule = await zone.get_schedule()
        assert SCH_PUT_SCHEDULE_ZONE(schedule)
        await zone.set_schedule(schedule)

    if zone := evo._get_single_tcs().zones_by_id.get(mock.GHOST_ZONE_ID):
        try:
            schedule = await zone.get_schedule()
        except evo2.InvalidSchedule:
            pass
        else:
            assert False


async def _test_status_apis(evo: evo2.EvohomeClient) -> None:
    """Test `_refresh_status()` for DHW/zone."""

    #
    # STEP 1: retrieve base data
    await evo.user_account()
    await evo.installation()

    #
    # STEP 2: GET /{_type}/{_id}/status
    if dhw := evo._get_single_tcs().hotwater:
        dhw_status = await dhw._refresh_status()
        assert SCH_DHW_STATUS(dhw_status)

    if zone := evo._get_single_tcs()._zones[0]:
        zone_status = await zone._refresh_status()
        assert SCH_ZONE_STATUS(zone_status)

    pass


async def _test_system_apis(evo: evo2.EvohomeClient) -> None:
    """Test `set_mode()` for TCS."""

    #
    # STEP 1: retrieve base data
    await evo.user_account()
    await evo.installation()

    #
    # STEP 2: GET /{_type}/{_id}/status
    try:
        tcs = evo._get_single_tcs()
    except evo2.NoSingleTcsError:
        tcs = evo.locations[0].gateways[0].control_systems[0]

    mode = tcs.systemModeStatus[SZ_MODE]
    assert mode in SYSTEM_MODES

    await tcs.set_mode(SystemMode.AWAY)
    await evo._installation(refresh_status=True)

    await tcs.set_mode(mode)

    pass


#######################################################################################


async def test_basics(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
) -> None:
    """Test authentication, `user_account()` and `installation()`."""

    try:
        await _test_basics_apis(
            await instantiate_client_v2(user_credentials, session, dont_login=True)
        )

    except evo2.AuthenticationFailed:
        if not _DEBUG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


async def test_sched_(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
) -> None:
    """Test `get_schedule()` and `get_schedule()`."""

    try:
        await _test_sched__apis(await instantiate_client_v2(user_credentials, session))

    except evo2.AuthenticationFailed:
        if not _DEBUG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


async def test_status(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
) -> None:
    """Test `_refresh_status()` for DHW/zone."""

    try:
        await _test_status_apis(await instantiate_client_v2(user_credentials, session))

    except evo2.AuthenticationFailed:
        if not _DEBUG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


async def test_system(
    user_credentials: tuple[str, str],
    session: aiohttp.ClientSession | mock.ClientSession,
) -> None:
    """Test `set_mode()` for TCS"""

    try:
        await _test_system_apis(await instantiate_client_v2(user_credentials, session))

    except evo2.AuthenticationFailed:
        if not _DEBUG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")

    except NotImplementedError:  # TODO: implement
        if _DEBUG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")
