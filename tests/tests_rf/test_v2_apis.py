#!/usr/bin/env python3
"""evohome-async - validate the evohome-async APIs (methods)."""

from __future__ import annotations

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
from evohomeasync2.schema.const import S2_MODE
from evohomeasync2.schema.schedule import SCH_PUT_SCHEDULE_DHW, SCH_PUT_SCHEDULE_ZONE
from evohomeasync2.zone import Zone

from . import faked_server as faked
from .conftest import skipif_auth_failed
from .const import _DBG_USE_REAL_AIOHTTP

#######################################################################################


async def _test_basics_apis(evo: evo2.EvohomeClientNew) -> None:
    """Test authentication, `user_account()` and `installation()`."""

    # STEP 1: retrieve base data
    await evo.update(dont_update_status=False)

    assert SCH_USER_ACCOUNT(evo._user_info)
    assert SCH_FULL_CONFIG(evo._install_config)

    # STEP 4: Status, GET /location/{loc.id}/status
    for loc in evo.locations:
        loc_status = await loc.update()
        assert SCH_LOCN_STATUS(loc_status)

    pass


async def _test_sched__apis(evo: evo2.EvohomeClientNew) -> None:
    """Test `get_schedule()` and `get_schedule()`."""

    # STEP 1: retrieve base data
    await evo.update()

    # STEP 2: GET & PUT /{x.TYPE}/{x.id}/schedule
    if dhw := evo._get_single_tcs().hotwater:
        schedule = await dhw.get_schedule()
        assert SCH_PUT_SCHEDULE_DHW(schedule)
        await dhw.set_schedule(schedule)

    zone: Zone | None

    if (zone := evo._get_single_tcs().zones[0]) and zone.id != faked.GHOST_ZONE_ID:
        schedule = await zone.get_schedule()
        assert SCH_PUT_SCHEDULE_ZONE(schedule)
        await zone.set_schedule(schedule)

    if zone := evo._get_single_tcs().zones_by_id.get(faked.GHOST_ZONE_ID):
        try:
            schedule = await zone.get_schedule()
        except evo2.InvalidScheduleError:
            pass
        else:
            assert False


async def _test_update_apis(evo: evo2.EvohomeClientNew) -> None:
    """Test `_update()` for DHW/zone."""

    # STEP 1: retrieve config
    await evo.update(dont_update_status=True)

    # STEP 2: GET /{x.TYPE}/{x.id}/status
    if dhw := evo._get_single_tcs().hotwater:
        dhw_status = await dhw._update()
        assert SCH_DHW_STATUS(dhw_status)

    if zone := evo._get_single_tcs().zones[0]:
        zone_status = await zone._update()
        assert SCH_ZONE_STATUS(zone_status)

    pass


async def _test_system_apis(evo: evo2.EvohomeClientNew) -> None:
    """Test `set_mode()` for TCS."""

    # STEP 1: retrieve base data
    await evo.update()

    # STEP 2: GET /{x.TYPE}/{x.id}/status
    try:
        tcs = evo._get_single_tcs()
    except evo2.NoSingleTcsError:
        tcs = evo.locations[0].gateway_by_id[0].control_system_by_id[0]

    mode = tcs.system_mode_status[S2_MODE]
    assert mode in SYSTEM_MODES

    await tcs.set_mode(SystemMode.AWAY)
    await evo.update()

    await tcs.set_mode(mode)

    pass


#######################################################################################


@skipif_auth_failed
async def test_basics(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test authentication, `user_account()` and `installation()`."""
    await _test_basics_apis(evohome_v2)


@skipif_auth_failed
async def _test_sched_(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test `get_schedule()` and `get_schedule()`."""
    await _test_sched__apis(evohome_v2)


@skipif_auth_failed
async def test_status(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test `_update()` for DHW/zone."""
    await _test_update_apis(evohome_v2)


@skipif_auth_failed
async def test_system(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test `set_mode()` for TCS"""

    try:
        await _test_system_apis(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")
