#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs)."""

from __future__ import annotations

from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohomeasync2 import ControlSystem, Gateway, Location
from evohomeasync2.const import API_STRFTIME, DhwState, ZoneMode
from evohomeasync2.schema.const import (
    SZ_MODE,
    SZ_STATE,
    SZ_STATE_STATUS,
    SZ_UNTIL,
    SZ_UNTIL_TIME,
)
from evohomeasync2.schema.helpers import pascal_case

from .conftest import _DBG_USE_REAL_AIOHTTP
from .helpers import should_fail, should_work

if TYPE_CHECKING:
    import aiohttp


#######################################################################################


async def _test_task_id(evo: evo2.EvohomeClient) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.
    """

    loc: Location
    gwy: Gateway
    tcs: ControlSystem

    _ = await evo.user_account()
    _ = await evo._installation(disable_status_update=True)

    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.control_systems:
                if tcs.hotwater:
                    # if (dhw := tcs.hotwater) and dhw.temperatureStatus['isAvailable']:
                    dhw = tcs.hotwater
                    break
    # else:
    #     pytest.skip("No available DHW found")
    #

    GET_URL = f"{dhw.TYPE}/{dhw.id}/status"
    PUT_URL = f"{dhw.TYPE}/{dhw.id}/state"

    #
    # PART 0: Get initial state...
    old_status = await should_work(evo, HTTPMethod.GET, GET_URL)
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
        SZ_MODE: old_status[SZ_STATE_STATUS][SZ_MODE],
        SZ_STATE: old_status[SZ_STATE_STATUS][SZ_STATE],
        SZ_UNTIL_TIME: old_status[SZ_STATE_STATUS].get(SZ_UNTIL),
    }  # NOTE: untilTime/until

    #
    # PART 1: Try the basic functionality...
    # new_mode = {SZ_MODE: ZoneMode.PERMANENT_OVERRIDE, SZ_STATE: DhwState.OFF, SZ_UNTIL_TIME: None}
    new_mode = {
        SZ_MODE: ZoneMode.TEMPORARY_OVERRIDE,
        SZ_STATE: DhwState.ON,
        SZ_UNTIL_TIME: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }

    result = await should_work(evo, HTTPMethod.PUT, PUT_URL, json=new_mode)
    assert isinstance(result, dict | list)  # mypy
    # {'id': '840367013'}  # HTTP 201/Created

    task_id = result[0]["id"] if isinstance(result, list) else result["id"]
    url_tsk = f"commTasks?commTaskId={task_id}"

    assert int(task_id)

    status = await should_work(evo, HTTPMethod.GET, url_tsk)
    # {'commtaskId': '840367013', 'state': 'Created'}
    # {'commtaskId': '840367013', 'state': 'Succeeded'}

    assert isinstance(status, dict)  # mypy
    assert status["commtaskId"] == task_id
    assert status["state"] in ("Created", "Running", "Succeeded")

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo, task_id)

    #
    # PART 2A: Try different capitalisations of the JSON keys...
    new_mode = {
        SZ_MODE: ZoneMode.TEMPORARY_OVERRIDE,
        SZ_STATE: DhwState.ON,
        SZ_UNTIL_TIME: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work(evo, HTTPMethod.PUT, PUT_URL, json=new_mode)  # HTTP 201

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo, task_id)

    status = await should_work(evo, HTTPMethod.GET, GET_URL)

    new_mode = {  # NOTE: different capitalisation, until time
        pascal_case(SZ_MODE): ZoneMode.TEMPORARY_OVERRIDE,
        pascal_case(SZ_STATE): DhwState.ON,
        pascal_case(SZ_UNTIL_TIME): (dt.now() + td(hours=2)).strftime(API_STRFTIME),
    }
    _ = await should_work(evo, HTTPMethod.PUT, PUT_URL, json=new_mode)

    # async with asyncio.timeout(30):
    #     _ = await wait_for_comm_task(evo, task_id)

    status = await should_work(evo, HTTPMethod.GET, GET_URL)

    #
    # PART 3: Restore the original mode
    _ = await should_work(evo, HTTPMethod.PUT, PUT_URL, json=old_mode)

    # async with asyncio.timeout(30):
    #    _ = await wait_for_comm_task(evo, task_id)

    status = await should_work(evo, HTTPMethod.GET, GET_URL)

    # assert status # != old_status

    #
    # PART 4A: Try bad JSON...
    bad_mode = {
        SZ_STATE: ZoneMode.TEMPORARY_OVERRIDE,
        SZ_MODE: DhwState.OFF,
        SZ_UNTIL_TIME: None,
    }
    _ = await should_fail(
        evo, HTTPMethod.PUT, PUT_URL, json=bad_mode, status=HTTPStatus.BAD_REQUEST
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
    _ = await should_fail(
        evo, HTTPMethod.GET, url_tsk, status=HTTPStatus.BAD_REQUEST
    )  # [{"code": "InvalidInput", "message": "Invalid Input."}]

    url_tsk = "commTasks?commTaskId=12345678"
    _ = await should_fail(
        evo, HTTPMethod.GET, url_tsk, status=HTTPStatus.NOT_FOUND
    )  # [{"code": "CommTaskNotFound", "message": "Communication task not found."}]


#######################################################################################


async def test_task_id(
    credentials: tuple[str, str],
    client_session: aiohttp.ClientSession,
) -> None:
    """Test /location/{loc.id}/status"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Test is only valid with a real server")

    try:
        await _test_task_id(await instantiate_client_v2(credentials, client_session))

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")
