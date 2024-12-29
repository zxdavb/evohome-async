"""Validate the evohome-async v2 APIs (methods)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohome.helpers import camel_to_snake
from evohomeasync2.schemas import SystemMode, factory_dhw_schedule, factory_zon_schedule
from evohomeasync2.schemas.const import S2_MODE
from tests.const import _DBG_USE_REAL_AIOHTTP

from . import faked_server as faked
from .common import skipif_auth_failed

if TYPE_CHECKING:
    from tests.conftest import EvohomeClientv2


def _get_dhw(evo: EvohomeClientv2) -> evo2.HotWater | None:
    """Return the DHW object of a TCS."""
    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.systems:
                if tcs.hotwater:
                    return tcs.hotwater
    return None


def _get_zon(evo: EvohomeClientv2) -> evo2.Zone | None:
    """Return the Zone object of a TCS."""
    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.systems:
                if tcs.zones:
                    return tcs.zones[0]
    return None


#######################################################################################


async def _test_usr_apis(evo: EvohomeClientv2) -> None:
    """Test User and Location methods.

    Includes: evo.user_account(), evo.installation() and loc.update() methods.
    """

    # STEP 1: retrieve config only: evo.user_account(), evo.installation()
    await evo.update(_dont_update_status=True)

    assert evo2.main.SCH_USER_ACCOUNT(evo.user_account)
    assert evo2.main.SCH_USER_LOCATIONS(evo._user_locs)

    # STEP 2: GET /location/{loc.id}/status
    for loc in evo.locations:
        loc_status = await loc.update()
        assert evo2.Location.SCH_STATUS(loc_status)


async def _test_tcs_apis(evo: EvohomeClientv2) -> None:
    """Test ControlSystem methods.

    Includes tcs.update() and tcs.set_mode().
    Does not include tcs.get_schedules(), tcs.set_schedules().
    """

    # STEP 1: retrieve config only
    await evo.update(_dont_update_status=False)

    # STEP 2: GET /temperatureControlSystem/{tcs.id}/status
    tcs = evo.locations[0].gateways[0].systems[0]

    # tcs_status = await tcs._update()
    # assert evo2.ControlSystem.SCH_STATUS(tcs_status)

    assert tcs.system_mode_status is not None
    mode = tcs.system_mode_status[S2_MODE]

    assert mode in SystemMode

    # STEP 3: PUT /temperatureControlSystem/{tcs.id}/mode
    await tcs.set_mode(SystemMode.AWAY)
    await evo.update()

    await tcs.set_mode(mode)


async def _test_dhw_apis(evo: EvohomeClientv2) -> None:
    """Test Hotwater methods.

    Includes dhw._update() and dhw.get_schedule().
    """

    # STEP 1: retrieve config only
    await evo.update(_dont_update_status=True)

    if not (dhw := _get_dhw(evo)):
        pytest.skip("No DHW found in TCS")

    # STEP 2: GET /domesticHotWater/{dhw.id}/???
    dhw_status = await dhw._get_status()
    assert evo2.HotWater.SCH_STATUS(dhw_status)

    # STEP 2: GET /domesticHotWater/{dhw.id}/get_schedule
    schedule = await dhw.get_schedule()
    assert factory_dhw_schedule(camel_to_snake)({"daily_schedules": schedule})

    await dhw.set_schedule(schedule)


async def _test_zon_apis(evo: EvohomeClientv2) -> None:
    """Test Zone methods.

    Includes zon._update() and zon.get_schedule().
    """

    # STEP 1: retrieve config only
    await evo.update(_dont_update_status=True)

    if not (zone := _get_zon(evo)):
        pytest.skip("No zones found in TCS")

    # STEP 2: GET /temperatureZone/{zon.id}/status
    zon_status = await zone._get_status()
    assert evo2.Zone.SCH_STATUS(zon_status)

    # STEP 2: GET /temperatureZone/{zon.id}/get_schedule
    if zone.id != faked.GHOST_ZONE_ID:
        schedule = await zone.get_schedule()
        assert factory_zon_schedule(camel_to_snake)({"daily_schedules": schedule})

        await zone.set_schedule(schedule)

    if zone := zone.tcs.zone_by_id.get(faked.GHOST_ZONE_ID):
        try:
            schedule = await zone.get_schedule()
        except evo2.InvalidScheduleError:
            pass
        else:
            pytest.fail("Did not raise expected exception")


#######################################################################################


@skipif_auth_failed
async def test_usr_apis(evohome_v2: EvohomeClientv2) -> None:
    """Test user_account() and installation()."""
    await _test_usr_apis(evohome_v2)


@skipif_auth_failed
async def test_tcs(evohome_v2: EvohomeClientv2) -> None:
    """Test set_mode() for TCS"""

    try:
        await _test_tcs_apis(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_dhw_apis(evohome_v2: EvohomeClientv2) -> None:
    """Test get_schedule() and get_schedule()."""
    await _test_dhw_apis(evohome_v2)


@skipif_auth_failed
async def test_zon_apis(evohome_v2: EvohomeClientv2) -> None:
    """Test _update() for DHW/zone."""
    await _test_zon_apis(evohome_v2)
