"""Test the v2 token manager."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from _evohome.const import HINT_BAD_CREDS
from evohome_cli.auth import TokenCacheManager
from evohomeasync2 import exceptions as exc
from tests.const import HEADERS_CRED_V2, URL_CRED_V2

from .aioresponses import aioresponses
from .test_v2_urls_cred import POST_CREDS  # HACK, should be in const.py, or a fixture

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp
    from freezegun.api import FrozenDateTimeFactory

    from evohome_cli.auth import CacheDataT
    from evohomeasync2.auth import EvoAccessTokenEntryT


async def test_get_auth_token(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
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
    token_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    #
    # have not yet called get_access_token (so not loaded cache either)
    assert token_manager.is_token_valid() is False

    with aioresponses() as rsp:
        response = {
            "error": "invalid_grant",
        }
        rsp.post(URL_CRED_V2, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.BadUserCredentialsError):
            await token_manager.get_access_token()

        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert token_manager.is_token_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V2, payload=payload)

        assert await token_manager.get_access_token() == payload["access_token"]

        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

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
    # test clear_access_token()
    token_manager.clear_access_token()

    assert token_manager.is_token_valid() is False


async def test_token_manager(  # noqa: PLR0917  # pytest injects fixtures by keyword
    cache_data_expired: CacheDataT,
    cache_data_valid: CacheDataT,
    cache_path: Path,
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the .load_access_token() and .save_access_token() methods."""

    cache_path = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    #
    # TEST 1: load an invalid cache...
    with cache_path.open("w") as f:
        f.write(json.dumps(cache_data_expired, indent=4))

    token_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    # have not yet called get_access_token (so not loaded cache either)
    assert token_manager.is_session_valid() is False

    await token_manager.load_from_cache()
    assert token_manager.is_token_valid() is False

    #
    # TEST 2: load a valid token cache
    with cache_path.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    token_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
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
            "evohome_cli.auth.TokenCacheManager.save_access_token",
            new_callable=AsyncMock,
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
            assert caplog.records[3].message == (" - access_token = ********")
            assert caplog.records[4].message.startswith(" - access_token_expires = ")
            # fmt: on

            assert len(caplog.records) == 5  # noqa: PLR2004

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
            "evohome_cli.auth.TokenCacheManager.save_access_token",
            new_callable=AsyncMock,
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

            # "payload may be invalid: required key not provided at 'token_type'"
            assert "payload may be invalid" in caplog.records[2].message

        req.assert_called_once()
        wrt.assert_called_once()

    assert token_manager.is_token_valid() is True


async def test_concurrent_get_access_token_fetches_once(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
) -> None:
    """Test that concurrent callers of .get_access_token() share a single fetch."""

    token_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )
    assert token_manager.is_token_valid() is False

    async def fetch_access_token() -> None:
        for _ in range(3):  # yield, so that the other callers queue behind this one
            await asyncio.sleep(0)
        token_manager._access_token = str(uuid.uuid4())
        token_manager._access_token_expires = dt.now(tz=UTC) + td(seconds=1800)

    with (
        patch.object(
            token_manager, "fetch_access_token", side_effect=fetch_access_token
        ) as fetch,
        patch.object(
            token_manager, "save_access_token", new_callable=AsyncMock
        ) as save,
    ):
        results = await asyncio.gather(
            *(token_manager.get_access_token() for _ in range(5))
        )

    assert len(set(results)) == 1
    assert results[0] == token_manager.access_token
    assert fetch.call_count == 1
    save.assert_awaited_once()


async def test_concurrent_get_access_token_failure(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that concurrent callers of .get_access_token() share a failed fetch."""

    token_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    async def _fetch_access_token(credentials: dict[str, str]) -> None:
        for _ in range(3):  # yield, so that the other callers queue behind this one
            await asyncio.sleep(0)
        raise exc.AuthenticationFailedError(
            '{"error": "invalid_grant"}', status=HTTPStatus.BAD_REQUEST
        )

    with (
        patch.object(
            token_manager, "_fetch_access_token", side_effect=_fetch_access_token
        ) as fetch,
        patch.object(
            token_manager, "save_access_token", new_callable=AsyncMock
        ) as save,
    ):
        results = await asyncio.gather(
            *(token_manager.get_access_token() for _ in range(5)),
            return_exceptions=True,
        )

        assert all(isinstance(r, exc.BadUserCredentialsError) for r in results)
        assert fetch.call_count == 1
        save.assert_not_awaited()
        assert [r.message for r in caplog.records].count(HINT_BAD_CREDS) == 1

        # a failure is shared only with the callers queued behind it, not later ones
        fetch.reset_mock()
        with pytest.raises(exc.BadUserCredentialsError):
            await token_manager.get_access_token()

        fetch.assert_called_once()

    assert token_manager.is_token_valid() is False


def test_credential_locks_are_independent(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
) -> None:
    """Test that the access token and session ID are refreshed under separate locks."""

    manager = TokenCacheManager(*credentials, client_session, cache_path=cache_path)

    assert isinstance(manager._token_lock, asyncio.Lock)
    assert isinstance(manager._session_lock, asyncio.Lock)
    assert manager._token_lock is not manager._session_lock


def test_access_token_round_trip(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
) -> None:
    """Test an exported access token can be imported by another token manager."""

    expires = dt.now(tz=UTC) + td(minutes=30)
    tokens: EvoAccessTokenEntryT = {
        "access_token": "access_token",
        "access_token_expires": expires.isoformat(),
        "refresh_token": "refresh_token",
    }

    manager = TokenCacheManager(*credentials, client_session, cache_path=cache_path)
    manager.import_access_token(tokens)

    assert manager.access_token == tokens["access_token"]
    assert manager.access_token_expires == expires
    assert manager.refresh_token == tokens["refresh_token"]
    assert manager.is_token_valid() is True

    assert manager.export_access_token() == tokens
