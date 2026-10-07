"""Validate the handling of the vendor's v0 APIs (URLs): their errors and edge cases.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server (if any) is behaving as per a)

Where test_v0_urls.py documents each endpoint (and has a list of them all), this module
documents how they fail: e.g. an unauthorized user or wrong method, a PUT with invalid
(or forbidden) params, and a PUT to a device that is not alive. It also allows for the
vendor sometimes not applying a PUT that is equivalent to an earlier one (see
is_stale_task_v0() in common.py).

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used), although
the keys of a request are case-insensitive (as confirmed here).
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
from tests.const import (
    _DBG_USE_REAL_AIOHTTP,
    TEST_LOC_IDX,
    TIMEOUT_COMM_TASK_V0,
    URL_BASE_V0,
)

from .common import (
    error_codes,
    get_loc,
    is_alive_v0,
    is_dhw_v0,
    is_stale_task_v0,
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

    from evohomeasync import EvohomeClient as EvohomeClientV0
    from evohomeasync.schemas import TccDeviceResponseT, TccLocationResponseT


async def _test_usr_locations(evo: EvohomeClientV0) -> None:
    """Test /locations?userId={user_id}&allData=True"""

    usr_id: int = evo.user_account["user_id"]
    # loc_id: int = evo.location_id

    url = f"locations?userId={usr_id}&allData=True"
    _ = await should_work_v0(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_LOCS)

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
    loc_id = get_loc(evo).id

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


# A change appears via allData=True within ~0.5s of its comm task succeeding, but poll
# for it anyway (rather than asserting it at once), as there's no guarantee of that.
_STATUS_INTERVAL = 2  # seconds, between polls of that view

# the older (non-async) client's body for reverting a zone to its schedule
_ZON_REVERT = {"Value": None, "Status": "Scheduled", "NextTime": None}

# NOTE: on some installations (e.g. the test installation), the vendor requires "Mode" on
# a DHW's changeableValues, and forbids a non-null Status or NextTime (so the older
# client's fuller body fails on its Status alone):
#   {"Status": "Scheduled"} -> 400, ForbiddenParameter: 'Status' is forbidden.
#   {"NextTime": <dtm>}     -> 400, ForbiddenParameter: 'NextTime' is forbidden.
#   {}                      -> 400, ParameterIsMissing: 'ThermostatMode' is required.
# There, a Mode-only PUT against the DHW's schedule succeeds but is not applied. It is not
# known if this is so of all DHWs, so _test_dhw_forbidden_params() skips a DHW that
# accepts Status.
_DHW_MODES = ("DHWOn", "DHWOff")


async def _get_location(evo: EvohomeClientV0) -> TccLocationResponseT:
    """Return the (vendor-cased) location under test."""

    usr_id: int = evo.user_account["user_id"]

    url = f"locations?userId={usr_id}&allData=True"
    locs = await should_work_v0(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_LOCS)

    return locs[TEST_LOC_IDX]


async def _get_devices(evo: EvohomeClientV0) -> list[TccDeviceResponseT]:
    """Return all the (vendor-cased) devices of the location under test."""
    return (await _get_location(evo))["devices"]


async def _get_status(evo: EvohomeClientV0, dev_id: int) -> str | None:
    """Return the current status of a zone/DHW, e.g. "Scheduled"."""
    return status_of_v0(
        next(d for d in await _get_devices(evo) if d["deviceID"] == dev_id)
    )


async def _put_and_wait(
    evo: EvohomeClientV0, url: str, json: Mapping[str, object]
) -> bool:
    """PUT a change, wait for its comm task to succeed, and return True if it applied.

    Returns False if the vendor did not apply the PUT (i.e. it returned the comm task of an
    earlier, equivalent PUT), in which case it has not applied the change.
    """

    sent = dt.now(tz=UTC)

    rsp = await should_work_v0(evo.auth, HTTPMethod.PUT, url, json=json)
    # {"id": 1234567890}  (an int; the older client also allowed for a list of one)

    task = await wait_for_comm_task_v0(evo.auth, task_id_v0(rsp))
    # {"state": "Succeeded", "started": "2026-09-22T20:08:04.053", ...}

    return not is_stale_task_v0(task, sent)


async def _wait_for_status(
    evo: EvohomeClientV0, dev_id: int, expected: str
) -> str | None:
    """Poll a zone/DHW until its status is the expected one, and return the last seen.

    Returns the last-seen status (not necessarily the expected one), so that the caller
    can assert against it and get a useful failure message.
    """

    status: str | None = None

    try:
        async with asyncio.timeout(TIMEOUT_COMM_TASK_V0):
            while True:
                if (status := await _get_status(evo, dev_id)) == expected:
                    return status

                await asyncio.sleep(_STATUS_INTERVAL)

    except TimeoutError:
        return status


async def _find_scheduled_zone(evo: EvohomeClientV0) -> TccDeviceResponseT:
    """Return a live zone that is following its schedule (else skip the test)."""

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
    return dev


async def _get_next_time(evo: EvohomeClientV0, dev_id: int) -> str | None:
    """Return the NextTime of a zone's setpoint (via v0, so local time, without a Z)."""

    dev = next(d for d in await _get_devices(evo) if d["deviceID"] == dev_id)
    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    next_time: str | None = values["heatSetpoint"].get("nextTime")
    return next_time


async def _test_zon_heat_setpoint(evo: EvohomeClientV0) -> None:
    """Test PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint

    Overrides a zone to its current setpoint (so is a no-op in practice), confirming that
    each override is applied, and then reverts it to its schedule (with the older
    client's body).

    Does so with PascalCase keys (as used by the older client) and with camelCase keys
    (as used by this library), to confirm the vendor accepts either. The two overrides
    have a different NextTime, as otherwise the vendor might not apply the second.

    Also confirms that a NextTime is returned (via GET) as sent, but without its Z: it
    is the location's local time, not UTC.

    The vendor may not apply a revert (see is_stale_task_v0() in common.py), e.g. if
    another test has sent one recently, so it is asserted only if it was applied.
    """

    dev = await _find_scheduled_zone(evo)
    dev_id: int = dev["deviceID"]

    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    setpoint: float = values["heatSetpoint"]["value"]

    url = f"devices/{dev_id}/thermostat/changeableValues/heatSetpoint"

    # the location's wall-clock time, as the vendor treats NextTime as such (and so
    # ignores its Z), else the overrides would be shorter/longer (or in the past)
    offset: int = (await _get_location(evo))["timeZone"]["currentOffsetMinutes"]
    now = (dt.now(tz=UTC) + td(minutes=offset)).replace(
        minute=0, second=0, microsecond=0
    )

    for hours, keys in (
        (2, ("Value", "Status", "NextTime")),  # PascalCase (as the older client)
        (3, ("value", "status", "nextTime")),  # camelCase (as this library)
    ):
        next_time = now + td(hours=hours)  # on the hour (so not rounded)
        until = next_time.strftime(TCC_DTM_STRFTIME)  # with a Z

        json = dict(zip(keys, (setpoint, "Temporary", until), strict=True))

        assert await _put_and_wait(evo, url, json), json  # i.e. was applied
        assert await _wait_for_status(evo, dev_id, "Temporary") == "Temporary", json

        # the NextTime is returned as sent, but without the Z (as it's local time)
        assert await _get_next_time(evo, dev_id) == until.removesuffix("Z")

    if await _put_and_wait(evo, url, _ZON_REVERT):  # i.e. was applied
        assert await _wait_for_status(evo, dev_id, "Scheduled") == "Scheduled"


async def _test_dhw_changeable_values(evo: EvohomeClientV0) -> None:
    """Test PUT /devices/{dhw_id}/thermostat/changeableValues

    Sets the DHW to its current mode (so is a no-op in practice).

    Does so with a PascalCase key (as used by the older client) and with a camelCase key
    (as used by this library), to confirm the vendor accepts either.
    """

    dev = next(
        (d for d in await _get_devices(evo) if is_dhw_v0(d) and is_alive_v0(d)),
        None,
    )
    if dev is None:
        pytest.skip("No live DHW found")

    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    mode: str = values["mode"]
    assert mode in _DHW_MODES, mode

    url = f"devices/{dev['deviceID']}/thermostat/changeableValues"

    for json in ({"Mode": mode}, {"mode": mode}):  # the vendor accepts either casing
        await _put_and_wait(evo, url, json)


async def _test_dhw_forbidden_params(evo: EvohomeClientV0) -> None:
    """Test the params that PUT /devices/{dhw_id}/thermostat/changeableValues rejects.

    On some installations (e.g. the test installation), the vendor forbids a DHW's
    Status and NextTime, and requires its Mode (see the NOTE above _DHW_MODES). Skipped
    for a DHW that accepts its Status, as then this is not its contract.

    Note that the vendor normalises key casing before reporting an offending key.
    """

    dev = next(
        (d for d in await _get_devices(evo) if is_dhw_v0(d) and is_alive_v0(d)),
        None,
    )
    if dev is None:
        pytest.skip("No live DHW found")

    values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
    mode: str = values["mode"]
    until = (dt.now(tz=UTC) + td(hours=1)).strftime(TCC_DTM_STRFTIME)

    url = f"devices/{dev['deviceID']}/thermostat/changeableValues"

    # the DHW's current Mode and Status, so this probe is a no-op if accepted
    probe = {"Mode": mode, "Status": values["status"]}
    async with evo.auth.websession.request(
        HTTPMethod.PUT,
        f"{URL_BASE_V0}/{url}",
        json=probe,
        headers=await evo.auth._headers(),
    ) as probe_rsp:
        if probe_rsp.ok:
            pytest.skip("This DHW accepts a Status, so doesn't have this contract")

    json: Mapping[str, object]

    # Mode is required...
    for json in ({}, {"Mode": None}):
        rsp = await should_fail_v0(
            evo.auth, HTTPMethod.PUT, url, json=json, status=HTTPStatus.BAD_REQUEST
        )
        assert error_codes(rsp) == ["ParameterIsMissing"], rsp

    # ...Status and NextTime are forbidden, but only when their value is not null...
    for json in (
        {"Mode": mode, "Status": "Hold"},
        {"Mode": mode, "NextTime": until},
    ):
        rsp = await should_fail_v0(
            evo.auth, HTTPMethod.PUT, url, json=json, status=HTTPStatus.BAD_REQUEST
        )
        assert error_codes(rsp) == ["ForbiddenParameter"], rsp

    # ...as the vendor validates only non-null values (and ignores unknown keys), so
    # the older client's revert body fails on its Status alone...
    rsp = await should_fail_v0(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json={
            "Status": "Scheduled",
            "Mode": mode,
            "NextTime": None,
            "SpecialModes": None,
            "HeatSetpoint": None,
            "CoolSetpoint": None,
        },
        status=HTTPStatus.BAD_REQUEST,
    )
    assert error_codes(rsp) == ["ForbiddenParameter"], rsp

    # ...and that same body, with its Status dropped, is accepted...
    # NOTE: this test documents which params the vendor accepts, so it doesn't wait for
    # the resulting comm task (each PUT here is a no-op, as Mode is the current mode)
    _ = await should_work_v0(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json={
            "Mode": mode,
            "NextTime": None,
            "SpecialModes": None,
            "HeatSetpoint": None,
            "CoolSetpoint": None,
        },
    )

    # ...and Mode accepts only DHWOn/DHWOff (in particular, there is no Auto)...
    rsp = await should_fail_v0(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json={"Mode": "Off"},  # a valid ThermostatMode, but not for a DHW
        status=HTTPStatus.BAD_REQUEST,
    )
    assert error_codes(rsp) == ["ThermostatModeNotAllowed"], rsp

    rsp = await should_fail_v0(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json={"Mode": "Auto"},  # not a ThermostatMode at all
        status=HTTPStatus.BAD_REQUEST,
    )
    assert error_codes(rsp) == ["InvalidInput"], rsp


async def _test_lost_device(evo: EvohomeClientV0, *, is_dhw: bool) -> None:
    """Test a PUT to a device that is not alive (i.e. its gateway is offline).

    The vendor rejects it, whatever the body. Uses a body that is accepted for a live
    device, so would be a no-op even if it were accepted here.
    """

    is_type = is_dhw_v0 if is_dhw else is_zone_v0

    dev = next(
        (d for d in await _get_devices(evo) if is_type(d) and not is_alive_v0(d)),
        None,
    )
    if dev is None:
        pytest.skip(f"No lost {'DHW' if is_dhw else 'zone'} found")

    json: Mapping[str, object]

    if is_dhw:
        url = f"devices/{dev['deviceID']}/thermostat/changeableValues"
        values: dict[str, Any] = dict(dev["thermostat"]["changeableValues"])
        json = {"Mode": values["mode"]}
    else:
        url = f"devices/{dev['deviceID']}/thermostat/changeableValues/heatSetpoint"
        json = _ZON_REVERT

    rsp = await should_fail_v0(
        evo.auth, HTTPMethod.PUT, url, json=json, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["DeviceIsLost"], rsp
    # [{'code': 'DeviceIsLost', 'message': 'Device is lost.'}]


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


# PUT /devices/{dhw_id}/thermostat/changeableValues (with rejected params)
@skipif_auth_failed
async def test_dhw_forbidden_params(evohome_v0: EvohomeClientV0) -> None:
    """Test /devices/{dhw_id}/thermostat/changeableValues (rejected params)"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evohome_v0.update()  # get user_id
    await _test_dhw_forbidden_params(evohome_v0)


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
