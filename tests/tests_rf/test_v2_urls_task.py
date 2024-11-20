#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs) for task management.

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
from evohomeasync2 import ControlSystem, Gateway, HotWater, Location, Zone
from evohomeasync2.const import API_STRFTIME, DhwState, ZoneMode
from evohomeasync2.schemas.const import (
    S2_MODE,
    S2_STATE,
    S2_STATE_STATUS,
    S2_UNTIL,
    S2_UNTIL_TIME,
)
from evohomeasync2.schemas.helpers import pascal_case

from .common import should_fail_v2, should_work_v2, skipif_auth_failed
from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    from ..conftest import EvohomeClientv2

#######################################################################################


# NOTE: a long test, but not all systems have DHW
async def _test_task_id_dhw(evo: EvohomeClientv2) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.
    """

    loc: Location
    gwy: Gateway
    tcs: ControlSystem

    await evo.update(_dont_update_status=True)

    dhw: HotWater | None = None

    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.control_systems:
                if tcs.hotwater:
                    # if (dhw := tcs.hotwater) and dhw.temperatureStatus['isAvailable']:
                    dhw = tcs.hotwater
                    break

    if dhw is None:
        pytest.skip("No available DHW found")

    GET_URL = f"{dhw._TYPE}/{dhw.id}/status"
    PUT_URL = f"{dhw._TYPE}/{dhw.id}/state"

    #
    # PART 0: Get initial state...
    old_status = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)
    assert isinstance(old_status, dict)  # mypy
    # {
    #     'dhwId': '3933910',
    #     'temperatureStatus': {'isAvailable': False},
    #     'stateStatus': {'state': 'Off', 'mode': 'FollowSchedule'},
    #     'activeFaults': []
    # }  # HTTP 200
    # {
    #     'dhwId': '3933910',
    #     'temperatureStatus': {'temperature': 21.0, 'isAvailable': True},
    #     'stateStatus': {
    #         'state': 'On',
    #         'mode': 'TemporaryOverride',
    #         'until': '2023-10-30T18:40:00Z'
    #     },
    #     'activeFaults': []
    # }  # HTTP 200

    old_mode = {
        S2_MODE: old_status[S2_STATE_STATUS][S2_MODE],
        S2_STATE: old_status[S2_STATE_STATUS][S2_STATE],
        S2_UNTIL_TIME: old_status[S2_STATE_STATUS].get(S2_UNTIL),
    }  # NOTE: untilTime/until

    #
    # PART 1: Try the basic functionality...
    # new_mode = {S2_MODE: ZoneMode.PERMANENT_OVERRIDE, S2_STATE: DhwState.OFF, S2_UNTIL_TIME: None}
    new_mode = {
        S2_MODE: ZoneMode.TEMPORARY_OVERRIDE,
        S2_STATE: DhwState.ON,
        S2_UNTIL_TIME: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }

    result = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode)
    assert isinstance(result, dict | list)  # mypy
    # {'id': '840367013'}  # HTTP 201/Created

    task_id = result[0]["id"] if isinstance(result, list) else result["id"]
    url_tsk = f"commTasks?commTaskId={task_id}"

    assert int(task_id)

    status = await should_work_v2(evo.auth, HTTPMethod.GET, url_tsk)
    # {'commtaskId': '840367013', 'state': 'Created'}
    # {'commtaskId': '840367013', 'state': 'Succeeded'}

    assert isinstance(status, dict)  # mypy
    assert status["commtaskId"] == task_id
    assert status["state"] in ("Created", "Running", "Succeeded")

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo.auth, task_id)

    #
    # PART 2A: Try different capitalisations of the JSON keys...
    new_mode = {
        S2_MODE: ZoneMode.TEMPORARY_OVERRIDE,
        S2_STATE: DhwState.ON,
        S2_UNTIL_TIME: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work_v2(
        evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode
    )  # HTTP 201

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo.auth, task_id)

    status = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    new_mode = {  # NOTE: different capitalisation, until time
        pascal_case(S2_MODE): ZoneMode.TEMPORARY_OVERRIDE,
        pascal_case(S2_STATE): DhwState.ON,
        pascal_case(S2_UNTIL_TIME): (dt.now() + td(hours=2)).strftime(API_STRFTIME),
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode)

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo.auth, task_id)

    status = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    #
    # PART 3: Restore the original mode
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=old_mode)

    # async with asyncio.timeout(30):
    #    _ = await wait_for_comm_task(evo.auth, task_id)

    status = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    # assert status # != old_status

    #
    # PART 4A: Try bad JSON...
    bad_mode = {
        S2_STATE: ZoneMode.TEMPORARY_OVERRIDE,
        S2_MODE: DhwState.OFF,
        S2_UNTIL_TIME: None,
    }
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.PUT, PUT_URL, json=bad_mode, status=HTTPStatus.BAD_REQUEST
    )

    # _ = [{
    #     "code": "InvalidInput", "message": """
    #         Error converting value 'TemporaryOverride'
    #         to type 'DomesticHotWater.Enums.EMEADomesticHotWaterState'.
    #         Path 'state', line 1, position 29.
    #     """
    # }, {
    #     "code": "InvalidInput", "message": """
    #         Error converting value 'Off'
    #         to type 'DomesticHotWater.Enums.EMEADomesticHotWaterSetpointMode'.
    #         Path 'mode', line 1, position 44.
    #     """
    # }]  # NOTE: message has been slightly edited for readability

    #
    # PART 4B: Try 'bad' task_id values...
    url_tsk = "commTasks?commTaskId=ABC"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url_tsk, status=HTTPStatus.BAD_REQUEST
    )  # [{"code": "InvalidInput", "message": "Invalid Input."}]

    url_tsk = "commTasks?commTaskId=12345678"
    _ = await should_fail_v2(
        evo.auth, HTTPMethod.GET, url_tsk, status=HTTPStatus.NOT_FOUND
    )  # [{"code": "CommTaskNotFound", "message": "Communication task not found."}]


# TODO: a short test
async def _test_task_id_zone(evo: EvohomeClientv2) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.
    """

    loc: Location
    gwy: Gateway
    tcs: ControlSystem

    await evo.update(_dont_update_status=True)

    zone: Zone | None = None

    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.control_systems:
                if not tcs.zones:
                    continue
                zone = tcs.zones[0]
                break

    if zone is None:
        pytest.skip("No available Zone found")

    GET_URL = f"{zone._TYPE}/{zone.id}/status"
    # T_URL = f"{zone._TYPE}/{zone.id}/mode"

    #
    # PART 0: Get the initial mode...
    old_status = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)
    assert isinstance(old_status, dict)  # mypy
    # {
    #     'zoneId': '3432576',
    #     'name': 'Main Room'
    #     'temperatureStatus': {'temperature': 25.5, 'isAvailable': True}
    #     'setpointStatus': {
    #         'targetHeatTemperature': 10.0,
    #         'setpointMode': 'FollowSchedule'
    #      }
    #     'activeFaults': []
    # }  # HTTP 200


@skipif_auth_failed
async def test_task_id_dhw(evohome_v2: EvohomeClientv2) -> None:
    """Test /commTasks?commTaskId={task_id}"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Test is only valid with a real server")

    try:
        await _test_task_id_dhw(evohome_v2)

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@skipif_auth_failed
async def _OUT_test_task_id_zone(evohome_v2: EvohomeClientv2) -> None:
    """Test /commTasks?commTaskId={task_id}"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Test is only valid with a real server")

    try:
        await _test_task_id_zone(evohome_v2)

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")
