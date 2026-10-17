"""Test the v1 client's methods.

Every method that changes state is used so that it is a no-op on a real system: it
reasserts the current setpoint/state of an entity that is already following its
schedule, and then reverts it to its schedule. Entities that are not alive, or not
following their schedule, are skipped. Nothing else is done to restore an entity's
state: that is left to the end of the test run (see reset_systems() in conftest.py).

Unlike the URL tests, the library does not wait for the vendor's comm tasks, so these
tests confirm that each request is accepted, not that it has taken effect.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

import evohomeasync as evo1
from tests.common import get_tcs
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient as EvohomeClientV1
    from evohomeasync.entities import ControlSystem, HotWater, Zone


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


def _is_evohome(tcs: ControlSystem) -> bool:
    """Return True if the TCS is an evohome system (not, say, a Round)."""
    return any(
        isinstance(t := z.config["thermostat_model_type"], str)
        and t.startswith("EMEA_")
        for z in tcs.zones
    )


async def _test_usr_apis(ec1: EvohomeClientV1) -> None:
    """Test User and Location methods.

    Includes: ec1.update(), ec1.user_account, ec1.locations, and zone/DHW temperatures.
    """

    # STEP 1: GET /accountInfo, GET /locations?userId={usr_id}&allData=True
    await ec1.get_status()

    assert evo1.main.SCH_GET_ACCOUNT_INFO(ec1.user_account)
    assert evo1.main.SCH_GET_ACCOUNT_LOCS(ec1._user_locs)

    # STEP 2: the high-precision temperatures (from the latest update)
    for tcs in (loc.tcs for loc in ec1.locations if loc.tcs):
        temps = await tcs.get_temperatures(dont_update_status=True)
        assert set(temps) == {z.id for z in tcs.zones}

        if tcs.hotwater:
            assert tcs.hotwater.temperature is None or isinstance(
                tcs.hotwater.temperature, float
            )


async def _test_tcs_apis(ec1: EvohomeClientV1) -> None:
    """Test ControlSystem methods.

    Includes tcs.set_auto() (which would leave the TCS in Auto mode).
    """

    await ec1.get_status()

    if not _is_evohome(tcs := get_tcs(ec1)):
        pytest.skip("The location under test is not an evohome system")

    # PUT /evoTouchSystems?locationId={loc_id}
    # NOTE: the vendor has removed this URL, so all the TCS set_*() methods now fail
    with pytest.raises(evo1.ApiCallFailedError) as err:
        await tcs.set_auto()
    assert err.value.status == HTTPStatus.NOT_FOUND


async def _test_dhw_apis(ec1: EvohomeClientV1) -> None:
    """Test HotWater methods.

    Includes dhw.set_dhw_on() or dhw.set_dhw_off() (whichever is its current state),
    and dhw.set_dhw_auto().

    NOTE: on some installations (e.g. the test installation), the vendor forbids a DHW's
    Status and NextTime, which these methods send, so they fail with a 400: then this
    test is an xfail (see test_v1_urls_auth.py for that contract).
    """

    await ec1.get_status()

    dhw = get_tcs(ec1).hotwater
    if dhw is None or not _is_live(dhw):
        pytest.skip("No live DHW found")

    until = dt.now(tz=UTC) + td(hours=1)

    # PUT /devices/{dhw_id}/thermostat/changeableValues
    if _changeable_values(dhw)["mode"] == "DHWOn":
        coro = dhw.set_dhw_on(until=until)  # would be a no-op
    else:
        coro = dhw.set_dhw_off(until=until)  # would be a no-op

    try:
        await coro
    except evo1.ApiCallFailedError as err:
        if err.status == HTTPStatus.BAD_REQUEST and "ForbiddenParameter" in str(err):
            pytest.xfail("This DHW forbids Status/NextTime (see test_v1_urls_auth.py)")
        raise

    await dhw.set_dhw_auto()


async def _test_zon_apis(ec1: EvohomeClientV1) -> None:
    """Test Zone methods.

    Includes zone.set_temperature() (temporary & permanent) and zone.set_zone_auto().
    """

    await ec1.get_status()

    zone = next((z for z in get_tcs(ec1).zones if _is_live_and_scheduled(z)), None)
    if zone is None:
        pytest.skip("No live zone found that is following its schedule")

    setpoint: float = _changeable_values(zone)["heat_setpoint"]["value"]

    # PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint
    await zone.set_temperature(setpoint, until=dt.now(tz=UTC) + td(hours=1))
    await zone.set_temperature(setpoint)

    # NOTE: sends no "Value" key, whereas the older client sent "Value": None
    await zone.set_zone_auto()


#######################################################################################


@skipif_auth_failed
async def test_usr_apis(
    ec1: EvohomeClientV1,
) -> None:
    """Test update(), user_account and locations."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_usr_apis(ec1)


@skipif_auth_failed
async def test_tcs_apis(
    ec1: EvohomeClientV1,
) -> None:
    """Test set_auto() for a TCS."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_tcs_apis(ec1)


@skipif_auth_failed
async def test_dhw_apis(
    ec1: EvohomeClientV1,
) -> None:
    """Test set_dhw_on()/set_dhw_off() and set_dhw_auto() for a DHW."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_dhw_apis(ec1)


@skipif_auth_failed
async def test_zon_apis(
    ec1: EvohomeClientV1,
) -> None:
    """Test set_temperature() and set_zone_auto() for a zone."""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await _test_zon_apis(ec1)
