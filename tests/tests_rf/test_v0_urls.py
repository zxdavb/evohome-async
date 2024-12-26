"""Invoke every vendor RESTful API (URL) used by the v0 client.

This is used to document the RESTful API that is provided by the vendor.

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

import logging
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from evohome import exceptions as exc
from evohomeasync.auth import Auth
from evohomeasync.schemas import (
    factory_location_response_list,
    factory_user_account_info_response,
)
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync.schemas import (
        TccLocationResponseT,
        TccSessionResponseT,
        TccUserAccountInfoResponseT,
    )
    from tests.conftest import CredentialsManager


async def _test_get_account_info(auth: Auth) -> TccUserAccountInfoResponseT:
    """Test GET /accountInfo"""

    return await auth._make_request(
        HTTPMethod.GET,
        "accountInfo",
    )  # type: ignore[return-value]


async def _test_get_comm_tasks(auth: Auth, tsk_id: int) -> dict[str, Any]:
    """Test GET /commTasks?commTaskId={tsk_id}"""

    return await auth._make_request(
        HTTPMethod.PUT,
        f"commTasks?commTaskId={tsk_id}",
    )  # type: ignore[return-value]


async def _test_get_locations(auth: Auth, usr_id: int) -> list[TccLocationResponseT]:
    """Test GET /locations?userId={usr_id}&allData=True"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"locations?userId={usr_id}&allData=True",
    )  # type: ignore[return-value]


async def _test_post_session(auth: Auth) -> TccSessionResponseT:
    """Test POST /session
    data = {
        "Username": username,
        "Password": password,
        "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
    }
    """

    raise NotImplementedError


async def _test_put_devices_dhw(auth: Auth, dhw_id: int) -> dict[str, Any]:
    """Test PUT /devices/{dhw_id}/thermostat/changeableValues
    data = {
        "Status": status,  ["Scheduled","Hold"]  # no: "Temporary"?
        "Mode": mode,     ["DHWOn", "DHWOff"]
        "NextTime": None | until.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SpecialModes": None,
        "HeatSetpoint": None,
        "CoolSetpoint": None,
    }
    """

    data = {"Status": "Scheduled"}

    return await auth._make_request(
        HTTPMethod.PUT,
        f"devices/{dhw_id}/thermostat/changeableValues",
        data=data,
    )  # type: ignore[return-value]


async def _test_put_devices_zon(auth: Auth, zon_id: int) -> dict[str, Any]:
    """Test PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    data = {
        "Status": "Temporary",
        "NextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Value": temperature,
    }
    data = {"Status": "Hold",      "NextTime": None, "Value": temperature}
    data = {"Status": "Scheduled", "NextTime": None, "Value": None}
    """

    data = {"Status": "Scheduled"}  # , "NextTime": None, "Value": None}

    return await auth._make_request(
        HTTPMethod.PUT,
        f"devices/{zon_id}/thermostat/changeableValues/heatSetpoint",
        data=data,
    )  # type: ignore[return-value]


async def _test_put_evo_touch_systems(auth: Auth, loc_id: int) -> dict[str, Any]:
    """Test PUT /evoTouchSystems?locationId={loc_id}
    data = {
        "QuickAction": status,  All except AuutWithEco, Auto must have QANT None
        "QuickActionNextTime": None | until.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    """

    data = {"QuickAction": "Auto", "QuickActionNextTime": None}

    return await auth._make_request(
        HTTPMethod.PUT,
        f"evoTouchSystems?locationId={loc_id}",
        data=data,
    )  # type: ignore[return-value]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    credentials_manager: CredentialsManager,
) -> None:
    """Test Location, Gateway and TCS URLs."""

    # Create the Auth client (may POST /session)...
    auth = Auth(
        credentials_manager.get_session_id,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # GET /accountInfo
    usr_info = await _test_get_account_info(auth)
    factory_user_account_info_response()(usr_info)

    #
    # GET /locations?userId={usr_id}&allData=True
    usr_locs = await _test_get_locations(auth, usr_info["userID"])
    factory_location_response_list()(usr_locs)

    #
    # PUT /evoTouchSystems?locationId={loc_id}  # NOTE: this URL doesn't work?
    loc_idx = 2

    with pytest.raises(exc.ApiRequestFailedError) as err:
        task = await _test_put_evo_touch_systems(auth, usr_locs[0]["locationID"])
    assert err.value.status == HTTPStatus.NOT_FOUND  # 404

    #
    # PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    zon_id = next(
        d["deviceID"]
        for d in usr_locs[loc_idx]["devices"]
        if d["thermostatModelType"].startswith("EMEA_")
    )

    task = await _test_put_devices_zon(auth, zon_id)

    #
    # GET /commTasks?commTaskId={tsk_id}
    _ = await _test_get_comm_tasks(auth, task["id"])

    #
    # PUT /devices/{dhw_id}/thermostat/changeableValues
    for loc in usr_locs:
        if dhw := next(
            d
            for d in loc["devices"]
            if d["thermostatModelType"] == "DOMESTIC_HOT_WATER"
        ):
            break

    if dhw:
        task = await _test_put_devices_dhw(auth, dhw["deviceID"])
