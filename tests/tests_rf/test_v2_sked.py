"""evohome-async - validate the handling of vendor APIs (URLs) for Authorization.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, NotRequired, TypedDict

from evohomeasync2 import schemas
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import should_fail_v2, should_work_v2, skipif_auth_failed

if TYPE_CHECKING:
    from tests.conftest import EvohomeClientv2


class SwitchpointT(TypedDict):
    timeOfDay: str
    dhwState: NotRequired[str]  # mutex with heat_setpoint
    heatSetpoint: NotRequired[float]


class DayOfWeekT(TypedDict):
    day_of_week: str
    switchpoints: list[SwitchpointT]


class DailySchedulesT(TypedDict):
    dailySchedules: list[DayOfWeekT]


async def _test_schedule_put(evo: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule"""

    schedule: DailySchedulesT  # {'dailySchedules': [...]}

    # TODO: remove .update() and use URLs only
    await evo.update()

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


async def _test_schedule_tsk(evo: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Also test commTasks?commTaskId={task_id}
    """

    schedule: DailySchedulesT  # {'dailySchedules': [...]}

    # TODO: remove .update() and use URLs only
    await evo.update()

    zone = evo.locations[0].gateways[0].systems[0].zones[0]
    url = f"{zone._TYPE}/{zone.id}/schedule"

    #
    # STEP 1: GET the current schedule
    schedule = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=schemas.TCC_GET_SCHEDULE
    )  # type: ignore[assignment]

    assert isinstance(schedule, dict | list)  # mypy

    if not _DBG_USE_REAL_AIOHTTP:  # TODO: faked server using old schema
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

        assert isinstance(status, dict)  # mypy
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
async def test_schedule_put(evohome_v2: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Does not test /commTasks?commTaskId={task_id}
    """

    await _test_schedule_put(evohome_v2)


@skipif_auth_failed  # GET, PUT
async def test_schedule_tsk(evohome_v2: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{x.id}/schedule

    Also tests /commTasks?commTaskId={task_id}
    """

    await _test_schedule_tsk(evohome_v2)
