"""evohome-async - validate the evohome-async APIs (methods)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohomeasync2.schemas import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE, SystemMode
from evohomeasync2.schemas.const import S2_MODE
from tests.const import _DBG_USE_REAL_AIOHTTP

from . import faked_server as faked
from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync2.zone import Zone
    from tests.conftest import EvohomeClientv2


#######################################################################################


async def _test_basics_apis(evo: EvohomeClientv2) -> None:
    """Test authentication, `user_account()` and `installation()`."""

    # STEP 1: retrieve base data
    await evo.update(_dont_update_status=False)

    assert evo2.main.SCH_USER_ACCOUNT(evo.user_account)
    assert evo2.main.SCH_USER_LOCATIONS(evo.user_installation)

    # STEP 4: Status, GET /location/{loc.id}/status
    for loc in evo.locations:
        loc_status = await loc.update()
        assert evo2.Location.SCH_STATUS(loc_status)


async def _test_sched__apis(evo: EvohomeClientv2) -> None:
    """Test `get_schedule()` and `get_schedule()`."""

    # STEP 1: retrieve base data
    await evo.update()

    # STEP 2: GET & PUT /{x._TYPE}/{x.id}/schedule
    if dhw := evo._get_single_tcs().hotwater:
        sched_hw = await dhw.get_schedule()
        assert TCC_GET_DHW_SCHEDULE(sched_hw)
        await dhw.set_schedule(sched_hw)

    zone: Zone | None

    if (zone := evo._get_single_tcs().zones[0]) and zone.id != faked.GHOST_ZONE_ID:
        schedule = await zone.get_schedule()
        assert TCC_GET_ZON_SCHEDULE(schedule)
        await zone.set_schedule(schedule)

    if zone := evo._get_single_tcs().zones_by_id.get(faked.GHOST_ZONE_ID):
        try:
            schedule = await zone.get_schedule()
        except evo2.InvalidScheduleError:
            pass
        else:
            pytest.fail("Did not raise expected exception")


async def _test_update_apis(evo: EvohomeClientv2) -> None:
    """Test `_update()` for DHW/zone."""

    # STEP 1: retrieve config
    await evo.update(_dont_update_status=True)

    # STEP 2: GET /{x._TYPE}/{x.id}/status
    if dhw := evo._get_single_tcs().hotwater:
        dhw_status = await dhw._update()
        assert evo2.HotWater.SCH_STATUS(dhw_status)

    if zone := evo._get_single_tcs().zones[0]:
        zone_status = await zone._update()
        assert evo2.Zone.SCH_STATUS(zone_status)


async def _test_system_apis(evo: EvohomeClientv2) -> None:
    """Test `set_mode()` for TCS."""

    # STEP 1: retrieve base data
    await evo.update()

    # STEP 2: GET /{x._TYPE}/{x.id}/status
    try:
        tcs = evo._get_single_tcs()
    except evo2.NoSingleTcsError:
        tcs = evo.locations[0].gateways[0].control_systems[0]

    assert tcs.system_mode_status is not None
    mode = tcs.system_mode_status[S2_MODE]

    assert mode in SystemMode

    await tcs.set_mode(SystemMode.AWAY)
    await evo.update()

    await tcs.set_mode(mode)


#######################################################################################


@skipif_auth_failed
async def test_basics(evohome_v2: EvohomeClientv2) -> None:
    """Test authentication, `user_account()` and `installation()`."""
    await _test_basics_apis(evohome_v2)


@skipif_auth_failed
async def _test_sched_(evohome_v2: EvohomeClientv2) -> None:
    """Test `get_schedule()` and `get_schedule()`."""
    await _test_sched__apis(evohome_v2)


@skipif_auth_failed
async def test_status(evohome_v2: EvohomeClientv2) -> None:
    """Test `_update()` for DHW/zone."""
    await _test_update_apis(evohome_v2)


@skipif_auth_failed
async def test_system(evohome_v2: EvohomeClientv2) -> None:
    """Test `set_mode()` for TCS"""

    try:
        await _test_system_apis(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")
