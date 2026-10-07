"""Validate the handling of the v2 APIs (URLs): their errors and edge cases.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server (if any) is behaving as per a)

Where test_v2_urls.py documents each endpoint (and has a list of them all), this module
documents how they fail: e.g. an unauthorized user or wrong method, an invalid URL, and
a PUT with missing or invalid params (with each error code the vendor returns).

URLs that are not used by the client (e.g. the status of a TCS, zone or DHW, as it is
included in that of its location) are tested only if _DBG_TEST_UNUSED_APIS.

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used), although
the keys of a request are case-insensitive (as confirmed here).
"""

from __future__ import annotations

from datetime import timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from _evohome.helpers import pascal_to_snake
from evohomeasync2.schemas.account import TCC_GET_USR_ACCOUNT
from evohomeasync2.schemas.config import TCC_GET_USR_LOCATIONS
from evohomeasync2.schemas.const import (
    TCC_DTM_STRFTIME,
    TccDhwState,
    TccSystemMode,
    TccZoneMode,
)
from evohomeasync2.schemas.status import (
    TCC_GET_DHW_STATUS,
    TCC_GET_LOC_STATUS,
    TCC_GET_TCS_STATUS,
    TCC_GET_ZON_STATUS,
)
from tests.const import _DBG_TEST_UNUSED_APIS, _DBG_USE_REAL_AIOHTTP

from .common import (
    error_codes,
    get_dhw,
    get_loc,
    should_fail_v2,
    should_work_v2,
    skipif_auth_failed,
)

if TYPE_CHECKING:
    import evohomeasync2 as evo2
    from evohomeasync2 import EvohomeClient as EvohomeClientV2
    from evohomeasync2.schemas.state import TccSetTcsModeT
    from evohomeasync2.schemas.status import TccTcsStatusResponseT


#######################################################################################


async def _test_usr_account(evo: EvohomeClientV2) -> None:
    """Test /userAccount"""

    # STEP 1:
    url = "userAccount"
    _ = await should_work_v2(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_ACCOUNT)
    # {
    #     'userId': '2263181',
    #     'username': 'nobody@nowhere.com',
    # ...
    #     'country': 'UnitedKingdom',
    #     'language': 'enGB'
    # }

    # STEP 2:
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    # {'message': "The requested resource does not support http method 'PUT'."}

    # STEP 3:
    url = "userXxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )
    # '<!DOCTYPE html PUBLIC ...


async def _test_user_locations(evo: EvohomeClientV2) -> None:
    """Test /location/installationInfo?userId={user_id}"""

    # TODO: can't use .update(); in any case, should use URLs only
    url = "userAccount"
    user_info = await should_work_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not re-tested here
    )
    assert isinstance(user_info, dict)  # mypy

    #
    url = f"location/installationInfo?userId={user_info['userId']}"
    if _DBG_TEST_UNUSED_APIS:  # without the param (not used by the client)
        _ = await should_work_v2(
            evo.auth,
            HTTPMethod.GET,
            url,
            schema=None,  # schema not tested here
        )

    # url = f"location/{loc_id}/installationInfo"  # no TCS info
    # _ = await should_work_v2(
    #     evo.auth,
    #     HTTPMethod.GET,
    #     url,
    #     schema=None,  # schema not tested here
    # )

    #
    url += "&includeTemperatureControlSystems=True"
    _ = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_LOCATIONS
    )

    #
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    #
    url = "location/installationInfo"
    _ = await should_fail_v2(evo.auth, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)

    #
    url = "location/installationInfo?userId=1230000"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED
    )

    #
    url = "location/installationInfo?userId=xxxxxxx"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST
    )

    #
    url = "location/installationInfo?xxxxXx=xxxxxxx"
    _ = await should_fail_v2(evo.auth, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)


async def _test_loc_status(evo: EvohomeClientV2) -> None:
    """Test /location/{loc.id}/status"""

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    loc = get_loc(evo)
    #

    url = f"location/{loc.id}/status"
    if _DBG_TEST_UNUSED_APIS:  # without the param (not used by the client)
        _ = await should_work_v2(
            evo.auth,
            HTTPMethod.GET,
            url,
            schema=None,  # schema not tested here
        )

    url += "?includeTemperatureControlSystems=True"
    _ = await should_work_v2(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_LOC_STATUS)
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = f"location/{loc.id}"
    await should_fail_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    url = "location/1230000/status"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED
    )

    url = "location/xxxxxxx/status"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST
    )

    url = f"location/{loc.id}/xxxxxxx"
    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_tcs_status(evo: EvohomeClientV2) -> None:
    """Test GET /temperatureControlSystem/{tcs.id}/status

    Also tests PUT /temperatureControlSystem/{tcs.id}/mode
    """

    # TODO: remove .update() and use URLs only?
    await evo.update(dont_update_status=True)

    tcs: evo2.ControlSystem
    if not (tcs := get_loc(evo).gateways[0].systems[0]):
        pytest.skip("No available TCS found")

    #
    # STEP 0: Get/keep the current mode, so we can restore it later
    old_status: TccTcsStatusResponseT

    if _DBG_TEST_UNUSED_APIS:  # GET the TCS's status (not used by the client)
        url = f"{tcs._TCC_TYPE}/{tcs.id}/status"
        old_status = await should_work_v2(
            evo.auth, HTTPMethod.GET, url, schema=TCC_GET_TCS_STATUS
        )

    else:  # GET it from its location's status, as does the client
        url = f"location/{tcs.location.id}/status?includeTemperatureControlSystems=True"
        loc_status = await should_work_v2(
            evo.auth, HTTPMethod.GET, url, schema=TCC_GET_LOC_STATUS
        )
        old_status = next(
            t
            for g in loc_status["gateways"]
            for t in g["temperatureControlSystems"]
            if t["systemId"] == tcs.id
        )
    # {
    #      'systemId': '1234567',
    #      'zones': [...]
    #      'systemModeStatus': {...}
    #      'activeFaults': [],
    # }

    old_mode: TccSetTcsModeT = {
        "systemMode": old_status["systemModeStatus"]["mode"],
        "permanent": old_status["systemModeStatus"]["isPermanent"],
    }
    if "timeUntil" in old_status["systemModeStatus"]:
        old_mode["timeUntil"] = old_status["systemModeStatus"]["timeUntil"]

    #
    # STEP 1: Change the mode, but with the wrong method
    url = f"{tcs._TCC_TYPE}/{tcs.id}/mode"

    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    # {'message': "The requested resource does not support http method 'GET'."}

    #
    # STEP 2: Change the mode, but with missing request data (JSON)
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json={}, status=HTTPStatus.BAD_REQUEST
    )
    # [  # NOTE: keys are (case-insensitive) PascalCase, not camelCase!!
    #     {'code': 'ParameterIsMissing', 'parameterName': 'TccSystemMode', 'message': 'Parameter is missing.'},
    #     {'code': 'ParameterIsMissing', 'parameterName': 'Permanent',  'message': 'Parameter is missing.'}
    # ]

    #
    # STEP 3: Change the mode, but with invalid request data (JSON)
    new_mode = {"systemMode": "xxxxx", "permanent": True}

    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=new_mode, status=HTTPStatus.BAD_REQUEST
    )
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxx" to...'}]

    #
    # STEP 4: Change the mode, but with semi-invalid request data (JSON)
    assert pascal_to_snake(TccSystemMode.COOL) not in tcs.allowed_modes
    new_mode = {"systemMode": "Cool", "permanent": True}

    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json=new_mode,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    # {'message': 'An error has occurred.'}

    #
    # STEP 4: Change the mode, with valid request data (JSON) (permanent)
    assert pascal_to_snake(TccSystemMode.AUTO) in tcs.allowed_modes
    new_mode = {"systemMode": TccSystemMode.AUTO, "permanent": True}

    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588314363'}

    #
    # STEP 4: Change the mode, with valid request data (JSON) (temporary)
    assert pascal_to_snake(TccSystemMode.AWAY) in tcs.allowed_modes
    new_mode = {
        "systemMode": TccSystemMode.AWAY,
        "permanent": False,
        "timeUntil": (tcs.location.now() + td(hours=1)).strftime(TCC_DTM_STRFTIME),
    }

    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588315695'}

    #
    # STEP 5: Restore the original mode
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=old_mode)
    # {'id': '1588316616'}

    #
    # STEP 6: Change the mode, but without permission
    url = f"{tcs._TCC_TYPE}/1234567/mode"

    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )
    # [{
    #     'code': 'Unauthorized',
    #     'message': 'You are not allowed to perform this action.'
    # }]

    #
    # STEP 7: hange the mode, but with invalid URL
    url = f"{tcs._TCC_TYPE}/{tcs.id}/systemMode"
    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json=old_mode,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )
    # '<!DOCTYPE html PUBLIC ...


async def _test_zone_status(evo: EvohomeClientV2) -> None:
    """Test /temperatureZone/{zone.id}/status

    Also tests /temperatureZone/{zone.id}/heatSetpoint
    """

    heat_setpoint: dict[str, float | str | None]  # TODO: TypedDict

    # TODO: remove .update() and use URLs only
    await evo.update()

    if not (zone := get_loc(evo).gateways[0].systems[0].zones[0]):
        pytest.skip("No available zones found")

    #
    url = f"{zone._TCC_TYPE}/{zone.id}/status"
    if _DBG_TEST_UNUSED_APIS:  # GET the zone's status (not used by the client)
        _ = await should_work_v2(
            evo.auth, HTTPMethod.GET, url, schema=TCC_GET_ZON_STATUS
        )
    # {
    #     'zoneId': '3432576',
    #     'temperatureStatus': {'temperature': 25.5, 'isAvailable': True},
    #     'activeFaults': [],
    #     'setpointStatus': {'targetHeatTemperature': 18.5, 'setpointMode': 'FollowSchedule'},
    #     'name': 'Main Room'
    # }

    #
    url = f"{zone._TCC_TYPE}/{zone.id}/heatSetpoint"

    # NOTE: unlike /mode (a TCS) and /state (a DHW), which are 405 for a GET, this is
    # a 404, as if the URL does not exist (so there is no way to GET the setpoint alone)
    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )
    # '<!DOCTYPE html PUBLIC ...

    heat_setpoint = {
        "setpointMode": TccZoneMode.PERMANENT_OVERRIDE,
    }
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )
    # [{
    #     'code': 'HeatSetpointChangeTargetTemperatureNotSet',
    #     'message': 'Target temperature not specified when required'
    # }]

    heat_setpoint = {
        "setpointMode": TccZoneMode.PERMANENT_OVERRIDE,
        "HeatSetpointValue": 19.5 if zone.temperature is None else zone.temperature,
        # "timeUntil": None,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": TccZoneMode.PERMANENT_OVERRIDE,
        "HeatSetpointValue": 99,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": TccZoneMode.TEMPORARY_OVERRIDE,
        "HeatSetpointValue": 19.5,
    }
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
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
        evo.auth, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxxxx" to ..."}]

    #
    heat_setpoint = {
        "setpointMode": TccZoneMode.FOLLOW_SCHEDULE,
        "HeatSetpointValue": 0.0,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588365922'}


async def _test_dhw_status(evo: EvohomeClientV2) -> None:
    """Test /domesticHotWater/{dhw.id}/status

    Also tests /domesticHotWater/{dhw.id}/state
    """

    # not a TccSetDhwModeT, as some of these bodies are deliberately invalid
    dhw_state: dict[str, str | None]

    # TODO: remove .update() and use URLs only
    await evo.update()

    if not (dhw := get_dhw(evo)):
        pytest.skip("No available DHW found")

    #
    # STEP 1: Get the status (which is GET-only) (not used by the client)
    url = f"{dhw._TCC_TYPE}/{dhw.id}/status"

    if _DBG_TEST_UNUSED_APIS:
        _ = await should_work_v2(
            evo.auth, HTTPMethod.GET, url, schema=TCC_GET_DHW_STATUS
        )
    # {
    #     'dhwId': '3933910',
    #     'temperatureStatus': {'temperature': 55.0, 'isAvailable': True},
    #     'stateStatus': {'state': 'Off', 'mode': 'FollowSchedule'},
    #     'activeFaults': []
    # }

    if _DBG_TEST_UNUSED_APIS:
        _ = await should_fail_v2(
            evo.auth,
            HTTPMethod.PUT,
            url,
            json={"mode": TccZoneMode.FOLLOW_SCHEDULE},
            status=HTTPStatus.METHOD_NOT_ALLOWED,
        )
    # {'message': "The requested resource does not support http method 'PUT'."}

    #
    # STEP 2: Change the state, but with the wrong method (it is PUT-only)
    url = f"{dhw._TCC_TYPE}/{dhw.id}/state"

    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    # {'message': "The requested resource does not support http method 'GET'."}

    #
    # STEP 3: Change the state, but with missing/invalid request data (JSON)
    dhw_state = {}
    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["ParameterIsMissing"], rsp
    # [{
    #     'code': 'ParameterIsMissing',
    #     'parameterName': 'Mode',
    #     'message': 'Parameter is missing.'
    # }]

    dhw_state = {"mode": "xxxxx", "state": TccDhwState.ON}
    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["InvalidInput"], rsp
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxx" to ...'}]

    dhw_state = {"mode": TccZoneMode.PERMANENT_OVERRIDE, "state": "xxxxx"}
    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["InvalidInput"], rsp
    # [{'code': 'InvalidInput', 'message': 'Error converting value "xxxxx" to ...'}]

    #
    # STEP 4: Change the state, but without data that the mode requires
    dhw_state = {"mode": TccZoneMode.PERMANENT_OVERRIDE}  # an override needs a state
    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["DHWStateNotSet"], rsp
    # [{
    #     'code': 'DHWStateNotSet',
    #     'message': 'Domestic hot water state is not set when required'
    # }]

    dhw_state = {"mode": TccZoneMode.TEMPORARY_OVERRIDE, "state": TccDhwState.ON}
    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.BAD_REQUEST
    )
    assert error_codes(rsp) == ["DHWUntilTimeNotSet"], rsp
    # [{
    #     'code': 'DHWUntilTimeNotSet',
    #     'message': 'Domestic hot water until time is not set when required'
    # }]

    #
    # STEP 5: Change the state, with valid request data (JSON)
    dhw_state = {  # NOTE: the keys are case-insensitive
        "Mode": TccZoneMode.PERMANENT_OVERRIDE,
        "State": TccDhwState.OFF,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=dhw_state)
    # {'id': '1278834041'}

    #
    # STEP 6: Restore the state (so it follows its schedule)
    dhw_state = {"mode": TccZoneMode.FOLLOW_SCHEDULE}  # no state is needed
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=dhw_state)
    # {'id': '1278834119'}

    #
    # STEP 7: Change the state, but without permission
    url = f"{dhw._TCC_TYPE}/1234567/state"

    rsp = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=dhw_state, status=HTTPStatus.UNAUTHORIZED
    )
    assert error_codes(rsp) == ["Unauthorized"], rsp
    # [{
    #     'code': 'Unauthorized',
    #     'message': 'You are not allowed to perform this action.'
    # }]

    #
    # STEP 8: Change the state, but with an invalid URL (/mode is for a TCS)
    url = f"{dhw._TCC_TYPE}/{dhw.id}/mode"

    _ = await should_fail_v2(
        evo.auth,
        HTTPMethod.PUT,
        url,
        json=dhw_state,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )
    # '<!DOCTYPE html PUBLIC ...


#######################################################################################


@skipif_auth_failed  # GET
async def test_usr_account(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /userAccount"""

    await _test_usr_account(evohome_v2)


@skipif_auth_failed  # GET
async def test_usr_locations(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /location/installationInfo"""

    await _test_user_locations(evohome_v2)


@skipif_auth_failed  # GET
async def test_loc_status(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /location/{loc.id}/status"""

    await _test_loc_status(evohome_v2)


@skipif_auth_failed  # GET, PUT
async def test_tcs_status(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /temperatureControlSystem/{tcs.id}/status

    Also tests PUT /temperatureControlSystem/{tcs.id}/mode
    """

    try:
        await _test_tcs_status(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed  # GET, PUT
async def test_zone_status(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /temperatureZone/{zone.id}/status

    Also tests PUT /temperatureZone/{zone.id}/heatSetpoint
    """

    try:
        await _test_zone_status(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed  # GET, PUT
async def test_dhw_status(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /domesticHotWater/{dhw.id}/status

    Also tests PUT /domesticHotWater/{dhw.id}/state
    """

    try:
        await _test_dhw_status(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")
