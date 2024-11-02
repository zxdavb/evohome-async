#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs)."""

from __future__ import annotations

from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohomeasync2.const import API_STRFTIME, SystemMode, ZoneMode
from evohomeasync2.schema import (
    SCH_FULL_CONFIG,
    SCH_GET_SCHEDULE,
    SCH_LOCN_STATUS,
    SCH_TCS_STATUS,
    SCH_USER_ACCOUNT,
    SCH_ZONE_STATUS,
)
from evohomeasync2.schema.const import (
    SZ_DAILY_SCHEDULES,
    SZ_HEAT_SETPOINT,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_IS_PERMANENT,
    SZ_MODE,
    SZ_PERMANENT,
    SZ_SETPOINT_MODE,
    SZ_SWITCHPOINTS,
    SZ_SYSTEM_MODE,
    SZ_TIME_UNTIL,
    SZ_USER_ID,
)
from evohomeasync2.schema.schedule import convert_to_put_schedule

from . import faked_server as faked
from .conftest import _DBG_USE_REAL_AIOHTTP, skipif_auth_failed
from .helpers import should_fail, should_work

if TYPE_CHECKING:
    from evohomeasync2.schema import _EvoDictT


#######################################################################################


async def _test_usr_account(evo: evo2.EvohomeClientNew) -> None:
    """Test /userAccount"""

    url = "userAccount"
    _ = await should_work(evo, HTTPMethod.GET, url, schema=SCH_USER_ACCOUNT)
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "userXxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    _ = await should_fail(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_all_config(evo: evo2.EvohomeClientNew) -> None:
    """Test /location/installationInfo?userId={user_id}"""

    _ = await evo.update()
    #

    url = f"location/installationInfo?userId={evo._user_info[SZ_USER_ID]}"
    await should_work(evo, HTTPMethod.GET, url)

    url += "&includeTemperatureControlSystems=True"
    _ = await should_work(evo, HTTPMethod.GET, url, schema=SCH_FULL_CONFIG)
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "location/installationInfo"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)

    url = "location/installationInfo?userId=1230000"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/installationInfo?userId=xxxxxxx"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)


async def _test_loc_status(evo: evo2.EvohomeClientNew) -> None:
    """Test /location/{loc.id}/status"""

    _ = await evo.update(dont_update_status=True)

    loc = evo.locations[0]
    #

    url = f"location/{loc.id}/status"
    _ = await should_work(evo, HTTPMethod.GET, url)

    url += "?includeTemperatureControlSystems=True"
    _ = await should_work(evo, HTTPMethod.GET, url, schema=SCH_LOCN_STATUS)
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = f"location/{loc.id}"
    await should_fail(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    url = "location/1230000/status"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/xxxxxxx/status"
    _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = f"location/{loc.id}/xxxxxxx"
    _ = await should_fail(
        evo,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_tcs_mode(evo: evo2.EvohomeClientNew) -> None:
    """Test /temperatureControlSystem/{tcs.id}/mode"""

    _ = await evo.update(dont_update_status=True)

    tcs: evo2.ControlSystem

    if not (tcs := evo.locations[0].gateways[0].control_systems[0]):
        pytest.skip("No available zones found")

    _ = await tcs.location.update()
    old_mode: _EvoDictT = tcs.system_mode_status  # type: ignore[assignment]

    url = f"{tcs.TYPE}/{tcs.id}/status"
    _ = await should_work(evo, HTTPMethod.GET, url, schema=SCH_TCS_STATUS)

    url = f"{tcs.TYPE}/{tcs.id}/mode"
    _ = await should_fail(
        evo, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.BAD_REQUEST
    )

    old_mode[SZ_SYSTEM_MODE] = old_mode.pop(SZ_MODE)
    old_mode[SZ_PERMANENT] = old_mode.pop(SZ_IS_PERMANENT)

    assert SystemMode.AUTO in [m[SZ_SYSTEM_MODE] for m in tcs.allowed_system_modes]
    new_mode: _EvoDictT = {
        SZ_SYSTEM_MODE: SystemMode.AUTO,
        SZ_PERMANENT: True,
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=new_mode)

    assert SystemMode.AWAY in [m[SZ_SYSTEM_MODE] for m in tcs.allowed_system_modes]
    new_mode = {
        SZ_SYSTEM_MODE: SystemMode.AWAY,
        SZ_PERMANENT: True,
        SZ_TIME_UNTIL: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=new_mode)

    _ = await should_work(evo, HTTPMethod.PUT, url, json=old_mode)

    url = f"{tcs.TYPE}/1234567/mode"
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )

    url = f"{tcs.TYPE}/{tcs.id}/systemMode"
    _ = await should_fail(
        evo,
        HTTPMethod.PUT,
        url,
        json=old_mode,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    pass


async def _test_zone_mode(evo: evo2.EvohomeClientNew) -> None:
    """Test /temperatureZone/{zone.id}/heatSetpoint"""

    _ = await evo.update()

    for zone in evo.locations[0].gateways[0].control_systems[0].zones:
        if zone.temperature is None:
            break
    else:
        pytest.skip("No available zones found")
    #

    url = f"{zone.TYPE}/{zone.id}/status"
    _ = await should_work(evo, HTTPMethod.GET, url, schema=SCH_ZONE_STATUS)

    url = f"{zone.TYPE}/{zone.id}/heatSetpoint"

    heat_setpoint: dict[str, float | str | None] = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: zone.temperature,
        # SZ_TIME_UNTIL: None,
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 99,
        SZ_TIME_UNTIL: None,
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: "xxxxxxx",
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_fail(
        evo, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
        SZ_HEAT_SETPOINT_VALUE: 0.0,
        SZ_TIME_UNTIL: None,
    }
    _ = await should_work(evo, HTTPMethod.PUT, url, json=heat_setpoint)


# TODO: Test sending bad schedule
# TODO: Try with/without convert_to_put_schedule()
async def _test_schedule(evo: evo2.EvohomeClientNew) -> None:
    """Test /{x.TYPE}/{x.id}/schedule (of a zone)"""

    _ = await evo.update()

    zone = evo.locations[0].gateways[0].control_systems[0].zones[0]
    #

    if zone.id == faked.GHOST_ZONE_ID:
        url = f"{zone.TYPE}/{faked.GHOST_ZONE_ID}/schedule"
        _ = await should_fail(evo, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)
        return

    url = f"{zone.TYPE}/{zone.id}/schedule"
    schedule = await should_work(evo, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)

    temp = schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT]  # type: ignore[call-overload]

    schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] = temp + 1  # type: ignore[call-overload,operator]
    _ = await should_work(
        evo,
        HTTPMethod.PUT,
        url,
        json=convert_to_put_schedule(schedule),  # type: ignore[arg-type]
    )

    schedule = await should_work(evo, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)
    assert (
        schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT]  # type: ignore[call-overload]
        == temp + 1  # type: ignore[operator]
    )

    schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] = temp  # type: ignore[call-overload]
    _ = await should_work(
        evo,
        HTTPMethod.PUT,
        url,
        json=convert_to_put_schedule(schedule),  # type: ignore[arg-type]
    )

    schedule = await should_work(evo, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)
    assert schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] == temp  # type: ignore[call-overload]

    _ = await should_fail(
        evo, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )  # NOTE: json=None


#######################################################################################


@skipif_auth_failed
async def test_usr_account(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /userAccount"""

    try:
        await _test_usr_account(evohome_v2)

    except evo2.AuthenticationFailedError:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@skipif_auth_failed
async def test_all_config(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /location/installationInfo"""

    await _test_all_config(evohome_v2)


@skipif_auth_failed
async def test_loc_status(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /location/{loc.id}/status"""

    await _test_loc_status(evohome_v2)


@skipif_auth_failed
async def test_tcs_mode(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /temperatureControlSystem/{tcs.id}/mode"""

    try:
        await _test_tcs_mode(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_zone_mode(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /temperatureZone/{zone.id}/heatSetpoint"""

    try:
        await _test_zone_mode(evohome_v2)

    except NotImplementedError:  # TODO: implement
        if _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@skipif_auth_failed
async def test_schedule(evohome_v2: evo2.EvohomeClientNew) -> None:
    """Test /{x.TYPE}/{x.id}/schedule"""

    await _test_schedule(evohome_v2)


# TODO: test_oauth_token(
# TODO: test_put_dhw_state(
# TODO: test_get_dhw_status(
# TODO: test_set_tcs_mode(
# TODO: test_get_zon_status(
