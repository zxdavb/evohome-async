#!/usr/bin/env python3
"""Tests for evohome-async."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2

from .common import SessionManager, TokenManager
from .const import TEST_PASSWORD, TEST_USERNAME

if TYPE_CHECKING:
    import aiohttp


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session(
    use_fake_aiohttp: bool,
) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Yield an aiohttp.ClientSession, which may be faked."""

    if use_fake_aiohttp:
        from .tests_rf.faked_server import aiohttp  # type: ignore[no-redef]
    else:
        import aiohttp

    if use_fake_aiohttp:
        from .tests_rf.faked_server import FakedServer

        client_session = aiohttp.ClientSession(faked_server=FakedServer(None, None))  # type: ignore[call-arg]
    else:
        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    username: str = os.getenv("TEST_USERNAME") or TEST_USERNAME
    password: str = os.getenv("TEST_PASSWORD") or TEST_PASSWORD

    return username, password


@pytest.fixture(scope="session")
def token_data(credentials: tuple[str, str]) -> dict[str, Any]:
    """Return the path to the token cache."""

    return {
        credentials[0]: {
            "access_token": "ncWMqPh2yGgAqc...",
            "access_token_expires": (dt.now() + td(hours=1)).isoformat(),
            "refresh_token": "Ryx9fL34Z5GcNV...",
        }
    }


@pytest.fixture(scope="session")
def token_cache(
    token_data: dict[str, int | str],
    tmp_path_factory: pytest.TempPathFactory,
    use_fake_aiohttp: bool,
) -> Path:
    """Return the path to the token cache."""

    # don't pollute the real token cache with fake tokens
    if not use_fake_aiohttp:
        from evohomeasync2.client import TOKEN_CACHE

        return TOKEN_CACHE

    token_cache = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    return token_cache


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def session_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    token_cache: Path,
) -> AsyncGenerator[SessionManager, None]:
    """Yield a token manager for the v1 API."""

    manager = SessionManager(*credentials, client_session, token_cache=token_cache)

    # await manager.load_session_id()  # dont restore from cache yet

    try:
        yield manager
    finally:
        await manager.save_session_id()  # for next run of tests


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def token_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    token_cache: Path,
) -> AsyncGenerator[TokenManager, None]:
    """Yield a token manager for the v2 API."""

    manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    # await manager.restore_access_token()  # dont restore from cache yet

    try:
        yield manager
    finally:
        await manager.save_access_token()  # for next run of tests


@pytest.fixture
async def evohome_v1(
    credentials: tuple[str, str],
    client_session: aiohttp.ClientSession,
) -> AsyncGenerator[evo1.EvohomeClient, None]:
    """Yield an instance of a v1 EvohomeClient."""

    evo = evo1.EvohomeClient(*credentials, websession=client_session)

    # await evo.update()

    try:
        yield evo
    finally:
        pass


@pytest.fixture
async def evohome_v2(
    token_manager: TokenManager,
) -> AsyncGenerator[evo2.EvohomeClientNew, None]:
    """Yield an instance of a v2 EvohomeClient."""

    evo = evo2.EvohomeClientNew(token_manager)

    # await evo.update()

    try:
        yield evo
    finally:
        pass
