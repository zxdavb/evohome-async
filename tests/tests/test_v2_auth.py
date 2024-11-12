#!/usr/bin/env python3
"""evohome-async - validate the v2 API token manager."""

from __future__ import annotations

import uuid
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses

from evohomeasync2 import exceptions as exc
from tests.const import HEADERS_AUTH_V1 as HEADERS_AUTH, URL_AUTH_V1 as URL_AUTH

if TYPE_CHECKING:
    from pathlib import Path

    from freezegun.api import FrozenDateTimeFactory

    from tests.conftest import CacheManager


async def test_get_auth_token(
    credentials: tuple[str, str],
    cache_manager: CacheManager,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_acces_token() and .is_access_token_valid() methods."""

    def server_response() -> dict[str, int | str]:
        """Return the server response to a valid authorization request."""
        return {
            "access_token": str(uuid.uuid4()),
            "token_type": "bearer",
            "expires_in": 1800,
            "refresh_token": str(uuid.uuid4()),
        }

    # TODO: ensure cache is empty...
    # maybe: token_manager = CacheManager(...) here?

    #
    # have not yet called get_access_token (so not loaded cache either)
    assert cache_manager.is_access_token_valid() is False

    #
    # test HTTPStatus.UNAUTHORIZED -> exc.AuthenticationFailedError
    data_password = {  # to assert POST was called with this data
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "Username": credentials[0],
        "Password": credentials[1],
    }

    with aioresponses() as rsp:
        response = {
            "error": "invalid_grant",
        }
        rsp.post(URL_AUTH, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.AuthenticationFailedError):
            await cache_manager.get_access_token()

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert cache_manager.is_access_token_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_AUTH, payload=payload)

        assert await cache_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert cache_manager.is_access_token_valid() is True

    #
    # check doesn't invoke the URL again, as session_id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await cache_manager.get_access_token() == payload["access_token"]

        mok.assert_not_called()

    assert cache_manager.is_access_token_valid() is True

    #
    # check does invoke the URL, as access token now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert cache_manager.is_access_token_valid() is False

    #
    # check does invoke the URL, as access token now expired
    data_token = {  # to assert POST was called with this data
        "grant_type": "refresh_token",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "refresh_token": payload["refresh_token"],
    }
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_AUTH, payload=payload)

        assert await cache_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_token
        )

    assert cache_manager.is_access_token_valid() is True

    #
    # test _clear_auth_tokens()
    cache_manager._clear_auth_tokens()

    assert cache_manager.is_access_token_valid() is False


async def test_cache(
    credentials: tuple[str, str],
    cache_manager: CacheManager,
    token_cache: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the .load_access_token() and .save_access_token() methods."""

    #
    # have not yet called get_access_token (so not loaded cache either)
    assert cache_manager.is_access_token_valid() is False

    #
    # Test 0: null token cache (zero-length content in file)
    await cache_manager._load_access_token()

    # assert not token_manager.is_access_token_valid()

    # #
    # # Test 1: valid token cache
    # with token_cache.open("w") as f:
    #     f.write(json.dumps(token_data))

    # await token_manager.load_access_token()

    # assert token_manager.is_access_token_valid()
