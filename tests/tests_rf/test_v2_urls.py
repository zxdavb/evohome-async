"""Invoke every vendor RESTful API (URL) of the v2 API.

This is used to document the RESTful API that is provided by the vendor. Together with
the schema modules (src/evohomeasync2/schemas/*.py), whose TypedDicts record the shape
of each request/response, these tests are the documentation of that API: they confirm
that each endpoint exists, and how it behaves.

Testing is at HTTP request layer (e.g. GET/PUT). The base URL is URL_BASE_V2, i.e.
https://tccna.resideo.com/WebAPI/emea/api/v1, and all endpoints below are relative to it.

  Entity    Method    Endpoint (all tested here, unless noted otherwise)
  --------  --------  -------------------------------------------------------------------

  user      GET       /userAccount

  location  GET       /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
            GET       /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True
            GET       /location/{loc_id}/status?includeTemperatureControlSystems=True

  gateway   GET       /gateway/{gwy_id}/installationInfo?includeTemperatureControlSystems=True
            GET       /gateway/{gwy_id}/status?includeTemperatureControlSystems=True

  TCS       GET       /temperatureControlSystem/{tcs_id}/installationInfo
            GET       /temperatureControlSystem/{tcs_id}/status
            PUT       /temperatureControlSystem/{tcs_id}/mode

  zone      GET       /temperatureZone/{zon_id}/installationInfo
            GET       /temperatureZone/{zon_id}/status
            PUT       /temperatureZone/{zon_id}/heatSetpoint
            GET, PUT  /temperatureZone/{zon_id}/schedule

  DHW       GET       /domesticHotWater/{dhw_id}/installationInfo
            GET       /domesticHotWater/{dhw_id}/status
            PUT       /domesticHotWater/{dhw_id}/state
            GET, PUT  /domesticHotWater/{dhw_id}/schedule

  task      GET       /commTasks?commTaskId={tsk_id}  (see test_v2_urls_task.py)

The API is regular, and these tests confirm the following conventions:
- every entity has an installationInfo endpoint (its config) and a status endpoint (its
  state); those of a TCS always include those of its zones (and DHW), but those of a
  location or gateway include those of its TCSs if (and only if)
  includeTemperatureControlSystems=True

- each entity's installationInfo is the same object as found nested within that of its
  parent (e.g. a TCS's is as found within its gateway's), so shares its schema

- a GET returns 200 (OK), but a PUT returns 201 (Created) and the id of a comm task,
  e.g. {"id": "1234567890"}, which can be polled (see test_v2_urls_task.py)

- a PUT is sometimes answered with the comm task of an earlier, equivalent PUT, as via
  the v0 API (the rule for this is not known, see is_stale_task_v0() in common.py)

- a GET of a PUT-only URL is 405 (Method Not Allowed), except for a zone's heatSetpoint,
  which is 404 (Not Found), as is any other invalid URL (which returns HTML, not JSON)

- responses are camelCase, but the keys of a request are case-insensitive

- a TemporaryOverride of a TCS or zone requires timeUntil, but that of a DHW untilTime

Some PUTs here change the state of an entity (e.g. put a TCS in Away mode), but each
then reverts it: to Auto (a TCS), or to FollowSchedule (a zone or DHW).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from _evohome.helpers import TCC_DTM_STRFTIME
from evohomeasync2 import ApiCallFailedError
from evohomeasync2.auth import Auth
from evohomeasync2.schemas.account import TCC_GET_USR_ACCOUNT
from evohomeasync2.schemas.config import (
    TCC_GET_DHW_CONFIG,
    TCC_GET_GWY_CONFIG,
    TCC_GET_LOC_INSTALLATION_INFO,
    TCC_GET_TCS_CONFIG,
    TCC_GET_USR_LOCATIONS,
    TCC_GET_ZON_CONFIG,
)
from evohomeasync2.schemas.schedule import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE
from evohomeasync2.schemas.status import (
    TCC_GET_DHW_STATUS,
    TCC_GET_GWY_STATUS,
    TCC_GET_LOC_STATUS,
    TCC_GET_TCS_STATUS,
    TCC_GET_ZON_STATUS,
)
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync2.schemas.account import TccUsrAccountResponseT
    from evohomeasync2.schemas.config import (
        TccDhwConfigResponseT,
        TccGwyConfigResponseT,
        TccLocConfigResponseT,
        TccTcsConfigResponseT,
        TccZonConfigResponseT,
    )
    from evohomeasync2.schemas.schedule import (
        TccDhwDailySchedulesT,
        TccZonDailySchedulesT,
    )
    from evohomeasync2.schemas.status import (
        TccDhwStatusResponseT,
        TccGwyStatusResponseT,
        TccLocStatusResponseT,
        TccTcsStatusResponseT,
        TccZonStatusResponseT,
    )


# TODO: Create a validator for the TccTaskResponseT typedDict (but until then...)
type _TccTaskResponse = dict[str, Any] | list[dict[str, Any]]  # c.f. TccTaskResponseT


def _until(hours: int = 3) -> str:
    """Return a (UTC) datetime, some hours hence, in the vendor's format."""
    return (dt.now(tz=UTC) + td(hours=hours)).strftime(TCC_DTM_STRFTIME)


#######################################################################################
# The user


async def _post_auth_oauth_token(auth: Auth) -> dict[str, int | str]:
    """Test POST /Auth/OAuth/Token

    Unlike the other endpoints, this one is off the vendor's host, not URL_BASE_V2.
    It is tested in test_v2_urls_cred.py (which is where it is documented).
    """

    raise NotImplementedError


async def get_usr_account(auth: Auth) -> TccUsrAccountResponseT:
    """Test GET /userAccount

    Returns the account of the (authenticated) user, including its userId:
      {"userId": "1234567", "username": "username@email.com", "firstname": "David", ...}
    """

    return TCC_GET_USR_ACCOUNT(
        await auth._make_request(
            HTTPMethod.GET,
            "userAccount",
        )
    )


async def get_usr_locations(auth: Auth, usr_id: str) -> list[TccLocConfigResponseT]:
    """Test GET /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True

    Returns the config of every location of the user, each as per:
      GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True

    NOTE: a location may have no gateways (so no TCS), e.g. when it is newly created.
    """

    return TCC_GET_USR_LOCATIONS(
        await auth._make_request(
            HTTPMethod.GET,
            f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True",
        )
    )


#######################################################################################
# The location, its gateway, and its TCS


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location, Gateway and TCS URLs and the corresponding validators."""

    # STEP 0: Create an Auth client stub...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 1: GET /userAccount
    usr_info = await get_usr_account(auth)

    #
    # STEP 2: GET /location/installationInfo?userId={usr_id}
    usr_locs = await get_usr_locations(auth, usr_info["userId"])

    #
    # STEP 3: GET /location/{loc_id}/installationInfo
    loc_id = next(loc for loc in usr_locs if loc["gateways"])["locationInfo"][
        "locationId"
    ]

    loc_config = await get_loc_config(auth, loc_id)

    #
    # STEP 4: GET /location/{loc_id}/status
    _ = await get_loc_status(auth, loc_id)

    #
    # STEP 5: GET /gateway/{gwy_id}/installationInfo
    gwy_id = loc_config["gateways"][0]["gatewayInfo"]["gatewayId"]

    gwy_config = await get_gwy_config(auth, gwy_id)
    assert gwy_config == loc_config["gateways"][0]  # is as nested within its location

    #
    # STEP 6: GET /gateway/{gwy_id}/status
    _ = await get_gwy_status(auth, gwy_id)

    #
    # STEP 7: without includeTemperatureControlSystems, the TCSs are omitted
    await _test_without_tcss(auth, loc_id, gwy_id)

    #
    #
    tcs_id = gwy_config["temperatureControlSystems"][0]["systemId"]

    #
    # STEP A: GET /temperatureControlSystem/{tcs_id}/installationInfo
    tcs_config = await get_tcs_config(auth, tcs_id)
    assert tcs_config == gwy_config["temperatureControlSystems"][0]  # as nested

    #
    # STEP B: GET /temperatureControlSystem/{tcs_id}/status
    _ = await get_tcs_status(auth, tcs_id)

    #
    # STEP C: PUT /temperatureControlSystem/{tcs_id}/mode
    _ = await put_tcs_mode(auth, tcs_id)
    # factory_tcs_status()(task)  # e.g. {'id': '1668279943'}


async def get_loc_config(auth: Auth, loc_id: str) -> TccLocConfigResponseT:
    """Test GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True

    Returns the config of the location, including that of its gateways and their TCSs:
      {
        "locationInfo": {"locationId": "2738909", "name": "My Home", ...},
        "gateways": [
          {
            "gatewayInfo": {"gatewayId": "2499896", "mac": "00D02DEE4E56", ...},
            "temperatureControlSystems": [{"systemId": "3432522", ...}]
          }
        ]
      }

    Each gateway (and each TCS) is as per its own installationInfo endpoint. Without
    the param, the vendor omits temperatureControlSystems from each gateway.
    """

    return TCC_GET_LOC_INSTALLATION_INFO(
        await auth._make_request(
            HTTPMethod.GET,
            f"location/{loc_id}/installationInfo?includeTemperatureControlSystems=True",
        )
    )


async def get_loc_status(auth: Auth, loc_id: str) -> TccLocStatusResponseT:
    """Test GET /location/{loc_id}/status?includeTemperatureControlSystems=True

    Returns the status of the location, including that of its gateways and their TCSs:
      {
        "locationId": "2738909",
        "gateways": [
          {
            "gatewayId": "2499896",
            "activeFaults": [],
            "temperatureControlSystems": [{"systemId": "3432522", ...}]
          }
        ]
      }

    Each gateway (and each TCS) is as per its own status endpoint. Without the param,
    the vendor omits temperatureControlSystems from each gateway.
    """

    return TCC_GET_LOC_STATUS(
        await auth._make_request(
            HTTPMethod.GET,
            f"location/{loc_id}/status?includeTemperatureControlSystems=True",
        )
    )


async def get_gwy_config(auth: Auth, gwy_id: str) -> TccGwyConfigResponseT:
    """Test GET /gateway/{gwy_id}/installationInfo?includeTemperatureControlSystems=True

    Returns the config of the gateway, including that of its TCSs:
      {
        "gatewayInfo": {
          "gatewayId": "2499896", "mac": "00D02DEE4E56", "crc": "17C2", "isWiFi": false
        },
        "temperatureControlSystems": [{"systemId": "3432522", ...}]
      }

    This is the same object as is nested within its location's installationInfo.
    Without the param, the vendor omits temperatureControlSystems.
    """

    return TCC_GET_GWY_CONFIG(
        await auth._make_request(
            HTTPMethod.GET,
            f"gateway/{gwy_id}/installationInfo?includeTemperatureControlSystems=True",
        )
    )


async def get_gwy_status(auth: Auth, gwy_id: str) -> TccGwyStatusResponseT:
    """Test GET /gateway/{gwy_id}/status?includeTemperatureControlSystems=True

    Returns the status of the gateway (i.e. its faults), including that of its TCSs:
      {
        "gatewayId": "2499896",
        "activeFaults": [
          {"faultType": "GatewayCommunicationLost", "since": "2025-02-23T22:34:25.04"}
        ],
        "temperatureControlSystems": [{"systemId": "3432522", ...}]
      }

    This is the same object as is nested within its location's status. Without the
    param, the vendor omits temperatureControlSystems.
    """

    return TCC_GET_GWY_STATUS(
        await auth._make_request(
            HTTPMethod.GET,
            f"gateway/{gwy_id}/status?includeTemperatureControlSystems=True",
        )
    )


async def _test_without_tcss(auth: Auth, loc_id: str, gwy_id: str) -> None:
    """Test that, without includeTemperatureControlSystems, the TCSs are omitted.

    This is so for both the installationInfo and status endpoints, of both locations
    and gateways (so their TCC_GET_* validators require the param to be set).
    """

    rsp = await auth._make_request(
        HTTPMethod.GET, f"location/{loc_id}/installationInfo"
    )
    assert isinstance(rsp, dict), rsp
    assert "temperatureControlSystems" not in rsp["gateways"][0], rsp

    rsp = await auth._make_request(HTTPMethod.GET, f"location/{loc_id}/status")
    assert isinstance(rsp, dict), rsp
    assert "temperatureControlSystems" not in rsp["gateways"][0], rsp

    rsp = await auth._make_request(HTTPMethod.GET, f"gateway/{gwy_id}/installationInfo")
    assert isinstance(rsp, dict), rsp
    assert list(rsp) == ["gatewayInfo"], rsp

    rsp = await auth._make_request(HTTPMethod.GET, f"gateway/{gwy_id}/status")
    assert isinstance(rsp, dict), rsp
    assert sorted(rsp) == ["activeFaults", "gatewayId"], rsp


async def get_tcs_config(auth: Auth, tcs_id: str) -> TccTcsConfigResponseT:
    """Test GET /temperatureControlSystem/{tcs_id}/installationInfo

    Returns the config of the TCS, including that of its zones (and DHW, if any):
      {
        "systemId": "3432522",
        "modelType": "EvoTouch",
        "zones": [{"zoneId": "3432521", ...}],
        "dhw": {"dhwId": "3933910", ...},  # only if the TCS has a DHW
        "allowedSystemModes": [{"systemMode": "Auto", "canBePermanent": true, ...}]
      }

    This is the same object as is nested within its gateway's installationInfo. There
    is no includeTemperatureControlSystems param (the zones/DHW are always included).
    """

    return TCC_GET_TCS_CONFIG(
        await auth._make_request(
            HTTPMethod.GET,
            f"temperatureControlSystem/{tcs_id}/installationInfo",
        )
    )


async def get_tcs_status(auth: Auth, tcs_id: str) -> TccTcsStatusResponseT:
    """Test GET /temperatureControlSystem/{tcs_id}/status

    Returns the status of the TCS, including that of its zones (and DHW, if any):
      {
        "systemId": "3432522",
        "zones": [{"zoneId": "3432521", ...}],
        "dhw": {"dhwId": "3933910", ...},  # only if the TCS has a DHW
        "activeFaults": [],
        "systemModeStatus": {"mode": "Auto", "isPermanent": true}
      }

    This is the same object as is nested within its gateway's status.
    """

    return TCC_GET_TCS_STATUS(
        await auth._make_request(
            HTTPMethod.GET,
            f"temperatureControlSystem/{tcs_id}/status",
        )
    )


async def put_tcs_mode(auth: Auth, tcs_id: str) -> _TccTaskResponse:
    """Test PUT /temperatureControlSystem/{tcs_id}/mode

    Sets the mode of the TCS, either permanently, or until a given time:
      {"systemMode": "Auto", "permanent": true}
      {"systemMode": "Away", "permanent": false, "timeUntil": "2024-01-01T00:00:00Z"}

    Returns a comm task, e.g. {"id": "1668279943"}. The allowed modes (and which may be
    temporary) are as per the TCS's allowedSystemModes.

    Errors (all 400, Bad Request), for more see test_v2_urls_auth.py:
      SystemModeChangeTimeUntilNotSet:  temporary, but no timeUntil (e.g. untilTime)
    """

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={
            "systemMode": "Away",
            "permanent": False,
            "timeUntil": _until(),
        },
    )

    # for TCSs/zones, TemporaryOverride requires timeUntil (but DHW uses untilTime)
    with pytest.raises(ApiCallFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"temperatureControlSystem/{tcs_id}/mode",
            json={
                "systemMode": "Away",
                "permanent": False,
                "untilTime": _until(),
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "SystemModeChangeTimeUntilNotSet" in exc_info.value.message

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={"systemMode": "Auto", "permanent": True},
    )


#######################################################################################
# A zone


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_zon_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Zone URLs"""

    #
    # STEP 0: Create the Auth client, get the TCS config...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info = await get_usr_account(auth)
    usr_locs = await get_usr_locations(auth, usr_info["userId"])

    #
    #
    loc_config = next(loc for loc in usr_locs if loc["gateways"])
    tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
    zon_id = tcs_config["zones"][0]["zoneId"]

    #
    # STEP A: GET /temperatureZone/{zon_id}/installationInfo
    zon_config = await get_zon_config(auth, zon_id)
    assert zon_config == tcs_config["zones"][0]  # is as nested within its TCS

    #
    # STEP B: GET /temperatureZone/{zon_id}/status
    _ = await get_zon_status(auth, zon_id)

    #
    # STEP C: PUT /temperatureZone/{zon_id}/heatSetpoint
    _ = await put_zon_heat_setpoint(auth, zon_id)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}

    #
    # STEP D: GET /temperatureZone/{zon_id}/schedule
    zon_schedule = await get_zon_schedule(auth, zon_id)

    #
    # STEP E: PUT /temperatureZone/{zon_id}/schedule
    _ = await put_zon_schedule(auth, zon_id, zon_schedule)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}


async def get_zon_config(auth: Auth, zon_id: str) -> TccZonConfigResponseT:
    """Test GET /temperatureZone/{zon_id}/installationInfo

    Returns the config of the zone:
      {
        "zoneId": "3432521",
        "modelType": "HeatingZone",
        "setpointCapabilities": {"maxHeatSetpoint": 35.0, "minHeatSetpoint": 5.0, ...},
        "scheduleCapabilities": {"maxSwitchpointsPerDay": 6, ...},
        "name": "Living room",
        "zoneType": "RadiatorZone"
      }

    This is the same object as is nested within its TCS's installationInfo.
    """

    return TCC_GET_ZON_CONFIG(
        await auth._make_request(
            HTTPMethod.GET,
            f"temperatureZone/{zon_id}/installationInfo",
        )
    )


async def get_zon_status(auth: Auth, zon_id: str) -> TccZonStatusResponseT:
    """Test GET /temperatureZone/{zon_id}/status

    Returns the status of the zone:
      {
        "zoneId": "3432521",
        "temperatureStatus": {"temperature": 21.5, "isAvailable": true},
        "activeFaults": [],
        "setpointStatus": {"targetHeatTemperature": 21.0, "setpointMode": "FollowSchedule"},
        "name": "Living room"
      }

    This is the same object as is nested within its TCS's status.
    """

    return TCC_GET_ZON_STATUS(
        await auth._make_request(
            HTTPMethod.GET,
            f"temperatureZone/{zon_id}/status",
        )
    )


async def put_zon_heat_setpoint(auth: Auth, zon_id: str) -> _TccTaskResponse:
    """Test PUT /temperatureZone/{zon_id}/heatSetpoint

    Sets the setpoint of the zone, either permanently, or until a given time, or has it
    follow its schedule:
      {"setpointMode": "PermanentOverride", "heatSetpointValue": 20.5}
      {"setpointMode": "TemporaryOverride", "heatSetpointValue": 20.5,
                                                    "timeUntil": "2024-01-01T00:00:00Z"}
      {"setpointMode": "FollowSchedule"}

    Returns a comm task, e.g. {"id": "1668279943"}. The keys are case-insensitive (so,
    for example, HeatSetpointValue is equivalent to heatSetpointValue).

    Errors (all 400, Bad Request), for more see test_v2_urls_auth.py:
      HeatSetpointChangeTimeUntilNotSet:          temporary, but no timeUntil
      HeatSetpointChangeTargetTemperatureNotSet:  an override, but no heatSetpointValue
    """

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={
            "setpointMode": "TemporaryOverride",
            "heatSetpointValue": 20.5,
            "timeUntil": _until(),
        },
    )

    # for TCSs/zones, TemporaryOverride requires timeUntil (but DHW uses untilTime)
    with pytest.raises(ApiCallFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"temperatureZone/{zon_id}/heatSetpoint",
            json={
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 20.5,
                "untilTime": _until(),
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "HeatSetpointChangeTimeUntilNotSet" in exc_info.value.message

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={
            "setpointMode": "PermanentOverride",
            "HeatSetpointValue": 20.5,  # NOTE: PascalCase, as the keys are case-insensitive
        },
    )

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={"setpointMode": "FollowSchedule"},  # no heatSetpointValue is needed
    )


async def get_zon_schedule(auth: Auth, zon_id: str) -> TccZonDailySchedulesT:
    """Test GET /temperatureZone/{zon_id}/schedule

    Returns the (weekly) schedule of the zone, one entry per day of the week:
      {
        "dailySchedules": [
          {
            "dayOfWeek": "Monday",
            "switchpoints": [{"heatSetpoint": 19.0, "timeOfDay": "06:30:00"}, ...]
          },
          ...
        ]
      }

    See test_v2_urls_sked.py for more about schedules.
    """

    return TCC_GET_ZON_SCHEDULE(
        await auth._make_request(
            HTTPMethod.GET,
            f"temperatureZone/{zon_id}/schedule",
        )
    )


async def put_zon_schedule(
    auth: Auth, zon_id: str, schedule: TccZonDailySchedulesT
) -> _TccTaskResponse:
    """Test PUT /temperatureZone/{zon_id}/schedule

    Sets the (weekly) schedule of the zone, in the same form as it is returned by:
      GET /temperatureZone/{zon_id}/schedule

    Returns a comm task, e.g. {"id": "1668279943"}. Here, the schedule is set to what it
    already is (so is a no-op). See test_v2_urls_sked.py for more about schedules.
    """

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/schedule",
        json=schedule,
    )


#######################################################################################
# A DHW


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_dhw_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test DHW URLs"""

    #
    # STEP 0: Create the Auth client, get the TCS config...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info = await get_usr_account(auth)
    usr_locs = await get_usr_locations(auth, usr_info["userId"])

    #
    #
    for loc_config in usr_locs:
        try:
            tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
            if "dhw" in tcs_config:
                break
        except (KeyError, IndexError):
            continue
    else:
        pytest.skip("No DHW found")

    dhw_id = tcs_config["dhw"]["dhwId"]

    #
    # STEP A: GET /domesticHotWater/{dhw_id}/installationInfo
    dhw_config = await get_dhw_config(auth, dhw_id)
    assert dhw_config == tcs_config["dhw"]  # is as nested within its TCS

    #
    # STEP B: GET /domesticHotWater/{dhw_id}/status
    _ = await get_dhw_status(auth, dhw_id)

    #
    # STEP C: PUT /domesticHotWater/{dhw_id}/state
    _ = await put_dhw_state(auth, dhw_id)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}

    #
    # STEP D: GET /domesticHotWater/{dhw_id}/schedule
    dhw_schedule = await get_dhw_schedule(auth, dhw_id)

    #
    # STEP E: PUT /domesticHotWater/{dhw_id}/schedule
    _ = await put_dhw_schedule(auth, dhw_id, dhw_schedule)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}


async def get_dhw_config(auth: Auth, dhw_id: str) -> TccDhwConfigResponseT:
    """Test GET /domesticHotWater/{dhw_id}/installationInfo

    Returns the config of the DHW:
      {
        "dhwId": "3933910",
        "dhwStateCapabilitiesResponse": {
          "allowedStates": ["On", "Off"],
          "allowedModes": ["FollowSchedule", "PermanentOverride", "TemporaryOverride"],
          "maxDuration": "1.00:00:00",
          "timingResolution": "00:10:00"
        },
        "scheduleCapabilitiesResponse": {"maxSwitchpointsPerDay": 6, ...}
      }

    This is the same object as is nested within its TCS's installationInfo.
    """

    return TCC_GET_DHW_CONFIG(
        await auth._make_request(
            HTTPMethod.GET,
            f"domesticHotWater/{dhw_id}/installationInfo",
        )
    )


async def get_dhw_status(auth: Auth, dhw_id: str) -> TccDhwStatusResponseT:
    """Test GET /domesticHotWater/{dhw_id}/status

    Returns the status of the DHW:
      {
        "dhwId": "3933910",
        "temperatureStatus": {"temperature": 55.0, "isAvailable": true},
        "stateStatus": {"state": "Off", "mode": "FollowSchedule"},
        "activeFaults": []
      }

    This is the same object as is nested within its TCS's status.
    """

    return TCC_GET_DHW_STATUS(
        await auth._make_request(
            HTTPMethod.GET,
            f"domesticHotWater/{dhw_id}/status",
        )
    )


async def put_dhw_state(auth: Auth, dhw_id: str) -> _TccTaskResponse:
    """Test PUT /domesticHotWater/{dhw_id}/state

    Sets the state of the DHW, either permanently, or until a given time, or has it
    follow its schedule:
      {"mode": "PermanentOverride", "state": "Off"}
      {"mode": "TemporaryOverride", "state": "On", "untilTime": "2024-01-01T00:00:00Z"}
      {"mode": "FollowSchedule"}

    Returns a comm task, e.g. {"id": "1668279943"}. The allowed modes and states are as
    per the DHW's dhwStateCapabilitiesResponse.

    Errors (all 400, Bad Request), for more see test_v2_urls_auth.py:
      DHWStateNotSet:      an override, but no state
      DHWUntilTimeNotSet:  temporary, but no untilTime (e.g. timeUntil)
    """

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={
            "mode": "TemporaryOverride",
            "state": "On",
            "untilTime": _until(),
        },
    )

    # for DHW, TemporaryOverride requires untilTime (but zones use timeUntil)
    with pytest.raises(ApiCallFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"domesticHotWater/{dhw_id}/state",
            json={
                "mode": "TemporaryOverride",
                "state": "On",
                "timeUntil": _until(),
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "DHWUntilTimeNotSet" in exc_info.value.message

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "PermanentOverride", "state": "Off"},
    )

    return await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "FollowSchedule"},  # no state is needed
    )


async def get_dhw_schedule(auth: Auth, dhw_id: str) -> TccDhwDailySchedulesT:
    """Test GET /domesticHotWater/{dhw_id}/schedule

    Returns the (weekly) schedule of the DHW, one entry per day of the week:
      {
        "dailySchedules": [
          {
            "dayOfWeek": "Monday",
            "switchpoints": [{"dhwState": "On", "timeOfDay": "06:30:00"}, ...]
          },
          ...
        ]
      }

    See test_v2_urls_sked.py for more about schedules.
    """

    return TCC_GET_DHW_SCHEDULE(
        await auth._make_request(
            HTTPMethod.GET,
            f"domesticHotWater/{dhw_id}/schedule",
        )
    )


async def put_dhw_schedule(
    auth: Auth, dhw_id: str, schedule: TccDhwDailySchedulesT
) -> _TccTaskResponse:
    """Test PUT /domesticHotWater/{dhw_id}/schedule

    Sets the (weekly) schedule of the DHW, in the same form as it is returned by:
      GET /domesticHotWater/{dhw_id}/schedule

    Returns a comm task, e.g. {"id": "1668279943"}. Here, the schedule is set to what it
    already is (so is a no-op). See test_v2_urls_sked.py for more about schedules.
    """

    return await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/schedule",
        json=schedule,
    )
