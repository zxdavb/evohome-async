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
from cli.auth import CacheManager

from evohomeasync import _EvohomeClientNew as EvohomeClientv0
from evohomeasync2 import _EvohomeClientNew as EvohomeClientv2

from .const import TEST_PASSWORD, TEST_USERNAME

if TYPE_CHECKING:
    import aiohttp


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session(
    use_real_aiohttp: bool,
) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Yield an aiohttp.ClientSession, which may be faked."""

    if use_real_aiohttp:
        import aiohttp  # type: ignore[no-redef]
    else:
        from .tests_rf.faked_server import aiohttp

    if use_real_aiohttp:
        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    else:
        from .tests_rf.faked_server import FakedServer

        client_session = aiohttp.ClientSession(faked_server=FakedServer(None, None))

    try:
        yield client_session  # type: ignore[misc]
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
            "auth_tokens": {
                "access_token": "ncw...",
                "access_token_expires": (dt.now() + td(hours=1)).isoformat(),
                "refresh_token": "ryx...",
            },
            "session_id": {
                "session_id": "123...",
                "session_id_expires": (dt.now() + td(hours=1)).isoformat(),
            },
        },
        "username@gmail.com": {
            "auth_tokens": {
                "access_token": "ncw...",
                "access_token_expires": (dt.now() + td(hours=1)).isoformat(),
                "refresh_token": "ryx...",
            },
            "session_id": {
                "session_id": "123...",
                "session_id_expires": (dt.now() - td(hours=1)).isoformat(),
            },
        },
    }


@pytest.fixture(scope="session")
def cache_file(
    token_data: dict[str, int | str],
    tmp_path_factory: pytest.TempPathFactory,
    use_real_aiohttp: bool,
) -> Path:
    """Return the path to the token cache."""

    # don't pollute the cache of real tokens (from the vendor) with fake tokens
    if use_real_aiohttp:
        from cli.client import CACHE_FILE

        return CACHE_FILE

    cache_file = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    with cache_file.open("w") as f:
        f.write(json.dumps(token_data, indent=4))

    return cache_file


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def cache_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_file: Path,
) -> AsyncGenerator[CacheManager, None]:
    """Yield a token manager for the v2 API."""

    manager = CacheManager(*credentials, client_session, cache_file=cache_file)

    # await cache_manager.load_cache()

    try:
        yield manager
    finally:
        await manager.save_access_token()  # for next run of tests


@pytest.fixture
async def evohome_v0(
    cache_manager: CacheManager,
) -> AsyncGenerator[EvohomeClientv0, None]:
    """Yield an instance of a v0 EvohomeClient."""

    await cache_manager.load_cache()

    evo = EvohomeClientv0(cache_manager)

    # await evo.update()

    try:
        yield evo
    finally:
        pass


@pytest.fixture
async def evohome_v2(
    cache_manager: CacheManager,
) -> AsyncGenerator[EvohomeClientv2, None]:
    """Yield an instance of a v2 EvohomeClient."""

    await cache_manager.load_cache()

    evo = EvohomeClientv2(cache_manager)

    # await evo.update()

    try:
        yield evo
    finally:
        pass
