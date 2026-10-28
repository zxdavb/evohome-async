"""Test the v1 session manager."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

from _evohome.const import HINT_BAD_CREDS
from evohome_cli.auth import TokenCacheManager
from evohomeasync import exceptions as exc
from tests.const import URL_CRED_V1

from .aioresponses import aioresponses
from .test_v1_urls_cred import POST_CREDS  # HACK, should be in const.py, or a fixture

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp
    from freezegun.api import FrozenDateTimeFactory

    from evohome_cli.auth import CacheDataT
    from evohomeasync.auth import SessionIdEntryT


async def test_get_session_id(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_session_id() and .is_session_valid() methods."""

    def server_response() -> dict[str, dict[str, Any] | str]:
        """Return the server response to a valid authorization request."""
        # "payload may be invalid: required key not provided at 'userInfo.xxx'"
        return {"sessionId": str(uuid.uuid4()), "userInfo": {}}

    # start with an empty cache
    session_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    #
    # have not yet called get_session_id (so not loaded cache either)
    assert session_manager.is_session_valid() is False

    with aioresponses() as rsp:
        response = [
            {
                "code": "EmailOrPasswordIncorrect",
                "message": "The email or password provided is incorrect.",
            }
        ]
        rsp.post(URL_CRED_V1, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.BadUserCredentialsError):
            await session_manager.get_session_id()

        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert session_manager.is_session_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V1, payload=payload)

        assert await session_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert session_manager.is_session_valid() is True

    #
    # check doesn't invoke the URL again, as session ID still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await session_manager.get_session_id() == payload["sessionId"]

        mok.assert_not_called()

    assert session_manager.is_session_valid() is True

    #
    # check session ID now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert session_manager.is_session_valid() is False

    #
    # check does invoke the URL, as session ID now expired
    #
    #
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V1, payload=payload)

        assert await session_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert session_manager.is_session_valid() is True

    #
    # test clear_session_id()
    session_manager.clear_session_id()

    assert session_manager.is_session_valid() is False


async def test_session_manager(  # noqa: PLR0917  # pytest injects fixtures by keyword
    cache_data_expired: CacheDataT,
    cache_data_valid: CacheDataT,
    cache_path: Path,
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    freezer: FrozenDateTimeFactory,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the .load_session_id() and .save_session_id() methods."""

    cache_path = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    #
    # TEST 1: load an invalid cache...
    with cache_path.open("w") as f:
        f.write(json.dumps(cache_data_expired, indent=4))

    session_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    # have not yet called get_access_token (so not loaded cache either)
    assert session_manager.is_session_valid() is False

    await session_manager.load_from_cache()
    assert session_manager.is_session_valid() is False

    #
    # TEST 2: load a valid token cache
    with cache_path.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    session_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    await session_manager.load_from_cache()
    assert session_manager.is_session_valid() is True

    session_id = await session_manager.get_session_id()

    #
    # TEST 3: some time has passed, but token is not expired
    freezer.tick(600)  # advance time by 5 minutes
    assert session_manager.is_session_valid() is True

    assert await session_manager.get_session_id() == session_id

    #
    # TEST 4: test save_session_id() method
    freezer.tick(1800)  # advance time by 15 minutes, 20 mins total
    assert session_manager.is_session_valid() is False

    with (
        patch(
            "evohomeasync.auth.AbstractSessionManager._post_session_id_request",
            new_callable=AsyncMock,
        ) as req,
        patch(
            "evohome_cli.auth.TokenCacheManager.save_session_id",
            new_callable=AsyncMock,
        ) as wrt,
    ):
        req.return_value = {
            "sessionId": "new_session_id...",
            "userInfo": {},  # "payload may be invalid: expected..."
        }

        assert await session_manager.get_session_id() == "new_session_id..."

        req.assert_called_once()
        wrt.assert_called_once()

    assert session_manager.is_session_valid() is True


async def test_concurrent_get_session_id_fetches_once(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
) -> None:
    """Test that concurrent callers of .get_session_id() share a single fetch."""

    session_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )
    assert session_manager.is_session_valid() is False

    async def fetch_session_id() -> None:
        for _ in range(3):  # yield, so that the other callers queue behind this one
            await asyncio.sleep(0)
        session_manager._session_id = str(uuid.uuid4())
        session_manager._session_id_expires = dt.now(tz=UTC) + td(minutes=15)

    with (
        patch.object(
            session_manager, "fetch_session_id", side_effect=fetch_session_id
        ) as fetch,
        patch.object(
            session_manager, "save_session_id", new_callable=AsyncMock
        ) as save,
    ):
        results = await asyncio.gather(
            *(session_manager.get_session_id() for _ in range(5))
        )

    assert len(set(results)) == 1
    assert results[0] == session_manager.session_id
    assert fetch.call_count == 1
    save.assert_awaited_once()


async def test_concurrent_get_session_id_failure(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that concurrent callers of .get_session_id() share a failed fetch."""

    session_manager = TokenCacheManager(
        *credentials, client_session, cache_path=cache_path
    )

    async def _fetch_session_id(credentials: dict[str, str]) -> None:
        for _ in range(3):  # yield, so that the other callers queue behind this one
            await asyncio.sleep(0)
        raise exc.AuthenticationFailedError(
            '[{"code": "EmailOrPasswordIncorrect"}]', status=HTTPStatus.UNAUTHORIZED
        )

    with (
        patch.object(
            session_manager, "_fetch_session_id", side_effect=_fetch_session_id
        ) as fetch,
        patch.object(
            session_manager, "save_session_id", new_callable=AsyncMock
        ) as save,
    ):
        results = await asyncio.gather(
            *(session_manager.get_session_id() for _ in range(5)),
            return_exceptions=True,
        )

        assert all(isinstance(r, exc.BadUserCredentialsError) for r in results)
        assert fetch.call_count == 1
        save.assert_not_awaited()
        assert [r.message for r in caplog.records].count(HINT_BAD_CREDS) == 1

        # a failure is shared only with the callers queued behind it, not later ones
        fetch.reset_mock()
        with pytest.raises(exc.BadUserCredentialsError):
            await session_manager.get_session_id()

        fetch.assert_called_once()

    assert session_manager.is_session_valid() is False


def test_session_id_round_trip(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_path: Path,
) -> None:
    """Test an exported session ID can be imported by another session manager."""

    expires = dt.now(tz=UTC) + td(minutes=10)
    session: SessionIdEntryT = {
        "session_id": "session_id",
        "session_id_expires": expires.isoformat(),
    }

    manager = TokenCacheManager(*credentials, client_session, cache_path=cache_path)
    manager.import_session_id(session)

    assert manager.session_id == "session_id"
    assert manager.session_id_expires == expires
    assert manager.is_session_valid() is True

    assert manager.export_session_id() == session
