"""Validate the evohome-async v0 APIs (methods).

Every method that changes state is used so that it is a no-op on a real system: it
reasserts the current setpoint/state/mode of an entity that is already following its
schedule (or is already in permanent Auto mode), and then reverts it to its schedule.
Entities that are not alive, or not following their schedule, are skipped.

Unlike the URL tests, the library does not wait for the vendor's comm tasks, so these
tests confirm that each request is accepted, not that it has taken effect. Note that the
vendor sometimes does not apply a v0 PUT that is equivalent to an earlier one (e.g. a
revert to schedule, see is_stale_task_v0() in common.py), so a zone is then checked (and
reverted again, if need be) via the v2 API.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

import evohomeasync as evo0
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import (
    ensure_zone_follows_schedule_v2,
    is_permanent_auto_v2,
    skipif_auth_failed,
)

if TYPE_CHECKING:
    from evohomeasync.entities import HotWater, Location, Zone
    from tests.conftest import EvohomeClientV0, EvohomeClientV2


#######################################################################################


def _changeable_values(dev: HotWater | Zone) -> dict[str, Any]:
    """Return a zone/DHW's changeable_values (snake_case), e.g. its schedule status."""
    return dict(dev._status["thermostat"].get("changeable_values") or {})


def _is_live(dev: HotWater | Zone) -> bool:
    """Return True if the zone/DHW is alive.

    The vendor rejects any change to a device that is not alive (400, DeviceIsLost).
    """
    return dev._status.get("is_alive") is True


def _is_live_and_scheduled(dev: HotWater | Zone) -> bool:
    """Return True if the zone/DHW is alive, and is following its schedule."""

    if not _is_live(dev):
        return False

    values = _changeable_values(dev)
    if (setpoint := values.get("heat_setpoint")) is not None:  # a zone
        return bool(setpoint.get("status") == "Scheduled")
    return bool(values.get("status") == "Scheduled")  # a DHW


def _is_evohome(loc: Location) -> bool:
    """Return True if the location is an evohome system (not, say, a Round)."""
    return any(
        isinstance(t := z.config["thermostat_model_type"], str)
        and t.startswith("EMEA_")
        for z in loc.zones
    )


async def _test_usr_apis(evo: EvohomeClientV0) -> None:
    """Test User and Location methods.

    Includes: evo.update(), evo.user_account, evo.locations, and zone/DHW temperatures.
    """

    # STEP 1: GET /accountInfo, GET /locations?userId={usr_id}&allData=True
    await evo.update()

    assert evo0.main.SCH_GET_ACCOUNT_INFO(evo.user_account)
    assert evo0.main.SCH_GET_ACCOUNT_LOCS(evo._user_locs)

    # STEP 2: the high-precision temperatures (from the latest update)
    for loc in evo.locations:
        temps = await loc.get_temperatures(dont_update_status=True)
        assert set(temps) == {z.id for z in loc.zones}

        if loc.hotwater:
            assert loc.hotwater.temperature is None or isinstance(
                loc.hotwater.temperature, float
            )


async def _test_tcs_apis(evo: EvohomeClientV0, evo_v2: EvohomeClientV2) -> None:
    """Test ControlSystem methods.

    Includes loc.set_auto(), but only for a location already in permanent Auto mode.
    """

    await evo.update()

    if not (loc := next((x for x in evo.locations if _is_evohome(x)), None)):
        pytest.skip("No evohome location found")

    if not await is_permanent_auto_v2(evo_v2, loc.id):
        pytest.skip("Location is not in permanent Auto mode (won't change it)")

    # PUT /evoTouchSystems?locationId={loc_id}
    # NOTE: the vendor has removed this URL, so all the TCS set_*() methods now fail
    with pytest.raises(evo0.ApiCallFailedError) as err:
        await loc.set_auto()  # would be a no-op
    assert err.value.status == HTTPStatus.NOT_FOUND


async def _test_dhw_apis(evo: EvohomeClientV0) -> None:
    """Test HotWater methods.

    Includes dhw.set_dhw_on() or dhw.set_dhw_off() (whichever is its current state),
    and dhw.set_dhw_auto().

    NOTE: the vendor now requires Mode and forbids every other key of a DHW's
    changeableValues, so all three of these methods currently fail: they send Status
    (and set_dhw_on/off() also send NextTime). See test_v0_urls_auth.py for the vendor's
    current contract. There is no longer any equivalent of set_dhw_auto().
    """

    await evo.update()

    dhw = next(
        (
            loc.hotwater
            for loc in evo.locations
            if loc.hotwater and _is_live(loc.hotwater)
        ),
        None,
    )
    if dhw is None:
        pytest.skip("No live DHW found")

    until = dt.now(tz=UTC) + td(hours=1)

    # PUT /devices/{dhw_id}/thermostat/changeableValues
    if _changeable_values(dhw)["mode"] == "DHWOn":
        coro = dhw.set_dhw_on(until=until)  # would be a no-op
    else:
        coro = dhw.set_dhw_off(until=until)  # would be a no-op

    with pytest.raises(evo0.ApiCallFailedError) as err:
        await coro
    assert err.value.status == HTTPStatus.BAD_REQUEST

    with pytest.raises(evo0.ApiCallFailedError) as err:
        await dhw.set_dhw_auto()
    assert err.value.status == HTTPStatus.BAD_REQUEST


async def _test_zon_apis(evo: EvohomeClientV0, evo_v2: EvohomeClientV2) -> None:
    """Test Zone methods.

    Includes zone.set_temperature() (temporary & permanent) and zone.set_zone_auto().
    """

    await evo.update()

    zone = next(
        (z for loc in evo.locations for z in loc.zones if _is_live_and_scheduled(z)),
        None,
    )
    if zone is None:
        pytest.skip("No live zone found that is following its schedule")

    setpoint: float = _changeable_values(zone)["heat_setpoint"]["value"]

    # PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint
    try:
        await zone.set_temperature(setpoint, until=dt.now(tz=UTC) + td(hours=1))
        await zone.set_temperature(setpoint)

    finally:
        # NOTE: sends no "Value" key, whereas the older client sent "Value": None
        await zone.set_zone_auto()

        # the vendor may not apply the above, e.g. if another test has sent a revert
        # recently (see is_stale_task_v0), so make sure via the v2 API
        await ensure_zone_follows_schedule_v2(evo_v2.auth, zone.id)


#######################################################################################


@skipif_auth_failed
async def test_usr_apis(evohome_v0: EvohomeClientV0) -> None:
    """Test update(), user_account and locations."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_usr_apis(evohome_v0)


@skipif_auth_failed
async def test_tcs_apis(
    evohome_v0: EvohomeClientV0, evohome_v2: EvohomeClientV2
) -> None:
    """Test set_auto() for a TCS."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_tcs_apis(evohome_v0, evohome_v2)


@skipif_auth_failed
async def test_dhw_apis(evohome_v0: EvohomeClientV0) -> None:
    """Test set_dhw_on()/set_dhw_off() and set_dhw_auto() for a DHW."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_dhw_apis(evohome_v0)


@skipif_auth_failed
async def test_zon_apis(
    evohome_v0: EvohomeClientV0, evohome_v2: EvohomeClientV2
) -> None:
    """Test set_temperature() and set_zone_auto() for a zone."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_zon_apis(evohome_v0, evohome_v2)
