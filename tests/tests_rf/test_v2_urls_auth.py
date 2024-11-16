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
from evohomeasync2.const import (
    API_STRFTIME,
    SZ_IS_PERMANENT,
    SZ_MODE,
    SZ_PERMANENT,
    SZ_SYSTEM_MODE,
    SystemMode,
    ZoneMode,
)
from evohomeasync2.schema.const import (
    S2_DAILY_SCHEDULES,
    S2_HEAT_SETPOINT,
    S2_HEAT_SETPOINT_VALUE,
    S2_PERMANENT,
    S2_SETPOINT_MODE,
    S2_SWITCHPOINTS,
    S2_SYSTEM_MODE,
    S2_TIME_UNTIL,
    S2_USER_ID,
)

from . import faked_server as faked
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

    url = f"location/installationInfo?userId={user_info[S2_USER_ID]}"
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

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    tcs: evo2.ControlSystem

    if not (tcs := evo.locations[0].gateways[0].control_systems[0]):
        pytest.skip("No available zones found")

    # TODO: remove .update() and use URLs only
    _ = await tcs.location.update()  # NOTE: below is snake_case
    old_mode: _EvoDictT = tcs.system_mode_status  # type: ignore[assignment]

    url = f"{tcs._TYPE}/{tcs.id}/status"
    _ = await should_work_v2(evo, HTTPMethod.GET, url, schema=schema.SCH_GET_TCS_STATUS)

    url = f"{tcs._TYPE}/{tcs.id}/mode"
    _ = await should_fail_v2(
        evo, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    # FIXME: old_mode is snack_case
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.BAD_REQUEST
    )

    old_mode[SZ_SYSTEM_MODE] = old_mode.pop(SZ_MODE)
    old_mode[SZ_PERMANENT] = old_mode.pop(SZ_IS_PERMANENT)

    assert SystemMode.AUTO in [m[SZ_SYSTEM_MODE] for m in tcs.allowed_system_modes]
    new_mode: _EvoDictT = {
        S2_SYSTEM_MODE: SystemMode.AUTO,
        S2_PERMANENT: True,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=new_mode)

    assert SystemMode.AWAY in [m[SZ_SYSTEM_MODE] for m in tcs.allowed_system_modes]
    new_mode = {
        S2_SYSTEM_MODE: SystemMode.AWAY,
        S2_PERMANENT: True,
        S2_TIME_UNTIL: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=new_mode)

    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=old_mode)

    url = f"{tcs._TYPE}/1234567/mode"
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )

    url = f"{tcs._TYPE}/{tcs.id}/systemMode"
    _ = await should_fail_v2(
        evo,
        HTTPMethod.PUT,
        url,
        json=old_mode,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    pass


async def _test_zone_status(evo: EvohomeClientv2) -> None:
    """Test /temperatureZone/{zone.id}/status

    Also tests /temperatureZone/{zone.id}/heatSetpoint
    """

    # TODO: remove .update() and use URLs only
    await evo.update()

    for zone in evo.locations[0].gateways[0].control_systems[0].zones:
        if zone.temperature is None:
            break
    else:
        pytest.skip("No available zones found")
    #

    url = f"{zone._TYPE}/{zone.id}/status"
    _ = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_ZONE_STATUS
    )

    url = f"{zone._TYPE}/{zone.id}/heatSetpoint"

    heat_setpoint: dict[str, float | str | None] = {
        S2_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        S2_HEAT_SETPOINT_VALUE: zone.temperature,
        # S2_TIME_UNTIL: None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        S2_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        S2_HEAT_SETPOINT_VALUE: 99,
        S2_TIME_UNTIL: None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        S2_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        S2_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        S2_SETPOINT_MODE: "xxxxxxx",
        S2_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )

    heat_setpoint = {
        S2_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
        S2_HEAT_SETPOINT_VALUE: 0.0,
        S2_TIME_UNTIL: None,
    }
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=heat_setpoint)


# TODO: Test sending bad schedule
async def _test_schedule(evo: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{xid}/schedule

    Also test commTasks?commTaskId={task_id}
    """

    # TODO: remove .update() and use URLs only
    await evo.update()

    zone = evo.locations[0].gateways[0].control_systems[0].zones[0]
    #

    if zone.id == faked.GHOST_ZONE_ID:
        url = f"{zone._TYPE}/{faked.GHOST_ZONE_ID}/schedule"
        _ = await should_fail_v2(
            evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST
        )
        return

    #
    # STEP 0: GET the current schedule
    url = f"{zone._TYPE}/{zone.id}/schedule"
    schedule = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_SCHEDULE
    )

    #
    # STEP 1: PUT a new schedule
    temp = schedule[S2_DAILY_SCHEDULES][0][S2_SWITCHPOINTS][0][S2_HEAT_SETPOINT]  # type: ignore[call-overload]

    schedule[S2_DAILY_SCHEDULES][0][S2_SWITCHPOINTS][0][S2_HEAT_SETPOINT] = temp + 1  # type: ignore[call-overload,operator]
    result = await should_work_v2(
        evo,
        HTTPMethod.PUT,
        url,
        json=schedule,  # was convert_to_put_schedule(schedule),  # type: ignore[arg-type]
    )  # returns (e.g.) {'id': '840367013'}

    #
    # STEP 2: check the status of the task
    if _DBG_USE_REAL_AIOHTTP:
        task_id = result[0]["id"] if isinstance(result, list) else result["id"]
        url_tsk = f"commTasks?commTaskId={task_id}"

        status = await should_work_v2(evo, HTTPMethod.GET, url_tsk)
        # {'commtaskId': '840367013', 'state': 'Created'}
        # {'commtaskId': '840367013', 'state': 'Running'}
        # {'commtaskId': '840367013', 'state': 'Succeeded'}

        assert isinstance(status, dict)  # mypy
        assert status["commtaskId"] == task_id
        assert status["state"] in ("Created", "Running", "Succeeded")

    #
    # STEP 3: check the new schedule was effected
    schedule = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_SCHEDULE
    )
    assert (
        schedule[S2_DAILY_SCHEDULES][0][S2_SWITCHPOINTS][0][S2_HEAT_SETPOINT]  # type: ignore[call-overload]
        == temp + 1  # type: ignore[operator]
    )

    #
    # STEP 4: PUT the original schedule back
    schedule[S2_DAILY_SCHEDULES][0][S2_SWITCHPOINTS][0][S2_HEAT_SETPOINT] = temp  # type: ignore[call-overload]
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=schedule)

    #
    # STEP 5: check the status of the task

    #
    # STEP 6: check the new schedule was effected
    schedule = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_SCHEDULE
    )
    assert schedule[S2_DAILY_SCHEDULES][0][S2_SWITCHPOINTS][0][S2_HEAT_SETPOINT] == temp  # type: ignore[call-overload]

    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )  # NOTE: json=None

    #
    # STEP 7: PUT a bad schedule
    # [{'code': 'ParameterIsMissing', 'parameterName': 'request', 'message': 'Parameter is missing.'}]


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


@skipif_auth_failed  # GET, PUT
async def test_schedule(evohome_v2: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{xid}/schedule

    Also test commTasks?commTaskId={task_id}
    """

    await _test_schedule(evohome_v2)


# TODO: test_oauth_token(
# TODO: test_get_dhw_status( & test_put_dhw_state(
