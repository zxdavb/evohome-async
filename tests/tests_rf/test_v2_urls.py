#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs) for Authorization.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohomeasync2 import schema
from evohomeasync2.const import API_STRFTIME, SystemMode, ZoneMode

from .common import should_fail_v2, should_work_v2, skipif_auth_failed
from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    from evohomeasync2.schema import _EvoDictT

    from ..conftest import EvohomeClientv2


#######################################################################################


async def _test_usr_account(evo: EvohomeClientv2) -> None:
    """Test /userAccount"""

    url = "userAccount"
    _ = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_USER_ACCOUNT
    )
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "userXxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    _ = await should_fail_v2(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_user_locations(evo: EvohomeClientv2) -> None:
    """Test /location/installationInfo?userId={user_id}"""

    # TODO: can't use .update(); in any case, should use URLs only
    url = "userAccount"
    user_info = await should_work_v2(
        evo,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not re-tested here
    )
    #

    url = f"location/installationInfo?userId={user_info["userId"]}"
    await should_work_v2(
        evo,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not tested here
    )

    url += "&includeTemperatureControlSystems=True"
    _ = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_USER_LOCATIONS
    )
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "location/installationInfo"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)

    url = "location/installationInfo?userId=1230000"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/installationInfo?userId=xxxxxxx"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)


async def _test_loc_status(evo: EvohomeClientv2) -> None:
    """Test /location/{loc.id}/status"""

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    loc = evo.locations[0]
    #

    url = f"location/{loc.id}/status"
    _ = await should_work_v2(
        evo,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not tested here
    )

    url += "?includeTemperatureControlSystems=True"
    _ = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_LOCN_STATUS
    )
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = f"location/{loc.id}"
    await should_fail_v2(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    url = "location/1230000/status"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/xxxxxxx/status"
    _ = await should_fail_v2(evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = f"location/{loc.id}/xxxxxxx"
    _ = await should_fail_v2(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_tcs_status(evo: EvohomeClientv2) -> None:
    """Test /temperatureControlSystem/{tcs.id}/statis

    Also tests /temperatureControlSystem/{tcs.id}/mode
    """

    # TODO: remove .update() and use URLs only?
    await evo.update(dont_update_status=True)

    tcs: evo2.ControlSystem

    if not (tcs := evo.locations[0].gateways[0].control_systems[0]):
        pytest.skip("No available zones found")

    #
    url = f"{tcs._TYPE}/{tcs.id}/status"
    old_status = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_TCS_STATUS
    )
    # {
    #      'systemId': '1234567',
    #      'zones': [...]
    #      'systemModeStatus': {...}
    #      'activeFaults': [],
    # }

    old_mode = {
        "systemMode": old_status["systemModeStatus"]["mode"],
        "permanent": old_status["systemModeStatus"]["isPermanent"],
    }
    if "timeUntil" in old_status["systemModeStatus"]:
        old_mode["timeUntil"] = old_status["systemModeStatus"]["timeUntil"]

    #
    url = f"{tcs._TYPE}/{tcs.id}/mode"
    _ = await should_fail_v2(
        evo, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    # {'message': "The requested resource does not support http method 'GET'."}

    #
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json={}, status=HTTPStatus.BAD_REQUEST
    )
    # [  # NOTE: keys are (case-insensitive) PascalCase, not camelCase!!
    #     {'code': 'ParameterIsMissing', 'parameterName': 'SystemMode', 'message': 'Parameter is missing.'},
    #     {'code': 'ParameterIsMissing', 'parameterName': 'Permanent',  'message': 'Parameter is missing.'}
    # ]

    #
    new_mode: _EvoDictT = {"systemMode": "xxxxx", "permanent": True}
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=new_mode, status=HTTPStatus.BAD_REQUEST
    )
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxx" to...'}]

    #
    assert SystemMode.COOL not in tcs.modes
    new_mode: _EvoDictT = {"systemMode": "Cool", "permanent": True}
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=new_mode, status=HTTPStatus.INTERNAL_SERVER_ERROR
    )
    # {'message': 'An error has occurred.'}

    #
    assert SystemMode.AUTO in tcs.modes
    new_mode: _EvoDictT = {"systemMode": SystemMode.AUTO, "permanent": True}
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588314363'}

    #
    assert SystemMode.AWAY in tcs.modes
    new_mode = {
        "systemMode": SystemMode.AWAY,
        "permanent": True,
        "timeUntil": (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588315695'}

    #
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=old_mode)
    # {'id': '1588316616'}

    #
    url = f"{tcs._TYPE}/1234567/mode"
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )
    # [{
    #     'code': 'Unauthorized',
    #     'message': 'You are not allowed to perform this action.'
    # }]

    #
    url = f"{tcs._TYPE}/{tcs.id}/systemMode"
    _ = await should_fail_v2(
        evo,
        HTTPMethod.PUT,
        url,
        json=old_mode,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )
    # '<!DOCTYPE html PUBLIC ...


async def _test_zone_status(evo: EvohomeClientv2) -> None:
    """Test /temperatureZone/{zone.id}/status

    Also tests /temperatureZone/{zone.id}/heatSetpoint
    """

    zone: evo2.Zone
    heat_setpoint: dict[str, float | str | None]

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    if not (zone := evo.locations[0].gateways[0].control_systems[0].zones[0]):
        pytest.skip("No available zones found")

    #
    url = f"{zone._TYPE}/{zone.id}/status"
    _ = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_ZONE_STATUS
    )
    # {
    #     'zoneId': '3432576',
    #     'temperatureStatus': {'temperature': 25.5, 'isAvailable': True},
    #     'activeFaults': [],
    #     'setpointStatus': {'targetHeatTemperature': 18.5, 'setpointMode': 'FollowSchedule'},
    #     'name': 'Main Room'
    # }

    #
    url = f"{zone._TYPE}/{zone.id}/heatSetpoint"

    heat_setpoint = {
        "setpointMode": ZoneMode.PERMANENT_OVERRIDE,
    }
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )
    # [{
    #     'code': 'HeatSetpointChangeTargetTemperatureNotSet',
    #     'message': 'Target temperature not specified when required'
    # }]

    heat_setpoint = {
        "setpointMode": ZoneMode.PERMANENT_OVERRIDE,
        "HeatSetpointValue": 19.5 if zone.temperature is None else zone.temperature,
        # "timeUntil": None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": ZoneMode.PERMANENT_OVERRIDE,
        "HeatSetpointValue": 99,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": ZoneMode.TEMPORARY_OVERRIDE,
        "HeatSetpointValue": 19.5,
    }
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )
    # [{
    #     'code': 'HeatSetpointChangeTimeUntilNotSet',
    #     'message': 'Time until not specified when required'
    # }]

    #
    heat_setpoint = {
        "setpointMode": "xxxxx",
        "HeatSetpointValue": 19.5,
    }
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxxxx" to ..."}]

    #
    heat_setpoint = {
        "setpointMode": ZoneMode.FOLLOW_SCHEDULE,
        "HeatSetpointValue": 0.0,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588365922'}


#######################################################################################


@skipif_auth_failed  # GET
async def test_usr_account(evohome_v2: EvohomeClientv2) -> None:
    """Test /userAccount"""

    try:
        await _test_usr_account(evohome_v2)

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@skipif_auth_failed  # GET
async def test_usr_locations(evohome_v2: EvohomeClientv2) -> None:
    """Test /location/installationInfo"""

    await _test_user_locations(evohome_v2)


@skipif_auth_failed  # GET
async def test_loc_status(evohome_v2: EvohomeClientv2) -> None:
    """Test /location/{loc.id}/status"""

    await _test_loc_status(evohome_v2)


@skipif_auth_failed  # GET, PUT
async def test_tcs_status(evohome_v2: EvohomeClientv2) -> None:
    """Test /temperatureControlSystem/{tcs.id}/statis

    Also tests /temperatureControlSystem/{tcs.id}/mode
    """

    try:
        await _test_tcs_status(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed  # GET, PUT
async def test_zone_status(evohome_v2: EvohomeClientv2) -> None:
    """Test /temperatureZone/{zone.id}/status

    Also tests /temperatureZone/{zone.id}/heatSetpoint
    """

    try:
        await _test_zone_status(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


# TODO: test_oauth_token(
# TODO: test_get_dhw_status( & test_put_dhw_state(
