"""Validate the handling of the vendor's v2 APIs (URLs) for Task management.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server (if any) is behaving as per a)

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

from datetime import timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from _evohome.helpers import camel_to_pascal
from evohomeasync2.schemas.const import (
    S2_MODE,
    S2_STATE,
    S2_STATE_STATUS,
    S2_UNTIL,
    S2_UNTIL_TIME,
    TCC_DTM_STRFTIME,
    TccDhwState,
    TccZoneMode,
)
from evohomeasync2.schemas.status import TCC_GET_DHW_STATUS, TCC_GET_LOC_STATUS
from tests.common import get_dhw, get_zon
from tests.const import _DBG_TEST_UNUSED_APIS, _DBG_USE_REAL_AIOHTTP

from .common import should_fail_v2, should_work_v2, skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient as EvohomeClientV2
    from evohomeasync2.schemas.status import TccDhwStatusResponseT

#######################################################################################


# NOTE: a long test, but not all systems have DHW
async def _test_task_id_dhw(evo: EvohomeClientV2) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.

    The DHW's status URL is not used by the client (its status is included in that of
    its location), so it is used here only if _DBG_TEST_UNUSED_APIS.
    """

    await evo.setup()

    if not (dhw := get_dhw(evo)):
        pytest.skip("No available DHW found")

    GET_URL = f"{dhw._TCC_TYPE}/{dhw.id}/status"
    PUT_URL = f"{dhw._TCC_TYPE}/{dhw.id}/state"

    #
    # PART 0: Get initial state...
    old_status: TccDhwStatusResponseT

    if _DBG_TEST_UNUSED_APIS:  # GET the DHW's status (not used by the client)
        old_status = await should_work_v2(
            evo.auth, HTTPMethod.GET, GET_URL, schema=TCC_GET_DHW_STATUS
        )

    else:  # GET it from its location's status, as does the client
        url = f"location/{dhw.location.id}/status?includeTemperatureControlSystems=True"
        loc_status = await should_work_v2(
            evo.auth, HTTPMethod.GET, url, schema=TCC_GET_LOC_STATUS
        )
        old_status = next(
            t["dhw"]
            for g in loc_status["gateways"]
            for t in g["temperatureControlSystems"]
            if "dhw" in t and t["dhw"]["dhwId"] == dhw.id
        )
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
    # new_mode = {S2_MODE: TccZoneMode.PERMANENT_OVERRIDE, S2_STATE: TccDhwState.OFF, S2_UNTIL_TIME: None}
    new_mode = {
        S2_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_STATE: TccDhwState.ON,
        S2_UNTIL_TIME: (dhw.location.now() + td(hours=1)).strftime(TCC_DTM_STRFTIME),
    }

    result = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode)
    assert isinstance(result, dict | list)  # mypy
    # {'id': '840367013'}  # HTTP 201/Created

    task_id = result[0]["id"] if isinstance(result, list) else result["id"]

    assert int(task_id)  # should_work_v2() waited for it (see wait_for_comm_task_id())

    #
    # PART 2A: Try different capitalisations of the JSON keys...
    new_mode = {
        S2_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_STATE: TccDhwState.ON,
        S2_UNTIL_TIME: (dhw.location.now() + td(hours=1)).strftime(TCC_DTM_STRFTIME),
    }
    _ = await should_work_v2(
        evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode
    )  # HTTP 201

    # _ = await wait_for_comm_task_id(evo.auth, task_id)

    if _DBG_TEST_UNUSED_APIS:
        _ = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    new_mode = {  # NOTE: different capitalisation, until time
        camel_to_pascal(S2_MODE): TccZoneMode.TEMPORARY_OVERRIDE,
        camel_to_pascal(S2_STATE): TccDhwState.ON,
        camel_to_pascal(S2_UNTIL_TIME): (dhw.location.now() + td(hours=2)).strftime(
            TCC_DTM_STRFTIME
        ),
    }
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=new_mode)

    # _ = await wait_for_comm_task_id(evo.auth, task_id)

    if _DBG_TEST_UNUSED_APIS:
        _ = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    #
    # PART 3: Restore the original mode
    _ = await should_work_v2(evo.auth, HTTPMethod.PUT, PUT_URL, json=old_mode)

    # _ = await wait_for_comm_task_id(evo.auth, task_id)

    if _DBG_TEST_UNUSED_APIS:
        _ = await should_work_v2(evo.auth, HTTPMethod.GET, GET_URL)

    # assert status # != old_status

    #
    # PART 4A: Try bad JSON...
    bad_mode = {
        S2_STATE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_MODE: TccDhwState.OFF,
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
async def _test_task_id_zone(evo: EvohomeClientV2) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.
    """

    await evo.setup()

    if not (zone := get_zon(evo)):
        pytest.skip("No available Zone found")

    GET_URL = f"{zone._TCC_TYPE}/{zone.id}/status"
    # T_URL = f"{zone._TCC_TYPE}/{zone.id}/mode"

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
async def test_task_id_dhw(
    evohome_v2: EvohomeClientV2,
) -> None:
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
async def _out_test_task_id_zone(evohome_v2: EvohomeClientV2) -> None:
    """Test /commTasks?commTaskId={task_id}"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Test is only valid with a real server")

    try:
        await _test_task_id_zone(evohome_v2)

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")
