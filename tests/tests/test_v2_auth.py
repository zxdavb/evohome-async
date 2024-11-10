#!/usr/bin/env python3
"""evohome-async - validate the v2 API token manager."""

from __future__ import annotations

import json
import uuid
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory

from evohomeasync2 import exceptions as exc
from evohomeasync2.client import TokenManager

from ..const import HEADERS_AUTH_V1 as HEADERS_AUTH, URL_AUTH_V1 as URL_AUTH

if TYPE_CHECKING:
    from .conftest import TokenManager


async def test_get_auth_token(
    credentials: tuple[str, str],
    token_manager: TokenManager,
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
    # maybe: token_manager = TokenManager(...) here?

    #
    # have not yet called get_access_token (so not loaded cache either)
    assert token_manager.is_access_token_valid() is False

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
            await token_manager.get_access_token()

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert token_manager.is_access_token_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_AUTH, payload=payload)

        assert await token_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert token_manager.is_access_token_valid() is True

    #
    # check doesn't invoke the URL again, as session_id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await token_manager.get_access_token() == payload["access_token"]

        mok.assert_not_called()

    assert token_manager.is_access_token_valid() is True

    #
    # check does invoke the URL, as access token now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert token_manager.is_access_token_valid() is False

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

        assert await token_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_token
        )

    assert token_manager.is_access_token_valid() is True

    #
    # test _clear_auth_tokens()
    token_manager._clear_auth_tokens()

    assert token_manager.is_access_token_valid() is False



async def _test_token_manager_loading(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    tmp_path: Path,
    token_data: dict[str, Any],
) -> None:
    """Test the token manager by loading different token data from the cache."""

    def tokens_are_null() -> bool:
        return (
            token_manager.access_token == ""
            and token_manager.access_token_expires <= dt.min
            and token_manager.refresh_token == ""
        )

    # we don't use the token_manager fixture in this test
    token_cache = tmp_path / ".evo-cache.tst"

    token_manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    assert tokens_are_null()
    assert not token_manager.is_access_token_valid()

    #
    # Test 0: null token cache (zero-length content in file)
    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_access_token_valid()

    #
    # Test 1: valid token cache
    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    await token_manager.load_access_token()

    assert not tokens_are_null()
    assert token_manager.is_access_token_valid()

    #
    # Test 2: empty token cache (empty dict in file)
    with token_cache.open("w") as f:
        f.write(json.dumps({}))

    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_access_token_valid()

    #
    # Test 1: valid token cache (again)
    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    await token_manager.load_access_token()

    assert not tokens_are_null()
    assert token_manager.is_access_token_valid()

    #
    # Test 3: invalid token cache (different username)
    with token_cache.open("w") as f:
        f.write(json.dumps({f"_{credentials[0]}": token_data[credentials[0]]}))

    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_access_token_valid()
