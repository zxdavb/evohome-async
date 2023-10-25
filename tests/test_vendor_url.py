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
from evohomeasync2 import exceptions
from evohomeasync2.const import URL_BASE
from evohomeasync2.schema import (
    SCH_FULL_CONFIG,
    SCH_LOCN_STATUS,
    SCH_USER_ACCOUNT,
    SCH_ZONE_STATUS,
)
from evohomeasync2.schema.const import (
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
    try:
        yield _session()
    finally:
        await _session().close()


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


async def _test_usr_account(
    username: str, password: str, session: None | aiohttp.ClientSession = None
) -> None:
    """Test /userAccount"""

    response: aiohttp.ClientResponse

    client = await instantiate_client(username, password, session=session)

    # Test 1
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/userAccount"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
    assert _DISABLE_STRICT_ASSERTS or SCH_USER_ACCOUNT(content)

    # Test 2
    try:
        response, content = await client._broker._client(
            HTTPMethod.PUT, f"{URL_BASE}/userAccount"
        )
    except exceptions.FailedRequest as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("The requested resource does not")

    # Test 3
    try:  # TODO: move, as is not a test specific to this URL, but a general test
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/userXxxxxxx"
        )
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert _DISABLE_STRICT_ASSERTS or exc.status == HTTPStatus.NOT_FOUND
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("The requested resource does not")


async def _test_all_config(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/installationInfo?userId={userId}"""

    response: aiohttp.ClientResponse

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()

    # Test 1A
    url = f"location/installationInfo?userId={client.account_info['userId']}"
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/{url}"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"

    # Test 1B
    url += "&includeTemperatureControlSystems=True"
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/{url}"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
    assert _DISABLE_STRICT_ASSERTS or SCH_FULL_CONFIG(content)

    # Test 2
    try:
        response, content = await client._broker._client(
            HTTPMethod.PUT, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("The requested resource does not")

    # Test 2
    url = "location/installationInfo"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("No HTTP resource was found")

    # Test 2
    url = "location/installationInfo?userId=1230000"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 401: Unauthorized
        assert exc.status == HTTPStatus.UNAUTHORIZED
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("You are not allowed")

    # Test 2
    url = "location/installationInfo?userId=xxxxxxx"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 400: Bad Request
        assert exc.status == HTTPStatus.BAD_REQUEST
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("Request was bad formatted")

    # Test 2
    url = "location/installationInfo?xxxxXx=xxxxxxx"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("No HTTP resource was found")


async def _test_loc_status(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

    response: aiohttp.ClientResponse

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    _ = await client._installation(refresh_status=False)

    loc = client.locations[0]

    # Test 1A
    url = f"location/{loc.locationId}/status"
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/{url}"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"

    # Test 1B
    url += "?includeTemperatureControlSystems=True"
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/{url}"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
    assert _DISABLE_STRICT_ASSERTS or SCH_LOCN_STATUS(content)

    # Test 2
    try:
        response, content = await client._broker._client(
            HTTPMethod.PUT, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("The requested resource does not")

    # Test 2
    url = f"location/{loc.locationId}"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "text/html"

    # Test 2
    url = "location/1230000/status"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 401: Unauthorized
        assert exc.status == HTTPStatus.UNAUTHORIZED
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("You are not allowed")

    # Test 2
    url = "location/xxxxxxx/status"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 400: Bad Request
        assert exc.status == HTTPStatus.BAD_REQUEST
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("Request was bad formatted")

    # Test 2
    url = f"location/{loc.locationId}/xxxxxxx"
    try:
        response, content = await client._broker._client(
            HTTPMethod.GET, f"{URL_BASE}/{url}"
        )
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "text/html"


async def _test_zone_mode(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

    response: aiohttp.ClientResponse

    client = await instantiate_client(username, password, session=session)
    _ = await client.user_account()
    _ = await client._installation(refresh_status=False)

    for zone in client.locations[0]._gateways[0]._control_systems[0]._zones:
        _ = await zone._refresh_status()
        if zone.temperatureStatus[SZ_IS_AVAILABLE]:
            break

    url = f"{zone._type}/{zone._id}/status"
    response, content = await client._broker._client(
        HTTPMethod.GET, f"{URL_BASE}/{url}"
    )
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
    assert _DISABLE_STRICT_ASSERTS or SCH_ZONE_STATUS(content)

    return

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: zone.temperatureStatus[SZ_TEMPERATURE],
        SZ_TIME_UNTIL: None,
    }

    url = f"{zone._type}/{zone._id}/heatSetpoint"
    response, content = await client._broker.put(
        url, json=heat_setpoint
    )
    response.raise_for_status()  # content = {'id': '824948817'}
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 99,
        SZ_TIME_UNTIL: None,
    }

    url = f"{zone._type}/{zone._id}/heatSetpoint"
    response, content = await client._broker.put(
        url, json=heat_setpoint
    )
    response.raise_for_status()
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"

    heat_setpoint = {
        SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }

    url = f"{zone._type}/{zone._id}/heatSetpoint"
    response, content = await client._broker.put(
        url, json=heat_setpoint
    )
    response.raise_for_status()
    assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"

    heat_setpoint = {
        SZ_SETPOINT_MODE: "xxxxxxx",
        SZ_HEAT_SETPOINT_VALUE: 19.5,
    }

    url = f"{zone._type}/{zone._id}/heatSetpoint"
    response, content = await client._client._broker.put(
        url, json=heat_setpoint
    )
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == HTTPStatus.BAD_REQUEST
        assert _DISABLE_STRICT_ASSERTS or response.content_type == "application/json"
        # assert content["message"].startswith("Error converting value")


@pytest.mark.asyncio
async def test_get_usr_account(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /userAccount"""

    try:
        await _test_usr_account(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_get_all_config(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/installationInfo"""

    try:
        await _test_all_config(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_get_loc_status(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    try:
        await _test_loc_status(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


# TODO: test_put_zon_mode(
@pytest.mark.asyncio
async def test_put_zone_mode(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    try:
        await _test_zone_mode(*credentials, session=session)
    except evo.AuthenticationError:
        pytest.skip("Unable to authenticate")


# TODO: test_oauth_token(
# TODO: test_put_dhw_state(
# TODO: test_get_dhw_status(
# TODO: test_get_schedule(
# TODO: test_put_schedule(
# TODO: test_set_tcs_mode(
# TODO: test_put_zon_mode(
# TODO: test_get_zon_status(
