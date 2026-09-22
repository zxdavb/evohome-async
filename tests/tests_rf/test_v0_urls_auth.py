"""Validate the handling of the vendor's v0 APIs (URLs) for Authorization.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server (if any) is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

import evohomeasync as evo0
from _evohome.helpers import TCC_DTM_STRFTIME
from evohomeasync.schemas import TCC_GET_USR_LOCS
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import (
    is_alive_v0,
    is_dhw_v0,
    is_zone_v0,
    should_fail_v0,
    should_work_v0,
    skipif_auth_failed,
    status_of_v0,
    task_id_v0,
    wait_for_comm_task_v0,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from evohomeasync.schemas import TccDeviceResponseT
    from tests.conftest import EvohomeClientV0


async def _test_usr_locations(evo: EvohomeClientV0) -> None:
    """Test /locations?userId={user_id}&allData=True"""

    usr_id: int = evo.user_account["user_id"]
    # loc_id: int = evo.location_id

    url = f"locations?userId={usr_id}&allData=True"
    _ = await should_work_v0(evo.auth, HTTPMethod.GET, url)  # FIXME: add schema

    # why isn't this one METHOD_NOT_ALLOWED?
    _ = await should_fail_v0(evo.auth, HTTPMethod.PUT, url, status=HTTPStatus.NOT_FOUND)

    url = f"locations?userId={usr_id}"
    _ = await should_work_v0(evo.auth, HTTPMethod.GET, url, schema=None)

    url = "locations?userId=123456"
    _ = await should_fail_v0(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED
    )

    url = "locations?userId='123456'"
    _ = await should_fail_v0(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST
    )

    url = "xxxxxxx"  # NOTE: a general test, not a test specific to the 'locations' URL
    _ = await should_fail_v0(
        evo.auth,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # not the usual content-type
    )


async def _test_evo_systems(evo: EvohomeClientV0) -> None:
    """Test /evoTouchSystems?locationId={loc_id}"""

    # usr_id: int = evo.user_account["user_id"]
    loc_id = evo.locations[0].id

    #
    # TEST 0: unsupported method?
    url = f"evoTouchSystems?locationId={loc_id}"
    _ = await should_fail_v0(
        evo.auth,
        HTTPMethod.GET,
        url,
        content_type="text/html",  # not the usual content-type
        status=HTTPStatus.NOT_FOUND,
    )
    # '<!DOCTYPE html PUBLIC ... not found ...'

    #
    # TEST 0: supported method?
    json = {
        "QuickAction": "Auto",
        "QuickActionNextTime": None,
    }

    #       evoTouchSystems?locationId=$locationId
    url = f"evoTouchSystems?locationId={loc_id}"
    _ = await should_fail_v0(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json=json,
        content_type="text/html",  # not the usual content-type
        status=HTTPStatus.NOT_FOUND,
    )
    # '<!DOCTYPE html PUBLIC ... not found ...'


# GET /accountInfo (is also in test_v0_urls_auth.py)
# @skipif_auth_failed
# async def test_usr_account(evohome_v0: EvohomeClientV0) -> None:
#     """Test /accountInfo"""


# GET /locations?userId={user_id}&allData=True
@skipif_auth_failed
async def test_usr_locations(evohome_v0: EvohomeClientV0) -> None:
    """Test /locations?userId={user_id}&allData=True"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    try:
        await evohome_v0.update()  # get user_id and location_id

        await _test_usr_locations(evohome_v0)

    except evo0.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate with real server")


# PUT /evoTouchSystems?locationId={loc_id}
@skipif_auth_failed
async def test_evo_systems(evohome_v0: EvohomeClientV0) -> None:
    """Test /evoTouchSystems?locationId={loc_id}"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    try:
        await evohome_v0.update()  # get user_id and location_id

        await _test_evo_systems(evohome_v0)

    except evo0.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate with real server")


_TASK_TIMEOUT = 30  # seconds, for a comm task to succeed

# the older (non-async) client's bodies for reverting an entity to its schedule
_ZON_REVERT = {"Value": None, "Status": "Scheduled", "NextTime": None}
_DHW_REVERT = {
    "Status": "Scheduled",
    "Mode": None,
    "NextTime": None,
    "SpecialModes": None,
    "HeatSetpoint": None,
    "CoolSetpoint": None,
}


async def _get_devices(evo: EvohomeClientV0) -> list[TccDeviceResponseT]:
    """Return all the (vendor-cased) devices of all the user's locations."""

    usr_id: int = evo.user_account["user_id"]

    url = f"locations?userId={usr_id}&allData=True"
    locs = await should_work_v0(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_LOCS)

    return [d for loc in locs for d in loc["devices"]]


async def _get_status(evo: EvohomeClientV0, dev_id: int) -> str | None:
    """Return the current status of a zone/DHW, e.g. "Scheduled"."""
    return status_of_v0(
        next(d for d in await _get_devices(evo) if d["deviceID"] == dev_id)
    )


async def _put_and_wait(
    evo: EvohomeClientV0, url: str, json: Mapping[str, object]
) -> None:
    """PUT a change, then wait for its comm task to succeed."""

    rsp = await should_work_v0(evo.auth, HTTPMethod.PUT, url, json=json)
    # {"id": "123"} or [{"id": "123"}]  (as per the older client's tests)

    async with asyncio.timeout(_TASK_TIMEOUT):
        _ = await wait_for_comm_task_v0(evo.auth, task_id_v0(rsp))
    # {"state": "Succeeded"}  (as per the older client's tests)


async def _test_override_then_revert(
    evo: EvohomeClientV0,
    dev_id: int,
    url: str,
    /,
    overrides: tuple[Mapping[str, object], ...],
    revert: Mapping[str, object],
    *,
    expected: str,
) -> None:
    """Apply each override in turn, confirm it took, and revert it to its schedule.

    Always leaves the entity following its schedule, even if a step fails.
    """

    try:
        for json in overrides:
            await _put_and_wait(evo, url, json)
            assert await _get_status(evo, dev_id) == expected, json

            await _put_and_wait(evo, url, revert)
            assert await _get_status(evo, dev_id) == "Scheduled", revert

    finally:
        if await _get_status(evo, dev_id) != "Scheduled":
            await _put_and_wait(evo, url, revert)


async def _test_zon_heat_setpoint(evo: EvohomeClientV0) -> None:
    """Test PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint

    Overrides a zone to its current setpoint (so is a no-op in practice) and reverts it.

    Does so with PascalCase keys (as used by the older client) and with camelCase keys
    (as used by this library), to confirm the vendor accepts either.
    """

    dev = next(
        (
            d
            for d in await _get_devices(evo)
            if is_zone_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if dev is None:
        pytest.skip("No live zone found that is following its schedule")

    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    setpoint: float = values["heatSetpoint"]["value"]
    until = (dt.now(tz=UTC) + td(hours=1)).strftime(TCC_DTM_STRFTIME)

    url = f"devices/{dev['deviceID']}/thermostat/changeableValues/heatSetpoint"

    await _test_override_then_revert(
        evo,
        dev["deviceID"],
        url,
        overrides=(
            {"Value": setpoint, "Status": "Temporary", "NextTime": until},
            {"value": setpoint, "status": "Temporary", "nextTime": until},
        ),
        revert=_ZON_REVERT,
        expected="Temporary",
    )


async def _test_dhw_changeable_values(evo: EvohomeClientV0) -> None:
    """Test PUT /devices/{dhw_id}/thermostat/changeableValues

    Holds the DHW in its current state (so is a no-op in practice) and reverts it.

    Does so with PascalCase keys (as used by the older client) and with camelCase keys
    (as used by this library), to confirm the vendor accepts either.
    """

    dev = next(
        (
            d
            for d in await _get_devices(evo)
            if is_dhw_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if dev is None:
        pytest.skip("No live DHW found that is following its schedule")

    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    mode: str = values["mode"]  # "DHWOn" | "DHWOff"
    until = (dt.now(tz=UTC) + td(hours=1)).strftime(TCC_DTM_STRFTIME)

    url = f"devices/{dev['deviceID']}/thermostat/changeableValues"

    await _test_override_then_revert(
        evo,
        dev["deviceID"],
        url,
        overrides=(
            _DHW_REVERT | {"Status": "Hold", "Mode": mode, "NextTime": until},
            {
                "status": "Hold",
                "mode": mode,
                "nextTime": until,
                "specialModes": None,
                "heatSetpoint": None,
                "coolSetpoint": None,
            },
        ),
        revert=_DHW_REVERT,
        expected="Hold",
    )


async def _test_lost_device(evo: EvohomeClientV0, *, is_dhw: bool) -> None:
    """Test a PUT to a device that is not alive (i.e. its gateway is offline).

    The vendor rejects it, whatever the body. Uses the body that reverts a device to its
    schedule, so would be a no-op even if it were accepted.
    """

    is_type = is_dhw_v0 if is_dhw else is_zone_v0

    dev = next(
        (d for d in await _get_devices(evo) if is_type(d) and not is_alive_v0(d)),
        None,
    )
    if dev is None:
        pytest.skip(f"No lost {'DHW' if is_dhw else 'zone'} found")

    if is_dhw:
        url = f"devices/{dev['deviceID']}/thermostat/changeableValues"
        json = _DHW_REVERT
    else:
        url = f"devices/{dev['deviceID']}/thermostat/changeableValues/heatSetpoint"
        json = _ZON_REVERT

    rsp = await should_fail_v0(
        evo.auth, HTTPMethod.PUT, url, json=json, status=HTTPStatus.BAD_REQUEST
    )
    assert isinstance(rsp, list), rsp
    assert rsp[0]["code"] == "DeviceIsLost", rsp
    # zone: [{'code': 'DeviceIsLost', 'message': 'Device is lost.'}]
    # DHW:  [{'code': 'DeviceIsLost', 'message': 'Device is lost.'},
    #        {'code': 'ForbiddenParameter', 'message': "'Status' is forbidden."}]


# PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint
@skipif_auth_failed
async def test_zon_heat_setpoint(evohome_v0: EvohomeClientV0) -> None:
    """Test /devices/{zone_id}/thermostat/changeableValues/heatSetpoint"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evohome_v0.update()  # get user_id
    await _test_zon_heat_setpoint(evohome_v0)


# PUT /devices/{dhw_id}/thermostat/changeableValues
@skipif_auth_failed
async def test_dhw_changeable_values(evohome_v0: EvohomeClientV0) -> None:
    """Test /devices/{dhw_id}/thermostat/changeableValues"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evohome_v0.update()  # get user_id
    await _test_dhw_changeable_values(evohome_v0)


# PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint (to a lost zone)
@skipif_auth_failed
async def test_zon_lost(evohome_v0: EvohomeClientV0) -> None:
    """Test /devices/{zone_id}/thermostat/changeableValues/heatSetpoint (lost zone)"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evohome_v0.update()  # get user_id
    await _test_lost_device(evohome_v0, is_dhw=False)


# PUT /devices/{dhw_id}/thermostat/changeableValues (to a lost DHW)
@skipif_auth_failed
async def test_dhw_lost(evohome_v0: EvohomeClientV0) -> None:
    """Test /devices/{dhw_id}/thermostat/changeableValues (lost DHW)"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evohome_v0.update()  # get user_id
    await _test_lost_device(evohome_v0, is_dhw=True)


USER_DATA = {
    "sessionId": "BE5F40A6-1234-1234-1234-A708947D6399",
    "userInfo": {
        "userID": 1234567,
        "username": "username@email.com",
        "firstname": "David",
        "lastname": "Smith",
        "streetAddress": "1 Main Street",
        "city": "London",
        "zipcode": "NW1 1AA",
        "country": "GB",
        "telephone": "",
        "userLanguage": "en-GB",
        "isActivated": True,
        "deviceCount": 0,
        "tenantID": 5,
        "securityQuestion1": "NotUsed",
        "securityQuestion2": "NotUsed",
        "securityQuestion3": "NotUsed",
        "latestEulaAccepted": False,
    },
}

FULL_DATA = {
    "locationID": 2738909,
    "name": "My Home",
    "streetAddress": "1 Main Street",
    "city": "London",
    "state": "",
    "country": "GB",
    "zipcode": "NW1 1AA",
    "type": "Residential",
    "hasStation": True,
    "devices": [
        {
            "gatewayId": 2499896,
            "deviceID": 3933910,
            "thermostatModelType": "DOMESTIC_HOT_WATER",
            "deviceType": 128,
            "name": "",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 22.77,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["DHWOn", "DHWOff"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 30.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {"mode": "DHWOff", "status": "Scheduled"},
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3933910,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 250,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432579,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Bathroom Dn",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.79,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432579,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 4,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3449740,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Bathroom Up",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.26,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 19.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3449740,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 7,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432521,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Dead Zone",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 5.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432521,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 0,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333958,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Eh",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333958,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 11,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432577,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Front Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 19.83,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 20.5, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432577,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 2,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3449703,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Kids Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 19.53,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3449703,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 6,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432578,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Kitchen",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.43,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432578,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 3,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432580,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Main Bedroom",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.72,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432580,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 5,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432576,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Main Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.14,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432576,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 1,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3450733,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Spare Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 18.81,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3450733,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 8,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333957,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "UFH",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333957,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 10,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333955,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Zv",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333955,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 9,
        },
    ],
    "oneTouchButtons": [],
    "weather": {
        "condition": "NightClear",
        "temperature": 9.0,
        "units": "Celsius",
        "humidity": 87,
        "phrase": "Clear",
    },
    "daylightSavingTimeEnabled": True,
    "timeZone": {
        "id": "GMT Standard Time",
        "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
        "offsetMinutes": 0,
        "currentOffsetMinutes": 0,
        "usingDaylightSavingTime": True,
    },
    "oneTouchActionsSuspended": False,
    "isLocationOwner": True,
    "locationOwnerID": 2263181,
    "locationOwnerName": "David Smith",
    "locationOwnerUserName": "null@gmail.com",
    "canSearchForContractors": True,
    "contractor": {
        "info": {"contractorID": 1839},
        "monitoring": {"levelOfAccess": "Partial", "contactPreferences": []},
    },
}
