#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations


from datetime import datetime as dt
from http import HTTPStatus
import pytest
import pytest_asyncio

import evohomeasync2 as evo
from evohomeasync2 import URL_BASE

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
    await client._basic_login()
    _global_oauth_tokens = extract_oauth_tokens(client)

    return client


async def _test_usr_account(
    username: str, password: str, session: None | aiohttp.ClientSession = None
) -> None:
    """Test /userAccount"""

    client = await instantiate_client(username, password, session=session)

    url = "userAccount"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        if exc.status == HTTPStatus.TOO_MANY_REQUESTS:
            pytest.skip("429: Too many requests")
        raise

    response, content = await client._client("PUT", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        # assert content["message"].startswith("The requested resource does not")

    url = "userXxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:  # TODO: move, as is not a test specific to this URL, but a general test
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("The requested resource does not")


async def _test_all_config(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/installationInfo?userId={userId}"""

    client = await instantiate_client(username, password, session=session)
    try:
        _ = await client.user_account()
    except aiohttp.ClientResponseError as exc:
        if exc.status == HTTPStatus.TOO_MANY_REQUESTS:
            pytest.skip("429: Too many requests")

    url = f"location/installationInfo?userId={client.account_info['userId']}"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    url += "&includeTemperatureControlSystems=True"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    response, content = await client._client("PUT", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        # assert content["message"].startswith("The requested resource does not")

    url = "location/installationInfo"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("No HTTP resource was found")

    url = "location/installationInfo?userId=1230000"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 401: Unauthorized
        assert exc.status == HTTPStatus.UNAUTHORIZED
        # assert content["message"].startswith("You are not allowed")

    url = "location/installationInfo?userId=xxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 400: Bad Request
        assert exc.status == HTTPStatus.BAD_REQUEST
        # assert content["message"].startswith("Request was bad formatted")

    url = "location/installationInfo?xxxxXx=xxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        # assert content["message"].startswith("No HTTP resource was found")


async def _test_loc_status(
    username: str,
    password: str,
    session: None | aiohttp.ClientSession = None,
) -> None:
    """Test location/{locationId}/status"""

    client = await instantiate_client(username, password, session=session)
    try:
        _ = await client.user_account()
    except aiohttp.ClientResponseError as exc:
        if exc.status == HTTPStatus.TOO_MANY_REQUESTS:
            pytest.skip("429: Too many requests")

    _ = await client._installation(refresh_status=False)
    loc = client.locations[0]

    url = f"location/{loc.locationId}/status"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    url += "?includeTemperatureControlSystems=True"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    response.raise_for_status()

    response, content = await client._client("PUT", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 405: Method Not Allowed
        assert exc.status == HTTPStatus.METHOD_NOT_ALLOWED
        # assert content["message"].startswith("The requested resource does not")

    url = f"location/{loc.locationId}"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert response.content_type == "text/html"

    url = "location/1230000/status"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 401: Unauthorized
        assert exc.status == HTTPStatus.UNAUTHORIZED
        # assert content["message"].startswith("You are not allowed")

    url = "location/xxxxxxx/status"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 400: Bad Request
        assert exc.status == HTTPStatus.BAD_REQUEST
        # assert content["message"].startswith("Request was bad formatted")

    url = f"location/{loc.locationId}/xxxxxxx"
    response, content = await client._client("GET", f"{URL_BASE}/{url}")
    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:  # 404: Not Found
        assert exc.status == HTTPStatus.NOT_FOUND
        assert response.content_type == "text/html"


# TODO: test_oauth_token(


@pytest.mark.asyncio
async def test_get_usr_account(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /userAccount"""

    await _test_usr_account(*credentials, session=session)


@pytest.mark.asyncio
async def test_get_all_config(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /location/installationInfo"""

    await _test_all_config(*credentials, session=session)


@pytest.mark.asyncio
async def test_get_loc_status(
    credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test location/{locationId}/status"""

    await _test_loc_status(*credentials, session=session)


# TODO: test_put_dhw_state(
# TODO: test_get_dhw_status(
# TODO: test_get_schedule(
# TODO: test_put_schedule(
# TODO: test_set_tcs_mode(
# TODO: test_put_zon_mode(
# TODO: test_get_zon_status(
