"""Invoke every vendor RESTful API (URL) used by the v2 client.

This is used to document the RESTful API that is provided by the vendor.

Testing is at HTTP request layer (e.g. GET/PUT).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohomeasync2 import ApiRequestFailedError
from evohomeasync2.auth import Auth
from evohomeasync2.schemas.account import factory_user_account
from evohomeasync2.schemas.config import (
    factory_location_installation_info,
    factory_user_locations_installation_info,
)
from evohomeasync2.schemas.schedule import factory_dhw_schedule, factory_zon_schedule
from evohomeasync2.schemas.status import (
    factory_dhw_status,
    factory_loc_status,
    factory_tcs_status,
    factory_zon_status,
)
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync2.schemas.account import TccTaskResponseT, TccUsrAccountResponseT
    from evohomeasync2.schemas.config import TccLocConfigResponseT
    from evohomeasync2.schemas.schedule import (
        TccDhwDailySchedulesT,
        TccZonDailySchedulesT,
    )
    from evohomeasync2.schemas.status import (
        TccDhwStatusResponseT,
        TccLocStatusResponseT,
        TccTcsStatusResponseT,
        TccZonStatusResponseT,
    )
    from tests.conftest import CredentialsManager


async def _post_auth_oauth_token(auth: Auth) -> dict[str, int | str]:
    """Test POST /Auth/OAuth/Token"""

    raise NotImplementedError


async def get_usr_account(auth: Auth) -> TccUsrAccountResponseT:
    """Test GET /userAccount"""

    return await auth._make_request(
        HTTPMethod.GET,
        "userAccount",
    )  # type: ignore[return-value]


async def get_usr_locations(auth: Auth, usr_id: str) -> list[TccLocConfigResponseT]:
    """Test GET /location/installationInfo?userId={user_id}"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True",
    )  # type: ignore[return-value]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    credentials_manager: CredentialsManager,
) -> None:
    """Test Location, Gateway and TCS URLs."""

    # STEP 0: Create the Auth client...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 1: GET /userAccount
    usr_info = await get_usr_account(auth)
    factory_user_account()(usr_info)

    #
    # STEP 2: GET /location/installationInfo?userId={user_id}
    usr_locs = await get_usr_locations(auth, usr_info["userId"])
    factory_user_locations_installation_info()(usr_locs)

    #
    # STEP 3: GET /location/{loc_id}/installationInfo
    loc_id = usr_locs[0]["locationInfo"]["locationId"]

    loc_config = await get_loc_config(auth, loc_id)
    factory_location_installation_info()(loc_config)

    #
    # STEP 4: GET /location/{loc_id}/status
    loc_status = await get_loc_status(auth, loc_id)
    factory_loc_status()(loc_status)

    #
    #
    tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
    tcs_id = tcs_config["systemId"]

    #
    # STEP A: GET /temperatureControlSystem/{tcs_id}/status
    tcs_status = await get_tcs_status(auth, tcs_id)
    factory_tcs_status()(tcs_status)

    #
    # STEP B: PUT /temperatureControlSystem/{tcs_id}/mode
    _ = await put_tcs_mode(auth, tcs_id)
    # factory_tcs_status()(task)  # e.g. {'id': '1668279943'}


async def get_loc_config(auth: Auth, loc_id: str) -> TccLocConfigResponseT:
    """Test GET /location/{loc_id}/installationInfo"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"location/{loc_id}/installationInfo?includeTemperatureControlSystems=True",
    )  # type: ignore[return-value]


async def get_loc_status(auth: Auth, loc_id: str) -> TccLocStatusResponseT:
    """Test GET /location/{loc_id}/status"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"location/{loc_id}/status?includeTemperatureControlSystems=True",
    )  # type: ignore[return-value]


async def get_tcs_status(auth: Auth, tcs_id: str) -> TccTcsStatusResponseT:
    """Test GET /temperatureControlSystem/{tcs_id}/status"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"temperatureControlSystem/{tcs_id}/status",
    )  # type: ignore[return-value]


async def put_tcs_mode(auth: Auth, tcs_id: str) -> TccTaskResponseT:
    """Test PUT /temperatureControlSystem/{tcs_id}/mode"""

    until = (dt.now(tz=UTC) + td(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={
            "systemMode": "Away",
            "permanent": False,
            "timeUntil": until,
        },
    )

    # for TCSs/zones, TemporaryOverride requires timeUntil (but DHW uses untilTime)
    with pytest.raises(ApiRequestFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"temperatureControlSystem/{tcs_id}/mode",
            json={
                "systemMode": "Away",
                "permanent": False,
                "untilTime": until,
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "SystemModeChangeTimeUntilNotSet" in exc_info.value.message

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={"systemMode": "Auto", "permanent": True},
    )  # type: ignore[return-value]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_zon_urls(
    credentials_manager: CredentialsManager,
) -> None:
    """Test Zone URLs"""

    #
    # STEP 0: Create the Auth client, get the TCS config...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info = await get_usr_account(auth)
    usr_locs = await get_usr_locations(auth, usr_info["userId"])

    #
    #
    tcs_config = usr_locs[0]["gateways"][0]["temperatureControlSystems"][0]
    zon_id = tcs_config["zones"][0]["zoneId"]

    #
    # STEP A: GET /temperatureZone/{zon_id}/status
    zon_status = await get_zon_status(auth, zon_id)
    factory_zon_status()(zon_status)

    #
    # STEP B: PUT /temperatureZone/{zon_id}/heatSetpoint
    _ = await put_zon_heat_setpoint(auth, zon_id)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}

    #
    # STEP C: GET /temperatureZone/{zon_id}/schedule
    zon_schedule = await get_zon_schedule(auth, zon_id)
    factory_zon_schedule()(zon_schedule)

    #
    # STEP D: PUT /temperatureZone/{zon_id}/schedule
    _ = await put_zon_schedule(auth, zon_id, zon_schedule)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}


async def get_zon_schedule(auth: Auth, zon_id: str) -> TccZonDailySchedulesT:
    """Test GET /temperatureZone/{zon_id}/schedule"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"temperatureZone/{zon_id}/schedule",
    )  # type: ignore[return-value]


async def get_zon_status(auth: Auth, zon_id: str) -> TccZonStatusResponseT:
    """Test GET /temperatureZone/{zon_id}/status"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"temperatureZone/{zon_id}/status",
    )  # type: ignore[return-value]


async def put_zon_heat_setpoint(auth: Auth, zon_id: str) -> TccTaskResponseT:
    """Test PUT /temperatureZone/{zon_id}/heatSetpoint"""

    until = (dt.now(tz=UTC) + td(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={
            "setpointMode": "TemporaryOverride",
            "heatSetpointValue": 20.5,
            "timeUntil": until,
        },
    )

    # for TCSs/zones, TemporaryOverride requires timeUntil (but DHW uses untilTime)
    with pytest.raises(ApiRequestFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"temperatureZone/{zon_id}/heatSetpoint",
            json={
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 20.5,
                "untilTime": until,
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "HeatSetpointChangeTimeUntilNotSet" in exc_info.value.message

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={"setpointMode": "PermanentOverride", "HeatSetpointValue": 20.5},
    )

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={"setpointMode": "FollowSchedule"},  # , "HeatSetpointValue": None},
    )  # type: ignore[return-value]


async def put_zon_schedule(
    auth: Auth, zon_id: str, schedule: TccZonDailySchedulesT
) -> TccTaskResponseT:
    """Test GET /temperatureZone/{zon_id}/schedule"""

    return await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/schedule",
        json=schedule,
    )  # type: ignore[return-value]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_dhw_urls(
    credentials_manager: CredentialsManager,
) -> None:
    """Test DHW URLs"""

    #
    # STEP 0: Create the Auth client, get the TCS config...
    auth = Auth(
        credentials_manager,
        credentials_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info = await get_usr_account(auth)
    usr_locs = await get_usr_locations(auth, usr_info["userId"])

    #
    #
    for loc_config in usr_locs:
        try:
            tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
            if "dhw" in tcs_config:
                break
        except (KeyError, IndexError):
            continue
    else:
        pytest.skip(f"no DHW in {tcs_config}")

    dhw_id = tcs_config["dhw"]["dhwId"]

    #
    # STEP A: GET /domesticHotWater/{dhw_id}/status
    dhw_status = await get_dhw_status(auth, dhw_id)
    factory_dhw_status()(dhw_status)

    #
    # STEP B: PUT /domesticHotWater/{dhw_id}/state
    _ = await put_dhw_state(auth, dhw_id)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}

    #
    # STEP C: GET /domesticHotWater/{dhw_id}/schedule
    dhw_schedule = await get_dhw_schedule(auth, dhw_id)
    factory_dhw_schedule()(dhw_schedule)

    #
    # STEP D: PUT /domesticHotWater/{dhw_id}/schedule
    _ = await put_dhw_schedule(auth, dhw_id, dhw_schedule)
    # factory_zon_status()(task)  # e.g. {'id': '1668279943'}


async def get_dhw_schedule(auth: Auth, dhw_id: str) -> TccDhwDailySchedulesT:
    """Test GET /domesticHotWater/{dhw_id}/schedule"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"domesticHotWater/{dhw_id}/schedule",
    )  # type: ignore[return-value]


async def get_dhw_status(auth: Auth, dhw_id: str) -> TccDhwStatusResponseT:
    """Test GET /domesticHotWater/{dhw_id}/status"""

    return await auth._make_request(
        HTTPMethod.GET,
        f"domesticHotWater/{dhw_id}/status",
    )  # type: ignore[return-value]


async def put_dhw_state(auth: Auth, dhw_id: str) -> TccTaskResponseT:
    """Test PUT /domesticHotWater/{dhw_id}/state"""

    until = (dt.now(tz=UTC) + td(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={
            "mode": "TemporaryOverride",
            "state": "On",
            "untilTime": until,
        },
    )

    # for DHW, TemporaryOverride requires untilTime (but zones use timeUntil)
    with pytest.raises(ApiRequestFailedError) as exc_info:
        await auth._make_request(
            HTTPMethod.PUT,
            f"domesticHotWater/{dhw_id}/state",
            json={
                "mode": "TemporaryOverride",
                "state": "On",
                "timeUntil": until,
            },
        )

    assert exc_info.value.status == HTTPStatus.BAD_REQUEST
    assert "DHWUntilTimeNotSet" in exc_info.value.message

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "PermanentOverride", "state": "Off"},
    )

    return await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "FollowSchedule"},  # , "state": None},
    )  # type: ignore[return-value]


async def put_dhw_schedule(
    auth: Auth, dhw_id: str, schedule: TccDhwDailySchedulesT
) -> TccTaskResponseT:
    """Test GET /domesticHotWater/{dhw_id}/schedule"""

    return await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/schedule",
        json=schedule,
    )  # type: ignore[return-value]
