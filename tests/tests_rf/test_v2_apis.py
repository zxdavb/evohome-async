"""Validate the evohome-async v2 APIs (methods).

Invokes every vendor API (URL) that the client uses, via the client's methods:

  Method    Endpoint                                                    Client method
  --------  ----------------------------------------------------------  ---------------------------
  GET       /userAccount                                                evo.update()
  GET       /location/installationInfo?userId={usr_id}&include...=True  evo.update()
  GET       /location/{loc_id}/status?includeTemperatureControlSystems  loc.update()
  PUT       /temperatureControlSystem/{tcs_id}/mode                     tcs.set_mode()
  PUT       /temperatureZone/{zon_id}/heatSetpoint                      zon.set_temperature(), reset()
  GET, PUT  /temperatureZone/{zon_id}/schedule                          zon.get/set_schedule()
  PUT       /domesticHotWater/{dhw_id}/state                            dhw.set_off(), reset()
  GET, PUT  /domesticHotWater/{dhw_id}/schedule                         dhw.get/set_schedule()

The client has methods for some other APIs, but does not use them (e.g. the status of a
zone is included in that of its location). They are invoked only if _DBG_TEST_UNUSED_APIS:

  GET       /location/{loc_id}/installationInfo                         loc.update(_update_time_zone_info=True)
  GET       /temperatureZone/{zon_id}/status                            zon._get_status()
  GET       /domesticHotWater/{dhw_id}/status                           dhw._get_status()

Only if _DBG_WAIT_FOR_COMM_TASKS, every PUT waits for its comm task to succeed.

For every vendor API, including those with no client method, see test_v2_urls.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohomeasync2.const import SystemMode
from evohomeasync2.hotwater import HotWater
from evohomeasync2.schemas.const import S2_MODE
from evohomeasync2.zone import Zone
from tests.common import get_dhw, get_loc, get_tcs, get_zon
from tests.const import _DBG_TEST_UNUSED_APIS, _DBG_USE_REAL_AIOHTTP

from . import faked_server as faked
from .common import skipif_auth_failed, wait_for_comm_task_obj

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient as EvohomeClientV2


#######################################################################################


async def _test_usr_apis(evo: EvohomeClientV2) -> None:
    """Test User and Location methods.

    Includes: evo.user_account(), evo.installation() and loc.update() methods.
    """

    # STEP 1: retrieve config only: evo.user_account(), evo.installation()
    await evo.update(dont_update_status=True)

    assert evo2.main.SCH_USR_ACCOUNT(evo.user_account)
    assert evo2.main.SCH_USR_LOCATIONS(evo._user_locs)

    # STEP 2: GET /location/{loc.id}/status
    loc = get_loc(evo)

    loc_status = await loc.update()
    assert evo2.Location.SCH_STATUS(loc_status)

    # STEP 3: GET /location/{loc.id}/installationInfo (not used by the client)
    if _DBG_TEST_UNUSED_APIS:
        loc_status = await loc.update(_update_time_zone_info=True)
        assert evo2.Location.SCH_STATUS(loc_status)


async def _test_tcs_apis(evo: EvohomeClientV2) -> None:
    """Test ControlSystem methods.

    Includes tcs.update() and tcs.set_mode().
    Does not include tcs.get_schedules(), tcs.set_schedules().
    """

    # STEP 1: retrieve config only
    await evo.update(dont_update_status=False)

    # STEP 2: GET /temperatureControlSystem/{tcs.id}/status
    tcs = get_tcs(evo)

    # tcs_status = await tcs._update()
    # assert evo2.ControlSystem.SCH_STATUS(tcs_status)

    assert tcs.system_mode_status is not None
    mode = tcs.system_mode_status[S2_MODE]

    assert mode in SystemMode

    # STEP 3: PUT /temperatureControlSystem/{tcs.id}/mode
    await wait_for_comm_task_obj(await tcs.set_mode(SystemMode.AWAY))
    await evo.update()

    await wait_for_comm_task_obj(await tcs.set_mode(mode))


async def _test_dhw_apis(evo: EvohomeClientV2) -> None:
    """Test Hotwater methods.

    Includes dhw.get_schedule() and dhw.set_schedule(), and dhw._get_status() (only if
    _DBG_TEST_UNUSED_APIS).
    """

    # STEP 1: retrieve config only
    await evo.update(dont_update_status=True)

    if not (dhw := get_dhw(evo)):
        pytest.skip("No DHW found in TCS")

    # STEP 2: GET /domesticHotWater/{dhw.id}/status (not used by the client)
    if _DBG_TEST_UNUSED_APIS:
        dhw_status = await dhw._get_status()
        assert evo2.HotWater.SCH_STATUS(dhw_status)

    # STEP 3: GET, PUT /domesticHotWater/{dhw.id}/schedule
    schedule = await dhw.get_schedule()
    assert HotWater.SCH_SCHEDULE({"daily_schedules": schedule})

    await wait_for_comm_task_obj(await dhw.set_schedule(schedule))


async def _test_dhw_mode(evo: EvohomeClientV2) -> None:
    """Test Hotwater mode methods.

    Includes dhw.set_off() and dhw.reset().
    """

    # STEP 1: retrieve config only
    await evo.update(dont_update_status=True)

    if not (dhw := get_dhw(evo)):
        pytest.skip("No DHW found in TCS")

    # STEP 2: PUT /domesticHotWater/{dhw.id}/state
    await wait_for_comm_task_obj(await dhw.set_off())  # PermanentOverride
    await wait_for_comm_task_obj(await dhw.reset())  # FollowSchedule


async def _test_zon_apis(evo: EvohomeClientV2) -> None:
    """Test Zone methods.

    Includes zon.get_schedule() and zon.set_schedule(), and zon._get_status() (only if
    _DBG_TEST_UNUSED_APIS).
    """

    # STEP 1: retrieve config only
    await evo.update(dont_update_status=True)

    if not (zone := get_zon(evo)):
        pytest.skip("No zones found in TCS")

    # STEP 2: GET /temperatureZone/{zon.id}/status (not used by the client)
    if _DBG_TEST_UNUSED_APIS:
        zon_status = await zone._get_status()
        assert evo2.Zone.SCH_STATUS(zon_status)

    # STEP 3: GET, PUT /temperatureZone/{zon.id}/schedule
    if zone.id != faked.GHOST_ZONE_ID:
        schedule = await zone.get_schedule()
        assert Zone.SCH_SCHEDULE({"daily_schedules": schedule})

        await wait_for_comm_task_obj(await zone.set_schedule(schedule))

    if zone := zone.tcs.zone_by_id.get(faked.GHOST_ZONE_ID):
        try:
            schedule = await zone.get_schedule()
        except evo2.InvalidScheduleError:
            pass
        else:
            pytest.fail("Did not raise expected exception")


async def _test_zon_mode(evo: EvohomeClientV2) -> None:
    """Test Zone mode methods.

    Includes zon.set_temperature() and zon.reset().
    """

    # STEP 1: retrieve config only
    await evo.update(dont_update_status=True)

    if not (zone := get_zon(evo)):
        pytest.skip("No zones found in TCS")

    # STEP 2: PUT /temperatureZone/{zon.id}/heatSetpoint
    task = await zone.set_temperature(zone.min_heat_setpoint)  # PermanentOverride
    await wait_for_comm_task_obj(task)
    await wait_for_comm_task_obj(await zone.reset())  # FollowSchedule


#######################################################################################


@skipif_auth_failed
async def test_usr_apis(evohome_v2: EvohomeClientV2) -> None:
    """Test user_account() and installation()."""

    try:
        await _test_usr_apis(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_tcs(evohome_v2: EvohomeClientV2) -> None:
    """Test set_mode() for TCS"""

    try:
        await _test_tcs_apis(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_dhw_apis(evohome_v2: EvohomeClientV2) -> None:
    """Test get_schedule() and get_schedule()."""
    await _test_dhw_apis(evohome_v2)


@skipif_auth_failed
async def test_dhw_mode(evohome_v2: EvohomeClientV2) -> None:
    """Test set_off() and reset() for DHW."""

    try:
        await _test_dhw_mode(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_zon_apis(evohome_v2: EvohomeClientV2) -> None:
    """Test _update() for DHW/zone."""
    await _test_zon_apis(evohome_v2)


@skipif_auth_failed
async def test_zon_mode(evohome_v2: EvohomeClientV2) -> None:
    """Test set_temperature() and reset() for zone."""

    try:
        await _test_zon_mode(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")
