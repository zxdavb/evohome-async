"""Validate the handling of the vendor's v2 APIs (URLs) for Schedules.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server (if any) is behaving as per a)

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohomeasync2 import schemas
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import get_dhw, should_fail_v2, should_work_v2, skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync2.schemas.schedule import (
        TccDhwDailySchedulesT,
        TccZonDailySchedulesT,
    )
    from tests.conftest import EvohomeClientV2


async def _test_schedule_put(evo: EvohomeClientV2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule"""

    schedule: TccZonDailySchedulesT  # {'dailySchedules': [...]}

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    zone = evo.locations[0].gateways[0].systems[0].zones[0]
    url = f"{zone._TYPE}/{zone.id}/schedule"

    #
    # STEP 1: GET the current schedule
    schedule = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_SCHEDULE
    )  # type: ignore[assignment]

    # an example of the expected response:
    """
        {
            'dailySchedules': [
                {
                    'dayOfWeek': 'Monday',
                    'switchpoints': [
                        {'heatSetpoint': 23.1, 'timeOfDay': '06:30:00'},
                        {'heatSetpoint': 18.0, 'timeOfDay': '08:00:00'},
                        {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'},
                        {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}
                    ]
                }, {
                    'dayOfWeek': 'Tuesday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '06:30:00'}, {'heatSetpoint': 18.0, 'timeOfDay': '08:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                },{
                    'dayOfWeek': 'Wednesday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '06:30:00'}, {'heatSetpoint': 18.0, 'timeOfDay': '08:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                }, {
                    'dayOfWeek': 'Thursday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '06:30:00'}, {'heatSetpoint': 18.0, 'timeOfDay': '08:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                }, {
                    'dayOfWeek': 'Friday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '06:30:00'}, {'heatSetpoint': 18.0, 'timeOfDay': '08:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                }, {
                    'dayOfWeek': 'Saturday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '07:30:00'}, {'heatSetpoint': 18.5, 'timeOfDay': '11:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                }, {
                    'dayOfWeek': 'Sunday',
                    'switchpoints': [{'heatSetpoint': 19.1, 'timeOfDay': '07:30:00'}, {'heatSetpoint': 18.5, 'timeOfDay': '11:00:00'}, {'heatSetpoint': 19.1, 'timeOfDay': '17:00:00'}, {'heatSetpoint': 14.9, 'timeOfDay': '21:30:00'}]
                }
            ]
        }
    """

    #
    # STEP 2: PUT a null schedule  # NOTE: json=None
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )

    # the expected response:
    """
        [{
            'code': 'ParameterIsMissing',
            'parameterName': 'request',
            'message': 'Parameter is missing.'
    }]
    """

    #
    # STEP 3: PUT an invalid schedule  # NOTE: json={}
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, url, json={}, status=HTTPStatus.BAD_REQUEST
    )

    # the expected response:
    """
        [{
            'code': 'DayOfWeekMissing',
            'message': 'One or more days missing.'
        }]
    """

    #
    # STEP 4: PUT a valid schedule
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=dict(schedule))

    # an example of the expected response:
    """
        {'id': '840367013'}
    """


async def _test_schedule_tsk(evo: EvohomeClientV2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Also test commTasks?commTaskId={task_id}
    """

    schedule: TccZonDailySchedulesT  # {'dailySchedules': [...]}

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    zone = evo.locations[0].gateways[0].systems[0].zones[0]
    url = f"{zone._TYPE}/{zone.id}/schedule"

    #
    # STEP 1: GET the current schedule
    schedule = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_SCHEDULE
    )  # type: ignore[assignment]

    assert isinstance(schedule, dict)  # mypy

    if not _DBG_USE_REAL_AIOHTTP:  # TODO: REMOVE: faked server using old schema
        return

    #
    # STEP 2: PUT a new schedule
    temp = schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"]
    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp + 1

    status = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=dict(schedule))

    assert isinstance(status, dict | list)  # mypy

    #
    # STEP 2: check the status of the task
    if _DBG_USE_REAL_AIOHTTP:
        task_id = status[0]["id"] if isinstance(status, list) else status["id"]

        status = await should_work_v2(
            evo.auth, HTTPMethod.GET, f"commTasks?commTaskId={task_id}"
        )
        # {'commtaskId': '840367013', 'state': 'Created'}
        # {'commtaskId': '840367013', 'state': 'Running'}
        # {'commtaskId': '840367013', 'state': 'Succeeded'}

        assert isinstance(status, dict)  # mypy  # TODO: use a SCHEMA
        assert status["commtaskId"] == task_id
        assert status["state"] in ("Created", "Running", "Succeeded")

    #
    # STEP 3: check the new schedule was effected
    schedule = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_SCHEDULE
    )  # type: ignore[assignment]

    assert schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] == temp + 1
    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp

    #
    # STEP 4: PUT the original schedule back
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, url, json=dict(schedule))

    #
    # STEP 5: (optional) check the status of the task

    #
    # STEP 6: check the original schedule was effected
    schedule = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_SCHEDULE
    )  # type: ignore[assignment]

    assert schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] == temp


@skipif_auth_failed  # GET, PUT
async def test_schedule_put(evohome_v2: EvohomeClientV2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Does not test /commTasks?commTaskId={task_id}
    """

    await _test_schedule_put(evohome_v2)


@skipif_auth_failed  # GET, PUT
async def test_schedule_tsk(evohome_v2: EvohomeClientV2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Also tests /commTasks?commTaskId={task_id}
    """

    await _test_schedule_tsk(evohome_v2)


async def _test_schedule_get_schema_zon(evo: EvohomeClientV2) -> None:
    """Document the exact key casing in the vendor's GET schedule response.

    The vendor API is reportedly case-insensitive on PUT, but this confirms
    what casing GET actually returns (expected: camelCase throughout).
    """

    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    zone = evo.locations[0].gateways[0].systems[0].zones[0]
    url = f"{zone._TYPE}/{zone.id}/schedule"

    #
    # GET without schema so we capture whatever the server actually sends back
    schedule: TccZonDailySchedulesT = await should_work_v2(  # type: ignore[assignment]
        evo.auth, HTTPMethod.GET, url
    )

    # an example of the expected response:
    """
        {
            'dailySchedules': [
                {
                    'dayOfWeek': 'Monday',
                    'switchpoints': [{'heatSetpoint': 18.1, 'timeOfDay': '07:00:00'}, ...]
                }, ...
            ]
        }
    """

    # Confirm schema, and that the keys are camelCase
    assert "DailySchedules" not in schedule  # is not PascalCase
    day = schedule["dailySchedules"][0]

    assert "DayOfWeek" not in day  # is not PascalCase
    assert day["dayOfWeek"] == "Monday"  # not "0", nor an int (an ordinal)

    assert "Switchpoints" not in day  # is not PascalCase
    sp = day["switchpoints"][0]

    assert "HeatSetpoint" not in sp  # is not PascalCase
    assert isinstance(sp["heatSetpoint"], float)  # e.g. 18.1

    assert "TimeOfDay" not in sp  # is not PascalCase
    assert isinstance(sp["timeOfDay"], str)  # e.g. "06:30:00"


async def _test_schedule_get_schema_dhw(evo: EvohomeClientV2) -> None:
    """Document the exact key casing in the vendor's GET DHW schedule response.

    Mirrors _test_schedule_get_schema for DHW — switchpoints use dhwState
    instead of heatSetpoint, but the same camelCase key convention applies.
    """
    # TODO: remove .update() and use URLs only
    await evo.update(dont_update_status=True)

    if not (dhw := get_dhw(evo)):
        pytest.skip("No DHW found in TCS")

    url = f"{dhw._TYPE}/{dhw.id}/schedule"

    #
    # GET without schema so we capture whatever the server actually sends back
    schedule: TccDhwDailySchedulesT = await should_work_v2(  # type: ignore[assignment]
        evo.auth, HTTPMethod.GET, url
    )

    # an example of the expected response:
    """
        {
            'dailySchedules': [
                {
                    'dayOfWeek': 'Monday',
                    'switchpoints': [{'dhwState': 'On', 'timeOfDay': '06:30:00'}, ...]
                }, ...
            ]
        }
    """

    # Confirm schema, and that the keys are camelCase
    assert "DailySchedules" not in schedule  # is not PascalCase
    day = schedule["dailySchedules"][0]

    assert "DayOfWeek" not in day  # is not PascalCase
    assert day["dayOfWeek"] == "Monday"  # not "0", nor an int (an ordinal)

    assert "Switchpoints" not in day  # is not PascalCase
    sp = day["switchpoints"][0]

    assert "DhwState" not in sp  # is not PascalCase
    assert sp["dhwState"] in ("On", "Off")

    assert "TimeOfDay" not in sp  # is not PascalCase
    assert isinstance(sp["timeOfDay"], str)  # e.g. "06:30:00"


@skipif_auth_failed  # GET
async def test_schedule_get_schema_zon(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /{x._TYPE}/{x.id}/schedule key casing.

    Documents that the vendor returns camelCase keys in GET responses even
    though the API is reportedly case-insensitive for PUT request bodies.
    """

    await _test_schedule_get_schema_zon(evohome_v2)


@skipif_auth_failed  # GET
async def test_schedule_get_schema_dhw(evohome_v2: EvohomeClientV2) -> None:
    """Test GET /{dhw._TYPE}/{dhw.id}/schedule key casing.

    DHW mirror of test_schedule_get_schema — skipped if no DHW in the TCS.
    """

    await _test_schedule_get_schema_dhw(evohome_v2)
