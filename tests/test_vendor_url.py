#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations


from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
import pytest
import pytest_asyncio

import evohomeasync2 as evo
from evohomeasync2.broker import vol
from evohomeasync2.const import URL_BASE
from evohomeasync2.schema import (
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_SCHEDULE,
    SCH_ZONE_STATUS,
)
from evohomeasync2.schema.const import (
    SZ_FOLLOW_SCHEDULE,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_IS_AVAILABLE,
    SZ_PERMANENT_OVERRIDE,
    SZ_SETPOINT_MODE,
    SZ_TEMPERATURE,
    SZ_TIME_UNTIL,
)

from . import _DISABLE_STRICT_ASSERTS
from .helpers import aiohttp, extract_oauth_tokens  # aiohttp may be mocked
from .helpers import credentials as _credentials
from .helpers import session as _session


_global_oauth_tokens: tuple[str, str, dt] = None, None, None


@pytest.fixture()
def credentials():
    return _credentials()


@pytest_asyncio.fixture
async def session():
    session = _session()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("evohomeasync2.broker.aiohttp", aiohttp)


async def instantiate_client(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
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


async def should_work(
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response, content = await client._broker._client(
        method, f"{URL_BASE}/{url}", json=json
    )

    response.raise_for_status()

    assert response.content_type == content_type

    if schema:
        return schema(content)
    return content


async def should_fail(
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> None:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response, content = await client._broker._client(
        method, f"{URL_BASE}/{url}", json=json
    )

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False

    if _DISABLE_STRICT_ASSERTS:
        return

    assert response.content_type == content_type
    if isinstance(content, dict):
        assert "message" in content
    elif isinstance(content, list):
        assert "message" in content[0]


async def _test_usr_account(
    username: str, password: str, session: None | aiohttp.ClientSession = None
) -> None:
    """Test /userAccount"""

    client = await instantiate_client(username, password, session=session)
    #

    url = "userAccount"
    await should_work(client, HTTPMethod.GET, url, schema=SCH_USER_ACCOUNT)
    await should_fail(client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED)

    url = "userXxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_all_config(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/installationInfo?userId={userId}"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    #

    url = f"location/installationInfo?userId={client.account_info['userId']}"
    await should_work(client, HTTPMethod.GET, url)

    url += "&includeTemperatureControlSystems=True"
    await should_work(client, HTTPMethod.GET, url, schema=SCH_FULL_CONFIG)
    await should_fail(client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED)

    url = "location/installationInfo"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)

    url = "location/installationInfo?userId=1230000"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/installationInfo?userId=xxxxxxx"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.NOT_FOUND)


async def _test_loc_status(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    _ = await client._installation(refresh_status=False)
    loc = client.locations[0]
    #

    url = f"location/{loc.locationId}/status"
    await should_work(client, HTTPMethod.GET, url)

    url += "?includeTemperatureControlSystems=True"
    await should_work(client, HTTPMethod.GET, url, schema=SCH_LOCN_STATUS)
    await should_fail(client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED)

    url = f"location/{loc.locationId}"
    await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )

    url = "location/1230000/status"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.UNAUTHORIZED)

    url = "location/xxxxxxx/status"
    await should_fail(client, HTTPMethod.GET, url, status=HTTPStatus.BAD_REQUEST)

    url = f"location/{loc.locationId}/xxxxxxx"
    await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_zone_mode(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

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

    url = f"{zone._type}/{zone._id}/status"
    await should_work(client, HTTPMethod.GET, url, schema=SCH_ZONE_STATUS)

    url = f"{zone._type}/{zone._id}/heatSetpoint"

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: zone.temperatureStatus[SZ_TEMPERATURE],
        SZ_TIME_UNTIL: None,
    }
    await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 99,
        SZ_TIME_UNTIL: None,
    }
    await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)

    heat_setpoint = {
        SZ_SETPOINT_MODE: "xxxxxxx",
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }
    await should_fail(
        client, HTTPMethod.PUT, url, json=heat_setpoint, status=HTTPStatus.BAD_REQUEST
    )

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_FOLLOW_SCHEDULE,
        SZ_HEAT_SETPOINT_VALUE: 0.0,
        SZ_TIME_UNTIL: None,
    }
    await should_work(client, HTTPMethod.PUT, url, json=heat_setpoint)


async def _test_schedule(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    _ = await client.installation()
    zone = client.locations[0]._gateways[0]._control_systems[0]._zones[0]
    #

    url = f"{zone._type}/{zone._id}/schedule"
    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_SCHEDULE)

    temp = schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"]

    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp + 1
    await should_work(client, HTTPMethod.PUT, url, json=schedule)

    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_SCHEDULE)
    assert schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] == temp + 1

    schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] = temp
    await should_work(client, HTTPMethod.PUT, url, json=schedule)

    schedule = await should_work(client, HTTPMethod.GET, url, schema=SCH_SCHEDULE)
    assert schedule["dailySchedules"][0]["switchpoints"][0]["heatSetpoint"] == temp

    await should_fail(
        client, HTTPMethod.PUT, url, json=None, status=HTTPStatus.BAD_REQUEST
    )  # NOTE: json=None


@pytest.mark.asyncio
async def test_usr_account(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /userAccount"""

    try:
        await _test_usr_account(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_all_config(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/installationInfo"""

    try:
        await _test_all_config(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_loc_status(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    try:
        await _test_loc_status(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_zone_mode(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    try:
        await _test_zone_mode(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_schedule(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    try:
        await _test_schedule(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


# TODO: test_oauth_token(
# TODO: test_put_dhw_state(
# TODO: test_get_dhw_status(
# TODO: test_set_tcs_mode(
# TODO: test_get_zon_status(
