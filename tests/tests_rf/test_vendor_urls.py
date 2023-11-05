#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations


from datetime import datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
import pytest
import pytest_asyncio

import evohomeasync2 as evo
from evohomeasync2.const import API_STRFTIME, SystemMode, ZoneMode
from evohomeasync2.schema import (
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_GET_SCHEDULE,
    SCH_TCS_STATUS,
    SCH_ZONE_STATUS,
)
from evohomeasync2.schema.const import (
    SZ_DAILY_SCHEDULES,
    SZ_HEAT_SETPOINT,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_IS_AVAILABLE,
    SZ_IS_PERMANENT,
    SZ_MODE,
    SZ_PERMANENT,
    SZ_SYSTEM_MODE,
    SZ_SETPOINT_MODE,
    SZ_SWITCHPOINTS,
    SZ_TEMPERATURE,
    SZ_TIME_UNTIL,
)
from evohomeasync2.schema.schedule import convert_to_put_schedule

from . import _DEBUG_USE_MOCK_AIOHTTP
from .helpers import aiohttp, extract_oauth_tokens  # aiohttp may be mocked
from .helpers import user_credentials as _user_credentials
from .helpers import client_session as _client_session
from .helpers import should_work, should_fail


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


async def _test_usr_account(
    username: str, password: str, session: aiohttp.ClientSession | None = None
) -> None:
    """Test /userAccount"""

    client = await instantiate_client(username, password, session=session)
    #

    url = "userAccount"
    _ = await should_work(client, HTTPMethod.GET, url, schema=SCH_USER_ACCOUNT)
    _ = await should_fail(
        client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "userXxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    _ = await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_all_config(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> None:
    """Test /location/installationInfo?userId={userId}"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    #

    url = f"location/installationInfo?userId={client.account_info['userId']}"
    await should_work(client, HTTPMethod.GET, url)

    url += "&includeTemperatureControlSystems=True"
    _ = await should_work(client, HTTPMethod.GET, url, schema=SCH_FULL_CONFIG)
    _ = await should_fail(
        client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = "location/installationInfo"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)

    url = "location/installationInfo?userId=1230000"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/installationInfo?userId=xxxxxxx"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)


async def _test_loc_status(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> None:
    """Test /location/{locationId}/status"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    _ = await client._installation(refresh_status=False)
    loc = client.locations[0]
    #

    url = f"location/{loc.locationId}/status"
    _ = await should_work(client, HTTPMethod.GET, url)

    url += "?includeTemperatureControlSystems=True"
    _ = await should_work(client, HTTPMethod.GET, url, schema=SCH_LOCN_STATUS)
    _ = await should_fail(
        client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = f"location/{loc.locationId}"
    await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    url = "location/1230000/status"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/xxxxxxx/status"
    _ = await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = f"location/{loc.locationId}/xxxxxxx"
    _ = await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_tcs_mode(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> None:
    """Test /temperatureControlSystem/{systemId}/mode"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    _ = await client._installation(refresh_status=False)

    tcs: evo.ControlSystem

    if not (tcs := client.locations[0]._gateways[0]._control_systems[0]):
        pytest.skip("No available zones found")

    _ = await tcs._refresh_status()
    old_mode = tcs.systemModeStatus

    url = f"{tcs.TYPE}/{tcs._id}/status"
    _ = await should_work(client, HTTPMethod.GET, url, schema=SCH_TCS_STATUS)

    url = f"{tcs.TYPE}/{tcs._id}/mode"
    _ = await should_fail(
        client, HTTPMethod.GET, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )
    _ = await should_fail(
        client, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.BAD_REQUEST
    )

    old_mode[SZ_SYSTEM_MODE] = old_mode.pop(SZ_MODE)
    old_mode[SZ_PERMANENT] = old_mode.pop(SZ_IS_PERMANENT)

    assert SystemMode.AUTO in [m[SZ_SYSTEM_MODE] for m in tcs.allowedSystemModes]
    new_mode = {
        SZ_SYSTEM_MODE: SystemMode.AUTO,
        SZ_PERMANENT: True,
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=new_mode)

    assert SystemMode.AWAY in [m[SZ_SYSTEM_MODE] for m in tcs.allowedSystemModes]
    new_mode = {
        SZ_SYSTEM_MODE: SystemMode.AWAY,
        SZ_PERMANENT: True,
        SZ_TIME_UNTIL: (dt.now() + td(hours=1)).strftime(API_STRFTIME),
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=new_mode)

    _ = await should_work(client, HTTPMethod.PUT, url, json=old_mode)

    url = f"{tcs.TYPE}/1234567/mode"
    _ = await should_fail(
        client, HTTPMethod.PUT, url, json=old_mode, status=HTTPStatus.UNAUTHORIZED
    )

    url = f"{tcs.TYPE}/{tcs._id}/systemMode"
    _ = await should_fail(
        client,
        HTTPMethod.PUT,
        url,
        json=old_mode,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    pass


async def _test_zone_mode(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> None:
    """Test /temperatureZone/{zoneId}/heatSetpoint"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    _ = await client._installation(refresh_status=False)

    for zone in client.locations[0]._gateways[0]._control_systems[0]._zones:
        _ = await zone._refresh_status()
        if zone.temperatureStatus[SZ_IS_AVAILABLE]:
            break
    else:
        pytest.skip("No available zones found")
    #

    url = f"{zone.TYPE}/{zone._id}/status"
    _ = await should_work(client, HTTPMethod.GET, url, schema=SCH_ZONE_STATUS)

    url = f"{zone.TYPE}/{zone._id}/heatSetpoint"

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: zone.temperatureStatus[SZ_TEMPERATURE],
        # SZ_TIME_UNTIL: None,
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 99,
        SZ_TIME_UNTIL: None,
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: "xxxxxxx",
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    _ = await should_fail(
        client, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )

    heat_setpoint = {
        SZ_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
        SZ_HEAT_SETPOINT_VALUE: 0.0,
        SZ_TIME_UNTIL: None,
    }
    _ = await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)


# TODO: Test sending bad schedule
# TODO: Try with/without convert_to_put_schedule()
async def _test_schedule(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
) -> None:
    """Test /{x.TYPE}/{x._id}/schedule (of a zone)"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    _ = await client.installation()
    zone = client.locations[0]._gateways[0]._control_systems[0]._zones[0]
    #

    url = f"{zone.TYPE}/{zone._id}/schedule"
    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)

    temp = schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT]

    schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] = temp + 1
    _ = await should_work(
        client, HTTPMethod.PUT, url, json=convert_to_put_schedule(schedule)
    )

    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)
    assert (
        schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT]
        == temp + 1
    )

    schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] = temp
    _ = await should_work(
        client, HTTPMethod.PUT, url, json=convert_to_put_schedule(schedule)
    )

    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_GET_SCHEDULE)
    assert schedule[SZ_DAILY_SCHEDULES][0][SZ_SWITCHPOINTS][0][SZ_HEAT_SETPOINT] == temp

    _ = await should_fail(
        client, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )  # NOTE: json=None


@pytest.mark.asyncio
async def test_usr_account(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /userAccount"""

    try:
        await _test_usr_account(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_all_config(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/installationInfo"""

    try:
        await _test_all_config(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_loc_status(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/{locationId}/status"""

    try:
        await _test_loc_status(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_tcs_mode(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /temperatureControlSystem/{systemId}/mode"""

    try:
        await _test_tcs_mode(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")
    except NotImplementedError:  # TODO: implement
        if not _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@pytest.mark.asyncio
async def test_zone_mode(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /temperatureZone/{zoneId}/heatSetpoint"""

    try:
        await _test_zone_mode(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")
    except NotImplementedError:  # TODO: implement
        if not _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Mocked server API not implemented")


@pytest.mark.asyncio
async def test_schedule(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /{x.TYPE}/{x_id}/schedule"""

    try:
        await _test_schedule(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        if _DEBUG_USE_MOCK_AIOHTTP:
            raise
        pytest.skip("Unable to authenticate")


# TODO: test_oauth_token(
# TODO: test_put_dhw_state(
# TODO: test_get_dhw_status(
# TODO: test_set_tcs_mode(
# TODO: test_get_zon_status(
