"""evohome-async - validate the handling of vendor APIs (URLs) for Authorization.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from datetime import timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

import evohomeasync2 as evo2
from evohomeasync2 import schemas
from evohomeasync2.const import API_STRFTIME
from evohomeasync2.schemas import SystemMode, ZoneMode
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import should_fail_v2, should_work_v2, skipif_auth_failed

if TYPE_CHECKING:
    from tests.conftest import EvohomeClientv2


#######################################################################################


async def _test_usr_account(evo: EvohomeClientv2) -> None:
    """Test /userAccount"""

    # STEP 1:
    url = "userAccount"
    _ = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_USR_ACCOUNT
    )
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


async def _test_user_locations(evo: EvohomeClientv2) -> None:
    """Test /location/installationInfo?userId={user_id}"""

    # TODO: can't use .update(); in any case, should use URLs only
    url = "userAccount"
    user_info: dict[str, Any] = await should_work_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not re-tested here
    )  # type: ignore[assignment]

    #
    url = f"location/installationInfo?userId={user_info["userId"]}"
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
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_USR_LOCATIONS
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


async def _test_loc_status(evo: EvohomeClientv2) -> None:
    """Test /location/{loc.id}/status"""

    # TODO: remove .update() and use URLs only
    await evo.update(_dont_update_status=True)

    loc = evo.locations[0]
    #

    url = f"location/{loc.id}/status"
    _ = await should_work_v2(
        evo.auth,
        HTTPMethod.GET,
        url,
        schema=None,  # schema not tested here
    )

    url += "?includeTemperatureControlSystems=True"
    _ = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_LOC_STATUS
    )
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


async def _test_tcs_status(evo: EvohomeClientv2) -> None:
    """Test GET /temperatureControlSystem/{tcs.id}/status

    Also tests PUT /temperatureControlSystem/{tcs.id}/mode
    """

    # TODO: remove .update() and use URLs only?
    await evo.update(_dont_update_status=True)

    tcs: evo2.ControlSystem
    if not (tcs := evo.locations[0].gateways[0].systems[0]):
        pytest.skip("No available TCS found")

    #
    # STEP 0: Get/keep the current mode, so we can restore it later
    url = f"{tcs._TYPE}/{tcs.id}/status"

    old_status: dict[str, Any] = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_TCS_STATUS
    )  # type: ignore[assignment]
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
    # STEP 1: Change the mode, but with the wrong method
    url = f"{tcs._TYPE}/{tcs.id}/mode"

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
    #     {'code': 'ParameterIsMissing', 'parameterName': 'SystemMode', 'message': 'Parameter is missing.'},
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
    assert SystemMode.COOL not in tcs.modes
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
    assert SystemMode.AUTO in tcs.modes
    new_mode = {"systemMode": SystemMode.AUTO, "permanent": True}

    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588314363'}

    #
    # STEP 4: Change the mode, with valid request data (JSON) (temporary)
    assert SystemMode.AWAY in tcs.modes
    new_mode = {
        "systemMode": SystemMode.AWAY,
        "permanent": False,
        "timeUntil": (tcs.location.now() + td(hours=1)).strftime(API_STRFTIME),
    }

    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=new_mode)
    # {'id': '1588315695'}

    #
    # STEP 5: Restore the original mode
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=old_mode)
    # {'id': '1588316616'}

    #
    # STEP 6: Change the mode, but without permission
    url = f"{tcs._TYPE}/1234567/mode"

    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )
    # [{
    #     'code': 'Unauthorized',
    #     'message': 'You are not allowed to perform this action.'
    # }]

    #
    # STEP 7: hange the mode, but with invalid URL
    url = f"{tcs._TYPE}/{tcs.id}/systemMode"
    _ = await should_fail_v2(
        evo.auth,
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

    heat_setpoint: dict[str, float | str | None]  # TODO: TypedDict

    # TODO: remove .update() and use URLs only
    await evo.update(_dont_update_status=True)

    if not (zone := evo.locations[0].gateways[0].systems[0].zones[0]):
        pytest.skip("No available zones found")

    #
    url = f"{zone._TYPE}/{zone.id}/status"
    _ = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_ZON_STATUS
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
        evo.auth, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
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
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": ZoneMode.PERMANENT_OVERRIDE,
        "HeatSetpointValue": 99,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588359054'}

    #
    heat_setpoint = {
        "setpointMode": ZoneMode.TEMPORARY_OVERRIDE,
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
        "setpointMode": ZoneMode.FOLLOW_SCHEDULE,
        "HeatSetpointValue": 0.0,
        "timeUntil": None,
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=heat_setpoint)
    # {'id': '1588365922'}


#######################################################################################


@skipif_auth_failed  # GET
async def test_usr_account(evohome_v2: EvohomeClientv2) -> None:
    """Test /userAccount"""

    await _test_usr_account(evohome_v2)


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
