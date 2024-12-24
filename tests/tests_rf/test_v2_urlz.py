"""evohome-async - invoke every known vendor RESful API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from typing import TYPE_CHECKING

import pytest

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
    from evohomeasync2.schemas.schedule import TccDailySchedulesZoneT
    from evohomeasync2.schemas.status import (
        TccDhwStatusResponseT,
        TccLocStatusResponseT,
        TccTcsStatusResponseT,
        TccZonStatusResponseT,
    )
    from tests.conftest import TokenManager


#######################################################################################


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_tcs_urls(
    cache_manager: TokenManager,
) -> None:
    """Test Location, Gateway and TCS URLs."""

    await cache_manager.load_from_cache()

    #
    # STEP 0: Create the Auth client
    auth = Auth(
        cache_manager.get_access_token,
        cache_manager.websession,
        logger=logging.getLogger(__name__),
    )

    #
    # STEP 1: GET /userAccount
    usr_info: TccUsrAccountResponseT = await auth._make_request(
        HTTPMethod.GET,
        "userAccount",
    )  # type: ignore[assignment]

    factory_user_account()(usr_info)

    #
    # STEP 2: GET /location/installationInfo?userId={user_id}
    usr_id = usr_info["userId"]

    usr_installs: list[TccLocConfigResponseT] = await auth._make_request(
        HTTPMethod.GET,
        f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True",
    )  # type: ignore[assignment]

    factory_user_locations_installation_info()(usr_installs)

    #
    # STEP A: GET /location/{loc_id}/installationInfo
    loc_id = usr_installs[0]["locationInfo"]["locationId"]

    loc_config: TccLocConfigResponseT = await auth._make_request(
        HTTPMethod.GET,
        f"location/{loc_id}/installationInfo?includeTemperatureControlSystems=True",
    )  # type: ignore[assignment]

    factory_location_installation_info()(loc_config)

    #
    # STEP B: GET /location/{loc_id}/status
    loc_status: TccLocStatusResponseT = await auth._make_request(
        HTTPMethod.GET,
        f"location/{loc_id}/status?includeTemperatureControlSystems=True",
    )  # type: ignore[assignment]

    factory_loc_status()(loc_status)

    #
    # STEP C: GET /temperatureControlSystem/{tcs_id}/status
    tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
    tcs_id = tcs_config["systemId"]

    tcs_status: TccTcsStatusResponseT = await auth._make_request(
        HTTPMethod.GET,
        f"temperatureControlSystem/{tcs_id}/status",
    )  # type: ignore[assignment]

    factory_tcs_status()(tcs_status)

    #
    # STEP D: PUT /temperatureControlSystem/{tcs_id}/mode
    _: TccTaskResponseT = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={
            "SystemMode": "Away",
            "Permanent": False,
            "TimeUntil": (dt.now(tz=UTC) + td(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )  # type: ignore[assignment]

    # factory_task()(task)  # {'id': '1668279943'}

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureControlSystem/{tcs_id}/mode",
        json={"SystemMode": "Auto", "Permanent": True},
    )  # type: ignore[assignment]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_zon_urls(
    cache_manager: TokenManager,
) -> None:
    """Test Zone URLs"""

    await cache_manager.load_from_cache()

    #
    # STEP 0: Create the Auth client, get the TCS config
    auth = Auth(
        cache_manager.get_access_token,
        cache_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info: TccUsrAccountResponseT = await auth._make_request(
        HTTPMethod.GET,
        "userAccount",
    )  # type: ignore[assignment]
    usr_id = usr_info["userId"]

    usr_installs: list[TccLocConfigResponseT] = await auth._make_request(
        HTTPMethod.GET,
        f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True",
    )  # type: ignore[assignment]
    tcs_config = usr_installs[0]["gateways"][0]["temperatureControlSystems"][0]

    #
    # STEP A: GET /temperatureZone/{zon_id}/status
    zon_id = tcs_config["zones"][0]["zoneId"]

    zon_status: TccZonStatusResponseT = await auth._make_request(
        HTTPMethod.GET,
        f"temperatureZone/{zon_id}/status",
    )  # type: ignore[assignment]

    factory_zon_status()(zon_status)

    #
    # STEP B: PUT /temperatureZone/{zon_id}/heatSetpoint
    _: TccTaskResponseT = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={
            "setpointMode": "TemporaryOverride",
            "heatSetpointValue": 20.5,
            "timeUntil": (dt.now(tz=UTC) + td(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )  # type: ignore[assignment]

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={"setpointMode": "PermanentOverride", "HeatSetpointValue": 20.5},
    )  # type: ignore[assignment]

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/heatSetpoint",
        json={"setpointMode": "FollowSchedule"},  # , "HeatSetpointValue": None},
    )  # type: ignore[assignment]

    #
    # STEP C: GET /temperatureZone/{zon_id}/schedule
    zon_schedule: TccDailySchedulesZoneT = await auth._make_request(
        HTTPMethod.GET,
        f"temperatureZone/{zon_id}/schedule",
    )  # type: ignore[assignment]

    factory_zon_schedule()(zon_schedule)

    #
    # STEP D: PUT /temperatureZone/{zon_id}/schedule
    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"temperatureZone/{zon_id}/schedule",
        json=zon_schedule,
    )  # type: ignore[assignment]


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_dhw_urls(
    cache_manager: TokenManager,
) -> None:
    """Test DHW URLs"""

    await cache_manager.load_from_cache()

    #
    # STEP 0: Create the Auth client, get the TCS config
    auth = Auth(
        cache_manager.get_access_token,
        cache_manager.websession,
        logger=logging.getLogger(__name__),
    )

    usr_info: TccUsrAccountResponseT = await auth._make_request(
        HTTPMethod.GET,
        "userAccount",
    )  # type: ignore[assignment]
    usr_id = usr_info["userId"]

    usr_installs: list[TccLocConfigResponseT] = await auth._make_request(
        HTTPMethod.GET,
        f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True",
    )  # type: ignore[assignment]
    for loc_config in usr_installs:
        tcs_config = loc_config["gateways"][0]["temperatureControlSystems"][0]
        if "dhw" in tcs_config:
            break
    else:
        pytest.skip(f"no DHW in {tcs_config}")

    #
    # STEP A: GET /domesticHotWater/{dhw_id}/status
    dhw_id = tcs_config["dhw"]["dhwId"]

    dhw_status: TccDhwStatusResponseT = await auth._make_request(
        HTTPMethod.GET,
        f"domesticHotWater/{dhw_id}/status",
    )  # type: ignore[assignment]

    factory_dhw_status()(dhw_status)

    #
    # STEP B: PUT /domesticHotWater/{dhw_id}/state
    _: TccTaskResponseT = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={
            "mode": "TemporaryOverride",
            "state": "On",
            "untilTime": (dt.now(tz=UTC) + td(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )  # type: ignore[assignment]

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "PermanentOverride", "state": "Off"},
    )  # type: ignore[assignment]

    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/state",
        json={"mode": "FollowSchedule"},  # , "state": None},
    )  # type: ignore[assignment]

    #
    # STEP C: GET /domesticHotWater/{dhw_id}/schedule
    dhw_schedule: TccDailySchedulesZoneT = await auth._make_request(
        HTTPMethod.GET,
        f"domesticHotWater/{dhw_id}/schedule",
    )  # type: ignore[assignment]

    factory_dhw_schedule()(dhw_schedule)

    #
    # STEP D: PUT /domesticHotWater/{dhw_id}/schedule
    _ = await auth._make_request(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw_id}/schedule",
        json=dhw_schedule,
    )  # type: ignore[assignment]
