"""Invoke every vendor RESTful API (URL) used by the v0 client.

This is used to document the RESTful API that is provided by the vendor.

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used).

Every PUT here is a no-op on a real system: it (re)asserts the current state of an
entity that is already following its schedule (or is already in permanent Auto mode),
and is skipped otherwise. So these tests will not disturb anyone's heating.

The vendor rejects a PUT to a device that is not alive (400, DeviceIsLost), so these
tests need a device whose gateway is online (see test_v0_urls_auth.py for lost ones).

The request bodies are those of the older (non-async) client, which were in PascalCase.
"""

from __future__ import annotations

import asyncio
import logging
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from _evohome import exceptions as exc
from evohomeasync.auth import Auth
from evohomeasync.schemas import TCC_GET_USR_INFO, TCC_GET_USR_LOCS
from evohomeasync2 import EvohomeClient as EvohomeClientV2
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import (
    is_alive_v0,
    is_dhw_v0,
    is_permanent_auto_v2,
    is_zone_v0,
    skipif_auth_failed,
    status_of_v0,
    task_id_v0,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from evohome_cli.auth import TokenCacheManager
    from evohomeasync.schemas import (
        TccLocationResponseT,
        TccSessionResponseT,
        TccUserAccountInfoResponseT,
    )


# TODO: Create a validator for the TccTaskResponseT typedDict (but until then...)
type _TccTaskResponse = dict[str, Any] | list[dict[str, Any]]  # c.f. TccTaskResponseT

_TASK_TIMEOUT = 30  # seconds, for a comm task to succeed


async def _post_session(auth: Auth) -> TccSessionResponseT:
    """Test POST /session
    data = {
        "Username": username,
        "Password": password,
        "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
    }
    """

    raise NotImplementedError


async def get_account_info(auth: Auth) -> TccUserAccountInfoResponseT:
    """Test GET /accountInfo"""

    return TCC_GET_USR_INFO(
        await auth._make_request(
            HTTPMethod.GET,
            "accountInfo",
        )
    )


async def get_comm_tasks(auth: Auth, tsk_id: str) -> _TccTaskResponse:
    """Test GET /commTasks?commTaskId={tsk_id}

    Returns (e.g.): {"state": "Succeeded"}
    """

    return await auth._make_request(
        HTTPMethod.GET,
        f"commTasks?commTaskId={tsk_id}",
    )


async def get_locations(auth: Auth, usr_id: int) -> list[TccLocationResponseT]:
    """Test GET /locations?userId={usr_id}&allData=True"""

    return TCC_GET_USR_LOCS(
        await auth._make_request(
            HTTPMethod.GET,
            f"locations?userId={usr_id}&allData=True",
        )
    )


async def put_devices_dhw(
    auth: Auth, dhw_id: int, json: Mapping[str, object]
) -> _TccTaskResponse:
    """Test PUT /devices/{dhw_id}/thermostat/changeableValues
    json = {
        "Status": status,  # "Scheduled" | "Hold"
        "Mode": mode,  # None | "DHWOn" | "DHWOff"
        "NextTime": None | until.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SpecialModes": None,
        "HeatSetpoint": None,
        "CoolSetpoint": None,
    }
    """

    return await auth._make_request(
        HTTPMethod.PUT,
        f"devices/{dhw_id}/thermostat/changeableValues",
        json=json,
    )


async def put_devices_zon(
    auth: Auth, zon_id: int, json: Mapping[str, object]
) -> _TccTaskResponse:
    """Test PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    json = {"Value": temperature, "Status": "Temporary", "NextTime": until}
    json = {"Value": temperature, "Status": "Hold",      "NextTime": None}
    json = {"Value": None,        "Status": "Scheduled", "NextTime": None}
    """

    return await auth._make_request(
        HTTPMethod.PUT,
        f"devices/{zon_id}/thermostat/changeableValues/heatSetpoint",
        json=json,
    )


async def put_evo_touch_systems(
    auth: Auth, loc_id: int, json: Mapping[str, object]
) -> _TccTaskResponse:
    """Test PUT /evoTouchSystems?locationId={loc_id}
    json = {
        "QuickAction": mode,  # All except AutoWithEco, Auto must have QANT None
        "QuickActionNextTime": None | until.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    """

    return await auth._make_request(
        HTTPMethod.PUT,
        f"evoTouchSystems?locationId={loc_id}",
        json=json,
    )


async def _wait_for_task(auth: Auth, response: _TccTaskResponse) -> None:
    """Wait for the comm task of a PUT to succeed (GET /commTasks?commTaskId=...)."""

    task_id = task_id_v0(response)

    async with asyncio.timeout(_TASK_TIMEOUT):
        while True:
            task = await get_comm_tasks(auth, task_id)
            assert isinstance(task, dict), task
            if task["state"] == "Succeeded":
                return
            await asyncio.sleep(0.5)


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location and TCS URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # GET /accountInfo
    usr_info = await get_account_info(auth)

    #
    # GET /locations?userId={usr_id}&allData=True
    usr_locs = await get_locations(auth, usr_info["userID"])

    # an evohome location (not, say, a Round Thermostat), already in permanent Auto
    loc_id = next(
        (
            loc["locationID"]
            for loc in usr_locs
            if any(is_zone_v0(d) for d in loc["devices"])
        ),
        None,
    )
    if loc_id is None:
        pytest.skip("No evohome location found")

    if not await is_permanent_auto_v2(EvohomeClientV2(credentials_manager), loc_id):
        pytest.skip("Location is not in permanent Auto mode (won't change it)")

    #
    # PUT /evoTouchSystems?locationId={loc_id}
    # NOTE: this URL doesn't work - has been removed by the vendor?
    json = {"QuickAction": "Auto", "QuickActionNextTime": None}  # a no-op
    with pytest.raises(exc.ApiCallFailedError) as err:
        _ = await put_evo_touch_systems(auth, loc_id, json)
    assert err.value.status == HTTPStatus.NOT_FOUND
    # '<!DOCTYPE html PUBLIC ... 404 - File or directory not found ...'  (from IIS)


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_zon_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Zone URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 0: find a zone that is following its schedule...
    usr_info = await get_account_info(auth)
    usr_locs = await get_locations(auth, usr_info["userID"])

    zone = next(
        (
            d
            for loc in usr_locs
            for d in loc["devices"]
            if is_zone_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if zone is None:
        pytest.skip("No live zone found that is following its schedule")

    #
    # PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    json = {"Value": None, "Status": "Scheduled", "NextTime": None}  # a no-op
    task = await put_devices_zon(auth, zone["deviceID"], json)

    #
    # GET /commTasks?commTaskId={tsk_id}
    await _wait_for_task(auth, task)


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_dhw_urls(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test DHW URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 0: find a DHW that is following its schedule...
    usr_info = await get_account_info(auth)
    usr_locs = await get_locations(auth, usr_info["userID"])

    dhw = next(
        (
            d
            for loc in usr_locs
            for d in loc["devices"]
            if is_dhw_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if dhw is None:
        pytest.skip("No live DHW found that is following its schedule")

    #
    # PUT /devices/{dhw_id}/thermostat/changeableValues
    json = {  # a no-op
        "Status": "Scheduled",
        "Mode": None,
        "NextTime": None,
        "SpecialModes": None,
        "HeatSetpoint": None,
        "CoolSetpoint": None,
    }
    task = await put_devices_dhw(auth, dhw["deviceID"], json)

    #
    # GET /commTasks?commTaskId={tsk_id}
    await _wait_for_task(auth, task)
