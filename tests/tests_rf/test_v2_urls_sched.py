#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs) for Authorization.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

from evohomeasync2 import schema

from . import faked_server as faked
from .common import should_fail_v2, should_work_v2, skipif_auth_failed
from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    from ..conftest import EvohomeClientv2


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
    temp = schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"]  # type: ignore[call-overload]

    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp + 1  # type: ignore[call-overload,operator]
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
        schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"]  # type: ignore[call-overload]
        == temp + 1  # type: ignore[operator]
    )

    #
    # STEP 4: PUT the original schedule back
    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp  # type: ignore[call-overload]
    _ = await should_work_v2(evo, HTTPMethod.PUT, url, json=schedule)

    #
    # STEP 5: check the status of the task

    #
    # STEP 6: check the new schedule was effected
    schedule = await should_work_v2(
        evo, HTTPMethod.GET, url, schema=schema.SCH_GET_SCHEDULE
    )
    assert schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] == temp  # type: ignore[call-overload]

    _ = await should_fail_v2(
        evo, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )  # NOTE: json=None

    #
    # STEP 7: PUT a bad schedule
    # [{'code': 'ParameterIsMissing', 'parameterName': 'request', 'message': 'Parameter is missing.'}]


# TODO: Test sending bad schedule


@skipif_auth_failed  # GET, PUT
async def test_schedule(evohome_v2: EvohomeClientv2) -> None:
    """Test /{x._TYPE}/{xid}/schedule

    Also test commTasks?commTaskId={task_id}
    """

    await _test_schedule(evohome_v2)
