"""evohome-async - validate the v2 API token manager."""

from __future__ import annotations

import json
import logging
import uuid
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from cli.auth import CredentialsManager

from evohomeasync2 import exceptions as exc
from tests.const import HEADERS_CRED_V2, URL_CRED_V2

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp
    from cli.auth import CacheDataT
    from freezegun.api import FrozenDateTimeFactory


async def test_get_auth_token(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_file: Path,
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

    # start with an empty cache
    token_manager = CredentialsManager(
        *credentials, client_session, cache_file=cache_file
    )

    #
    # have not yet called get_access_token (so not loaded cache either)
    assert token_manager.is_token_valid() is False

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
        rsp.post(URL_CRED_V2, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.AuthenticationFailedError):
            await token_manager.get_access_token()

        rsp.assert_called_once_with(
            URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=data_password
        )

    assert token_manager.is_token_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V2, payload=payload)

        assert await token_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=data_password
        )

    assert token_manager.is_token_valid() is True

    #
    # check doesn't invoke the URL again, as session_id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await token_manager.get_access_token() == payload["access_token"]

        mok.assert_not_called()

    assert token_manager.is_token_valid() is True

    #
    # check does invoke the URL, as access token now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert token_manager.is_token_valid() is False

    #
    # check does invoke the URL, as access token now expired
    data_token = {  # to assert POST was called with this data
        "grant_type": "refresh_token",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "refresh_token": payload["refresh_token"],
    }
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V2, payload=payload)

        assert await token_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(
            URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=data_token
        )

    assert token_manager.is_token_valid() is True

    #
    # test _clear_access_token()
    token_manager._clear_access_token()

    assert token_manager.is_token_valid() is False


async def test_token_manager(
    cache_data_expired: CacheDataT,
    cache_data_valid: CacheDataT,
    cache_file: Path,
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the .load_access_token() and .save_access_token() methods."""

    cache_file = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    #
    # TEST 1: load an invalid cache...
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_expired, indent=4))

    token_manager = CredentialsManager(
        *credentials, client_session, cache_file=cache_file
    )

    # have not yet called get_access_token (so not loaded cache either)
    assert token_manager.is_session_valid() is False

    await token_manager.load_from_cache()
    assert token_manager.is_token_valid() is False

    #
    # TEST 2: load a valid token cache
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    token_manager = CredentialsManager(
        *credentials, client_session, cache_file=cache_file
    )

    await token_manager.load_from_cache()
    assert token_manager.is_token_valid() is True

    access_token = await token_manager.get_access_token()

    #
    # TEST 3: some time has passed, but token is not expired
    freezer.tick(600)  # advance time by 5 minutes
    assert token_manager.is_token_valid() is True

    assert await token_manager.get_access_token() == access_token

    #
    # TEST 4: test save_access_token() method
    freezer.tick(1800)  # advance time by 15 minutes, 20 mins total
    assert token_manager.is_token_valid() is False

    with (
        patch(
            "evohomeasync2.auth.AbstractTokenManager._post_access_token_request",
            new_callable=AsyncMock,
        ) as req,
        patch(
            "cli.auth.CredentialsManager.save_access_token", new_callable=AsyncMock
        ) as wrt,
    ):
        req.return_value = {
            "access_token": "new_access_token...",
            "expires_in": 1800,
            "refresh_token": "new_refresh_token...",
            "token_type": "bearer",
        }

        with caplog.at_level(logging.DEBUG):
            assert await token_manager.get_access_token() == "new_access_token..."

            # fmt: off
            assert caplog.records[0].message == ("Fetching access_token...")
            assert caplog.records[1].message == (" - authenticating with the refresh_token")
            assert caplog.records[2].message.startswith("POST https://tccna.resideo.com/Auth/OAuth/Token")
            assert caplog.records[3].message == (" - access_token = new_access_token...")
            assert caplog.records[4].message.startswith(" - access_token_expires = ")
            assert caplog.records[5].message == (" - refresh_token = new_refresh_token...")
            # fmt: on

        req.assert_called_once()
        wrt.assert_called_once()

    assert token_manager.is_token_valid() is True

    #
    # TEST 5: look for warning message
    freezer.tick(2400)  # advance time by another 20 minutes
    assert token_manager.is_token_valid() is False

    with (
        patch(
            "evohomeasync2.auth.AbstractTokenManager._post_access_token_request",
            new_callable=AsyncMock,
        ) as req,
        patch(
            "cli.auth.CredentialsManager.save_access_token", new_callable=AsyncMock
        ) as wrt,
    ):
        req.return_value = {
            "access_token": "newer_access_token...",
            "expires_in": 1800,
            "refresh_token": "newer_refresh_token...",
            # "token_type": "bearer",  # should throw the warning we're looking for
        }

        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            assert await token_manager.get_access_token() == "newer_access_token..."

            # required key not provided @ data['token_type']
            assert "payload may be invalid" in caplog.records[2].message

        req.assert_called_once()
        wrt.assert_called_once()

    assert token_manager.is_token_valid() is True
