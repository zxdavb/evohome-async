"""Invoke every vendor RESTful API (URL) of the v0 API (as used by the v1 client).

This is used to document the RESTful API that is provided by the vendor. Together with
the schema module (src/evohomeasync/schemas.py), whose TypedDicts record the shape of
each request/response, these tests are the documentation of that API: they confirm that
each endpoint exists, and how it behaves.

Testing is at HTTP request layer (e.g. GET/PUT). The base URL is URL_BASE_V0, i.e.
https://tccna.resideo.com/WebAPI/api, and all endpoints below are relative to it.

  Entity    Method    Endpoint (all tested here, unless noted otherwise)
  --------  --------  -------------------------------------------------------------------

  user      GET       /accountInfo

  location  GET       /locations?userId={usr_id}[&allData=True]
            GET       /locations?locationId={loc_id}[&allData=True]

  gateway   GET       /gateways?locationId={loc_id}[&allData=True]

  device    GET       /devices?locationId={loc_id}[&allData=True]
            GET       /devices/{dev_id}
            GET       /devices/{dev_id}/thermostat
            GET, PUT  /devices/{dev_id}/thermostat/changeableValues

            PUT       /devices/{zon_id}/thermostat/changeableValues/heatSetpoint  (a zone)

  TCS       PUT       /evoTouchSystems?locationId={loc_id}  (removed by the vendor: a 404)

  task      GET       /commTasks?commTaskId={tsk_id}

There is no longer any v0 URL to change a TCS's mode. Zones and
DHW are both devices, distinguished by thermostatModelType (e.g. EMEA_ZONE, or
DOMESTIC_HOT_WATER), and so share the same URLs, except that only a zone has
.../heatSetpoint (a shortcut to the HeatSetpoint of its changeableValues). A PUT of
changeableValues requires different keys (and allows different modes) for each.

The API is regular, and these tests confirm the following conventions:
- allData=True adds an entity's children: a location's devices (and its
  oneTouchButtons, and any weather or contractor), a gateway's devices, and a device's
  thermostat (and alertSettings)

- an entity's own URL returns the same object as is nested within its parent's, except
  that a device's thermostat excludes its changeableValues, and that changeableValues
  include a changeSource (e.g. modeChangeSource) that the nested object does not (this
  is so for a live device, but it has been seen absent for a lost one)

- responses are camelCase, but IDs are cased inconsistently: userID, locationID,
  deviceID and gatewayID (of a gateway), but gatewayId (of a device), and locationId
  (of a gateway); the keys of a request are case-insensitive

- datetimes are in the location's local time, not UTC: e.g. a
  NextTime is returned without a Z, and a Z on one that is sent is ignored (so
  "2026-09-22T23:00:00Z" is 22:00 UTC, when the location is on BST)

- a GET returns 200 (OK), but a PUT returns 201 (Created) and the id of a comm task,
  e.g. {"id": 1234567890} (an int)

- a GET of a PUT-only URL is 404 (Not Found), as is any other invalid URL (which
  returns HTML, not JSON), and the id of another user's entity is 401 (Unauthorized)

- a PUT to a device that is not alive is 400 (DeviceIsLost), see test_v0_urls_auth.py

- a PUT is sometimes answered with the comm task of an earlier, equivalent PUT (which
  has already succeeded), and is not applied, e.g. a revert to schedule within minutes
  of another; the rule for this is not known (see is_stale_task_v0() in common.py)

- otherwise, a change has appeared via GET within a second of its comm task succeeding

Every PUT here is a no-op on a real system: it (re)asserts the current state of an
entity (e.g. a zone that is already following its schedule), and is skipped otherwise.
So these tests will not disturb anyone's heating.

The request bodies are those of the older (non-async) client, which were in PascalCase.
"""

from __future__ import annotations

import asyncio
import logging
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from _evohome import exceptions as exc
from evohomeasync.auth import Auth
from evohomeasync.schemas import (
    TCC_GET_COMM_TASK,
    TCC_GET_USR_INFO,
    TCC_GET_USR_LOCS,
    TCC_TASK_RESPONSE,
)
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import (
    is_alive_v0,
    is_dhw_v0,
    is_zone_v0,
    skipif_auth_failed,
    status_of_v0,
    task_id_v0,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from evohome_cli.auth import TokenCacheManager
    from evohomeasync.schemas import (
        TccCommTaskResponseT,
        TccLocationResponseT,
        TccSessionResponseT,
        TccTaskResponseT,
        TccUserAccountInfoResponseT,
    )


_TASK_TIMEOUT = 60  # seconds, for a comm task to succeed
# NOTE: a comm task usually succeeds within 10s, but was measured exceeding 30s
# when several PUTs were in flight, so this budget is deliberately generous

# The keys that allData=True adds to each entity (i.e. its children, and some others);
# a location's weather & contractor are NotRequired (c.f. TccLocationResponseT)
_LOC_ALL_DATA_KEYS = {"devices", "oneTouchButtons"}
_LOC_ALL_DATA_KEYS_OPT = {"contractor", "weather"}  # e.g. only if it has a contractor
_GWY_ALL_DATA_KEYS = {"devices"}
_DEV_ALL_DATA_KEYS = {"alertSettings", "thermostat"}


async def _get_dict(auth: Auth, url: str) -> dict[str, Any]:
    """GET a URL whose response is a JSON object, and return it."""

    rsp = await auth._make_request(HTTPMethod.GET, url)
    assert isinstance(rsp, dict), rsp
    return rsp


async def _get_list(auth: Auth, url: str) -> list[dict[str, Any]]:
    """GET a URL whose response is a JSON array, and return it."""

    rsp = await auth._make_request(HTTPMethod.GET, url)
    assert isinstance(rsp, list), rsp
    return rsp


#######################################################################################
# The user


async def _post_session(auth: Auth) -> TccSessionResponseT:
    """Test POST /session

    Authenticates the user, and returns a sessionId (and the user's account info):
      json = {
        "Username": username,
        "Password": password,
        "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
      }

    It is tested in test_v0_urls_cred.py (which is where it is documented).
    """

    raise NotImplementedError


async def get_account_info(auth: Auth) -> TccUserAccountInfoResponseT:
    """Test GET /accountInfo

    Returns the account of the (authenticated) user, including its userID:
      {"userID": 1234567, "username": "username@email.com", "firstname": "David", ...}

    NOTE: the userID is an int.
    """

    return TCC_GET_USR_INFO(
        await auth._make_request(
            HTTPMethod.GET,
            "accountInfo",
        )
    )


#######################################################################################
# Locations, gateways and devices (all GET-only)


async def get_locations(auth: Auth, usr_id: int) -> list[TccLocationResponseT]:
    """Test GET /locations?userId={usr_id}&allData=True

    Returns every location of the user, including their devices (and each device's
    thermostat), and their weather:
      [
        {
          "locationID": 2738909,
          "name": "My Home",
          ...
          "devices": [{"deviceID": 3432521, "thermostat": {...}, ...}],
          "oneTouchButtons": [],
          "weather": {"condition": "Sunny", "temperature": 13.0, ...},
          ...
        }
      ]

    Without allData=True, the vendor omits each location's devices, oneTouchButtons,
    weather and contractor (the latter two are included only if the location has them,
    e.g. contractor only if it has one). A location may have no devices (e.g. when it is
    newly created).
    """

    return TCC_GET_USR_LOCS(
        await auth._make_request(
            HTTPMethod.GET,
            f"locations?userId={usr_id}&allData=True",
        )
    )


async def get_location(auth: Auth, loc_id: int) -> TccLocationResponseT:
    """Test GET /locations?locationId={loc_id}&allData=True

    Returns the location (not a list of one), as per GET /locations?userId={usr_id}.

    Without allData=True, the vendor omits its devices, oneTouchButtons, weather and
    contractor.
    """

    rsp = await _get_dict(auth, f"locations?locationId={loc_id}&allData=True")
    return TCC_GET_USR_LOCS([rsp])[0]  # the schema is for a list of locations


async def get_gateways(auth: Auth, loc_id: int) -> list[dict[str, Any]]:
    """Test GET /gateways?locationId={loc_id}

    Returns the gateways of the location:
      [
        {
          "gatewayID": 2499896,
          "mac": "00D02DEE4E56",
          "crc": "17C2",
          "locationId": 2738909,
          "isUpgrading": false,
          "isRedlinkGateway": false
        }
      ]

    NOTE: the gateway's id is gatewayID, but a device's reference to it is gatewayId.
    With allData=True, the vendor adds each gateway's devices, as per GET /devices.
    """

    return await _get_list(auth, f"gateways?locationId={loc_id}")


async def get_devices(auth: Auth, loc_id: int) -> list[dict[str, Any]]:
    """Test GET /devices?locationId={loc_id}&allData=True

    Returns the devices (zones & DHW) of the location, as per the location's devices:
      [{"gatewayId": 2499896, "deviceID": 3432521, "thermostat": {...}, ...}]

    Without allData=True, the vendor omits each device's thermostat and alertSettings.
    See TccDeviceResponseT for the shape of a device (with allData=True).
    """

    return await _get_list(auth, f"devices?locationId={loc_id}&allData=True")


async def get_device(auth: Auth, dev_id: int) -> dict[str, Any]:
    """Test GET /devices/{dev_id}

    Returns the device, but without its thermostat and alertSettings (there is no
    allData param), i.e. as per GET /devices?locationId={loc_id}:
      {
        "gatewayId": 2499896,
        "deviceID": 3432521,
        "thermostatModelType": "EMEA_ZONE",
        "name": "Living room",
        "isAlive": true,
        ...
      }
    """

    return await _get_dict(auth, f"devices/{dev_id}")


async def get_thermostat(auth: Auth, dev_id: int) -> dict[str, Any]:
    """Test GET /devices/{dev_id}/thermostat

    Returns the device's thermostat, but without its changeableValues:
      {
        "units": "Celsius",
        "indoorTemperature": 21.5,
        "indoorTemperatureStatus": "Measured",
        "outdootHumidityAvailable": false,  # NOTE: not a typo
        ...
      }

    See TccThermostatResponseT for the shape of a thermostat (with changeableValues).
    """

    return await _get_dict(auth, f"devices/{dev_id}/thermostat")


async def get_changeable_values(auth: Auth, dev_id: int) -> dict[str, Any]:
    """Test GET /devices/{dev_id}/thermostat/changeableValues

    Returns the thermostat's changeableValues, plus the source of the last change (which
    is not in the changeableValues nested within the thermostat), e.g. for a zone:
      {
        "mode": "Off",
        "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
        "vacationHoldDays": 0,
        "heatSetpointChangeSource": {"partnerName": "EMEA", "changeTag": ""}
      }

    and for a DHW:
      {
        "mode": "DHWOff",
        "status": "Scheduled",
        "modeChangeSource": {"partnerName": "EMEA", "changeTag": ""}
      }

    The changeSource is present for a live device, but has been seen absent for a lost
    one. See TccZoneChangeableValuesT and TccDhwChangeableValuesT (neither of which has
    the changeSource). There is no GET of .../changeableValues/heatSetpoint (a 404).
    """

    return await _get_dict(auth, f"devices/{dev_id}/thermostat/changeableValues")


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_loc_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test the (GET-only) Location, Gateway and Device URLs.

    Confirms how each relates to the others (e.g. each entity's own URL returns the
    same object as is nested within its parent's), by comparing their keys (rather than
    their values, some of which, e.g. temperatures, may change between requests).
    """

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # GET /accountInfo
    usr_info = await get_account_info(auth)

    #
    # GET /locations?userId={usr_id}&allData=True
    usr_locs = await get_locations(auth, usr_info["userID"])

    loc = next((loc for loc in usr_locs if loc["devices"]), None)
    if loc is None:
        pytest.skip("No location with devices found")

    loc_id: int = loc["locationID"]

    # ...and without allData=True
    locs = await _get_list(auth, f"locations?userId={usr_info['userID']}")
    loc_sum = next(loc for loc in locs if loc["locationID"] == loc_id)

    extra = set(loc) - set(loc_sum)
    assert _LOC_ALL_DATA_KEYS <= extra <= _LOC_ALL_DATA_KEYS | _LOC_ALL_DATA_KEYS_OPT

    #
    # GET /locations?locationId={loc_id}&allData=True
    loc_one = await get_location(auth, loc_id)
    assert set(loc_one) == set(loc)  # is as per the user's locations

    # ...and without allData=True
    loc_one_sum = await _get_dict(auth, f"locations?locationId={loc_id}")
    assert set(loc_one_sum) == set(loc_sum)

    #
    # GET /gateways?locationId={loc_id}
    gwys = await get_gateways(auth, loc_id)
    assert {g["gatewayID"] for g in gwys} == {d["gatewayId"] for d in loc["devices"]}

    # ...and with allData=True, which adds each gateway's devices
    gwys_all = await _get_list(auth, f"gateways?locationId={loc_id}&allData=True")
    assert set(gwys_all[0]) - set(gwys[0]) == _GWY_ALL_DATA_KEYS
    assert {d["deviceID"] for g in gwys_all for d in g["devices"]} == {
        d["deviceID"] for d in loc["devices"]
    }

    #
    # GET /devices?locationId={loc_id}&allData=True
    devs = {d["deviceID"]: d for d in await get_devices(auth, loc_id)}
    assert list(devs) == [d["deviceID"] for d in loc["devices"]]

    # ...and without allData=True
    devs_sum = {
        d["deviceID"]: d for d in await _get_list(auth, f"devices?locationId={loc_id}")
    }
    assert list(devs_sum) == list(devs)

    #
    # For each device (both zones and DHW)...
    for dev_all in loc["devices"]:
        dev_id: int = dev_all["deviceID"]

        assert set(devs[dev_id]) == set(dev_all)  # as per the location's devices
        assert set(dev_all) - set(devs_sum[dev_id]) == _DEV_ALL_DATA_KEYS

        #
        # GET /devices/{dev_id}
        dev = await get_device(auth, dev_id)
        assert set(dev) == set(devs_sum[dev_id])  # i.e. is without allData=True

        #
        # GET /devices/{dev_id}/thermostat
        thm = await get_thermostat(auth, dev_id)
        assert set(dev_all["thermostat"]) - set(thm) == {"changeableValues"}

        #
        # GET /devices/{dev_id}/thermostat/changeableValues
        cvs = await get_changeable_values(auth, dev_id)
        extra = set(cvs) - set(dev_all["thermostat"]["changeableValues"])

        source = (
            "modeChangeSource" if is_dhw_v0(dev_all) else "heatSetpointChangeSource"
        )
        if is_alive_v0(dev_all):
            assert extra == {source}, extra
        else:  # it has been seen absent for a lost device (maybe as it's not changed?)
            assert extra <= {source}, extra


#######################################################################################
# The TCS


async def put_evo_touch_systems(
    auth: Auth, loc_id: int, json: Mapping[str, object]
) -> TccTaskResponseT:
    """Test PUT /evoTouchSystems?locationId={loc_id}

    Once set the mode of the location's TCS, but has been removed by the vendor (it is
    now a 404, for any method, so there is no longer any way to do so via this API):
      json = {
        "QuickAction": mode,  # All except AutoWithEco, Auto must have QANT None
        "QuickActionNextTime": None | until.strftime("%Y-%m-%dT%H:%M:%SZ"),
      }
    """

    return TCC_TASK_RESPONSE(
        await auth._make_request(
            HTTPMethod.PUT,
            f"evoTouchSystems?locationId={loc_id}",
            json=json,
        )
    )


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location and TCS URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # GET /accountInfo
    usr_info = await get_account_info(auth)

    #
    # GET /locations?userId={usr_id}&allData=True
    usr_locs = await get_locations(auth, usr_info["userID"])

    # an evohome location (not, say, a Round Thermostat)
    loc_id = next(
        (
            loc["locationID"]
            for loc in usr_locs
            if any(is_zone_v0(d) for d in loc["devices"])
        ),
        None,
    )
    if loc_id is None:
        pytest.skip("No evohome location found")

    #
    # PUT /evoTouchSystems?locationId={loc_id}
    # NOTE: this URL doesn't work - has been removed by the vendor
    json = {"QuickAction": "Auto", "QuickActionNextTime": None}
    with pytest.raises(exc.ApiCallFailedError) as err:
        _ = await put_evo_touch_systems(auth, loc_id, json)
    assert err.value.status == HTTPStatus.NOT_FOUND
    # '<!DOCTYPE html PUBLIC ... 404 - File or directory not found ...'  (from IIS)


#######################################################################################
# A device (a zone or DHW)


async def put_changeable_values(
    auth: Auth, dev_id: int, json: Mapping[str, object]
) -> TccTaskResponseT:
    """Test PUT /devices/{dev_id}/thermostat/changeableValues

    Sets the changeableValues of the device, whose required keys (and allowed modes)
    depend upon whether it is a zone or DHW. For a zone (Mode is Heat or Off), with a
    HeatSetpoint as per PUT .../changeableValues/heatSetpoint:
      json = {"Mode": mode, "HeatSetpoint": {"Value": None, "Status": "Scheduled"}}

    For a DHW (Mode is DHWOn or DHWOff), which has no HeatSetpoint:
      json = {"Mode": mode}

    Returns a comm task, e.g. {"id": 1234567890}.

    Errors (all 400, Bad Request), for more see test_v0_urls_auth.py:
      ParameterIsMissing:        e.g. no Mode, or (a zone) no HeatSetpoint
      ThermostatModeNotAllowed:  e.g. "Allowed modes are Heat, Off." (a zone)

    NOTE: on some installations (e.g. the test installation), the vendor forbids a DHW's
    Status and NextTime (which the older client sent), so a DHW can't be set to follow
    its schedule, nor to a mode until a given time, via this API - see
    test_v0_urls_auth.py.
    """

    return TCC_TASK_RESPONSE(
        await auth._make_request(
            HTTPMethod.PUT,
            f"devices/{dev_id}/thermostat/changeableValues",
            json=json,
        )
    )


#######################################################################################
# A zone


async def put_devices_zon(
    auth: Auth, zon_id: int, json: Mapping[str, object]
) -> TccTaskResponseT:
    """Test PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint

    Sets the setpoint of the zone, either permanently (Hold), or until a given time
    (Temporary), or has it follow its schedule (Scheduled):
      json = {"Value": temperature, "Status": "Hold",      "NextTime": None}
      json = {"Value": temperature, "Status": "Temporary", "NextTime": until}
      json = {"Value": None,        "Status": "Scheduled", "NextTime": None}

    Returns a comm task, e.g. {"id": 1234567890}. This URL is PUT-only (a GET is a 404).
    The same can be done via PUT .../changeableValues (with a Mode, and this body as its
    HeatSetpoint).

    NOTE: the NextTime is in the location's local time: any Z is ignored.

    NOTE: the vendor sometimes answers this with the comm task of an earlier, equivalent
    PUT (which has already succeeded), and does not apply it, even if the zone has since
    been overridden: this has been seen repeatedly for a revert to schedule (which has
    only the one form). See is_stale_task_v0() in common.py.
    """

    return TCC_TASK_RESPONSE(
        await auth._make_request(
            HTTPMethod.PUT,
            f"devices/{zon_id}/thermostat/changeableValues/heatSetpoint",
            json=json,
        )
    )


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_zon_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Zone URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 0: find a zone that is following its schedule...
    usr_info = await get_account_info(auth)
    usr_locs = await get_locations(auth, usr_info["userID"])

    zone = next(
        (
            d
            for loc in usr_locs
            for d in loc["devices"]
            if is_zone_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if zone is None:
        pytest.skip("No live zone found that is following its schedule")

    json: dict[str, Any]

    #
    # PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    json = {"Value": None, "Status": "Scheduled", "NextTime": None}  # a no-op
    task = await put_devices_zon(auth, zone["deviceID"], json)

    #
    # GET /commTasks?commTaskId={tsk_id}
    await _wait_for_task(auth, task)

    #
    # PUT /devices/{zon_id}/thermostat/changeableValues (the same, but the long way)
    json = {
        "Mode": zone["thermostat"]["changeableValues"]["mode"],  # e.g. Off
        "HeatSetpoint": {"Value": None, "Status": "Scheduled", "NextTime": None},
    }  # a no-op
    task = await put_changeable_values(auth, zone["deviceID"], json)

    #
    # GET /commTasks?commTaskId={tsk_id}
    await _wait_for_task(auth, task)


#######################################################################################
# A DHW


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_dhw_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test DHW URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 0: find a live DHW...
    usr_info = await get_account_info(auth)
    usr_locs = await get_locations(auth, usr_info["userID"])

    # NOTE: no need for it to be following its schedule: setting a DHW to its current
    # mode is a no-op whatever its status (and there is no way to restore that status)
    dhw = next(
        (
            d
            for loc in usr_locs
            for d in loc["devices"]
            if is_dhw_v0(d) and is_alive_v0(d)
        ),
        None,
    )
    if dhw is None:
        pytest.skip("No live DHW found")

    #
    # PUT /devices/{dhw_id}/thermostat/changeableValues
    json = {"Mode": dhw["thermostat"]["changeableValues"]["mode"]}  # a no-op
    task = await put_changeable_values(auth, dhw["deviceID"], json)

    #
    # GET /commTasks?commTaskId={tsk_id}
    await _wait_for_task(auth, task)


#######################################################################################
# A comm task


async def get_comm_tasks(auth: Auth, tsk_id: int | str) -> TccCommTaskResponseT:
    """Test GET /commTasks?commTaskId={tsk_id}

    Returns the state of the comm task (as returned by a PUT), and what it acted upon:
      {
        "state": "Succeeded",
        "started": "2026-09-22T20:08:04.053",  # TZ-naive
        "finished": "2026-09-22T20:08:07.13",  # TZ-naive, and only once finished
        "macId": "00D02D67C990",
        "gatewayId": 2678129,
        "deviceId": 6860918,
        "activityId": "0187be9d-1f3c-41e7-abd6-28f5442feddd"
      }

    NOTE: the task's own id is not included. Only "Succeeded" is known to be terminal
    (the older client polled until it saw it).
    """

    return TCC_GET_COMM_TASK(
        await auth._make_request(
            HTTPMethod.GET,
            f"commTasks?commTaskId={tsk_id}",
        )
    )


async def _wait_for_task(auth: Auth, response: TccTaskResponseT) -> None:
    """Wait for the comm task of a PUT to succeed (GET /commTasks?commTaskId=...)."""

    task_id = task_id_v0(response)

    async with asyncio.timeout(_TASK_TIMEOUT):
        while True:
            task = await get_comm_tasks(auth, task_id)
            if task["state"] == "Succeeded":
                return
            await asyncio.sleep(0.5)
