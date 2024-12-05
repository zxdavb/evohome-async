#!/usr/bin/env python3
"""evohome-async - validate the v2 API token manager."""

from __future__ import annotations

import json
import uuid
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from cli.auth import TokenManager

from evohomeasync2 import exceptions as exc
from tests.const import HEADERS_AUTH_V2 as HEADERS_AUTH, URL_AUTH_V2 as URL_AUTH

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp
    from cli.auth import CacheDataT
    from freezegun.api import FrozenDateTimeFactory


async def test_get_auth_token(
    credentials: tuple[str, str],
    cache_manager: TokenManager,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_access_token() and .is_access_token_valid() methods."""

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
    # test _clear_access_token()
    cache_manager._clear_access_token()

    assert cache_manager.is_access_token_valid() is False


async def test_token_manager(
    cache_data_expired: CacheDataT,
    cache_data_valid: CacheDataT,
    cache_file: Path,
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    freezer: FrozenDateTimeFactory,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the .load_access_token() and .save_access_token() methods."""

    cache_file = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    #
    # TEST 1: load an invalid cache...
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_expired, indent=4))

    cache_manager = TokenManager(*credentials, client_session, cache_file=cache_file)

    # have not yet called get_access_token (so not loaded cache either)
    assert cache_manager.is_session_id_valid() is False

    await cache_manager.load_cache()
    assert cache_manager.is_access_token_valid() is False

    #
    # TEST 2: load a valid token cache
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    cache_manager = TokenManager(*credentials, client_session, cache_file=cache_file)

    await cache_manager.load_cache()
    assert cache_manager.is_access_token_valid() is True

    access_token = await cache_manager.get_access_token()

    #
    # TEST 3: some time has passed, but token is not expired
    freezer.tick(600)  # advance time by 5 minutes
    assert cache_manager.is_access_token_valid() is True

    assert await cache_manager.get_access_token() == access_token

    #
    # TEST 4: test save_access_token() method
    freezer.tick(1800)  # advance time by 15 minutes, 20 mins total
    assert cache_manager.is_access_token_valid() is False

    with (
        patch(
            "evohomeasync2.auth.AbstractTokenManager._post_access_token_request",
            new_callable=AsyncMock,
        ) as req,
        patch("cli.auth.CacheManager.save_access_token", new_callable=AsyncMock) as wrt,
    ):
        req.return_value = {
            "access_token": "new_access_token...",
            "expires_in": 1800,
            "refresh_token": "new_refresh_token...",
        }

        assert await cache_manager.get_access_token() == "new_access_token..."

        req.assert_called_once()
        wrt.assert_called_once()

    assert cache_manager.is_access_token_valid() is True
