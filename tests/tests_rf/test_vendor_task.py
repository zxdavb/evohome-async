#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations


from datetime import datetime as dt
from datetime import timedelta as td
from http import HTTPMethod, HTTPStatus
import pytest
import pytest_asyncio

import evohomeasync2 as evo
from evohomeasync2 import Location, Gateway, ControlSystem
from evohomeasync2.const import API_STRFTIME, DhwState, ZoneMode
from evohomeasync2.schema.const import (
    SZ_MODE,
    SZ_STATE,
    SZ_STATE_STATUS,
    SZ_UNTIL,
    SZ_UNTIL_TIME,
)
from evohomeasync2.schema.helpers import pascal_case

from . import _DEBUG_USE_REAL_AIOHTTP
from .helpers import aiohttp, extract_oauth_tokens  # aiohttp may be mocked
from .helpers import user_credentials as _user_credentials
from .helpers import client_session as _client_session
from .helpers import should_work, should_fail, wait_for_comm_task


_global_oauth_tokens: tuple[str, str, dt] = None, None, None


@pytest.fixture()
def user_credentials():
    return _user_credentials()


@pytest_asyncio.fixture
async def session():
    client_session = _client_session()
    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("evohomeasync2.broker.aiohttp", aiohttp)


async def instantiate_client(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_oauth_tokens

    refresh_token, access_token, access_token_expires = _global_oauth_tokens

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_expires=access_token_expires,
    )

    # Authentication
    await client._broker._basic_login()
    _global_oauth_tokens = extract_oauth_tokens(client)

    return client


async def _test_task_id(
    username: str,
    password: str,
    session: aiohttp.ClientSession,
) -> None:
    """Test the task_id returned when using the vendor's RESTful APIs.

    This test can be used to prove that JSON keys are can be camelCase or PascalCase.
    """

    loc: Location
    gwy: Gateway
    tcs: ControlSystem

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    _ = await client._installation(refresh_status=False)

    for loc in client.locations:
        for gwy in loc._gateways:
            for tcs in gwy._control_systems:
                if tcs.hotwater:
                    # if (dhw := tcs.hotwater) and dhw.temperatureStatus['isAvailable']:
                    dhw = tcs.hotwater
                    break
    # else:
    #     pytest.skip("No available DHW found")
    #

    GET_URL = f"{dhw.TYPE}/{dhw._id}/status"
    PUT_URL = f"{dhw.TYPE}/{dhw._id}/state"

    #
    # PART 0: Get initial state...
    old_status = await should_work(client, HTTPMethod.GET, GET_URL)  # HTTP 200
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

    result = await should_work(client, HTTPMethod.PUT, PUT_URL, json=new_mode)
    # {'id': '840367013'}  # HTTP 201/Created

    task_id = result[0]["id"] if isinstance(result, list) else result["id"]
    url_tsk = f"commTasks?commTaskId={task_id}"

    _ = await should_work(client, HTTPMethod.GET, url_tsk)
    # {'commtaskId': '840367013', 'state': 'Created'}
    # {'commtaskId': '840367013', 'state': 'Succeeded'}

    # dtm = dt.now()
    _ = await wait_for_comm_task(client, task_id, timeout=3)
    # assert (dt.now() - dtm).total_seconds() < 2

    #
    # PART 2A: Try different capitalisations of the JSON keys...
    new_mode = {
        SZ_MODE: ZoneMode.TEMPORARY_OVERRIDE,
        SZ_STATE: DhwState.ON,
        SZ_UNTIL_TIME: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work(client, HTTPMethod.PUT, PUT_URL, json=new_mode)  # HTTP 201
    _ = await wait_for_comm_task(client, task_id, timeout=3)
    status = await should_work(client, HTTPMethod.GET, GET_URL)

    new_mode = {  # NOTE: different capitalisation, until time
        pascal_case(SZ_MODE): ZoneMode.TEMPORARY_OVERRIDE,
        pascal_case(SZ_STATE): DhwState.ON,
        pascal_case(SZ_UNTIL_TIME): (dt.now() + td(hours=2)).strftime(API_STRFTIME),
    }
    _ = await should_work(client, HTTPMethod.PUT, PUT_URL, json=new_mode)
    _ = await wait_for_comm_task(client, task_id)
    status = await should_work(client, HTTPMethod.GET, GET_URL)

    #
    # PART 3: Restore the original mode
    _ = await should_work(client, HTTPMethod.PUT, PUT_URL, json=old_mode)
    _ = await wait_for_comm_task(client, task_id)
    status = await should_work(client, HTTPMethod.GET, GET_URL)

    assert status  # == old_status

    #
    # PART 4A: Try bad JSON...
    bad_mode = {
        SZ_STATE: ZoneMode.TEMPORARY_OVERRIDE,
        SZ_MODE: DhwState.OFF,
        SZ_UNTIL_TIME: None,
    }
    _ = await should_fail(
        client, HTTPMethod.PUT, PUT_URL, json=bad_mode, status=HTTPStatus.BAD_REQUEST
    )  #
    # x = [{
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
        client, HTTPMethod.GET, url_tsk, status=HTTPStatus.BAD_REQUEST
    )  # [{"code": "InvalidInput", "message": "Invalid Input."}]

    url_tsk = "commTasks?commTaskId=12345678"
    _ = await should_fail(
        client, HTTPMethod.GET, url_tsk, status=HTTPStatus.NOT_FOUND
    )  # [{"code": "CommTaskNotFound", "message": "Communication task not found."}]

    pass


@pytest.mark.asyncio
async def test_task_id(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/{locationId}/status"""

    if not _DEBUG_USE_REAL_AIOHTTP:
        pytest.skip("Test is only valid with a real server")

    try:
        await _test_task_id(*user_credentials, session)
    except evo.AuthenticationFailed:
        pytest.skip("Unable to authenticate")
