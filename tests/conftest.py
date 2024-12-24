"""Tests for evohome-async."""

from __future__ import annotations

import json
from datetime import UTC, datetime as dt, timedelta as td
from typing import TYPE_CHECKING

import pytest
from cli.auth import CredentialsManager

from evohomeasync import _EvohomeClientNew as EvohomeClientv0
from evohomeasync2 import _EvohomeClientNew as EvohomeClientv2

from .const import TEST_PASSWORD, TEST_USERNAME

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    import aiohttp
    from cli.auth import CacheDataT


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session(
    use_real_aiohttp: bool,  # noqa: FBT001 (is a fixture)
) -> AsyncGenerator[aiohttp.ClientSession]:
    """Yield an aiohttp.ClientSession, which may be faked."""

    if use_real_aiohttp:
        import aiohttp

        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    else:
        from .tests_rf import faked_server as fake
        from .tests_rf.faked_server import aiohttp  # type: ignore[no-redef]

        client_session = aiohttp.ClientSession(faked_server=fake.FakedServer({}, {}))  # type: ignore[call-arg]

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    username: str = TEST_USERNAME
    password: str = TEST_PASSWORD

    return username, password


@pytest.fixture(scope="session")
def cache_data_valid(credentials: tuple[str, str]) -> CacheDataT:
    """Return the path to the token cache."""

    return {
        credentials[0]: {
            "access_token": {
                "access_token": "ncw...",
                "access_token_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
                "refresh_token": "ryx...",
            },
            "session_id": {
                "session_id": "123...",
                "session_id_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
            },
        },
        "username@gmail.com.xx": {
            "access_token": {
                "access_token": "ncw...",
                "access_token_expires": (dt.now(tz=UTC) + td(hours=1)).isoformat(),
                "refresh_token": "ryx...",
            },
            "session_id": {
                "session_id": "123...",
                "session_id_expires": (dt.now(tz=UTC) - td(hours=1)).isoformat(),
            },
        },
    }


@pytest.fixture(scope="session")
def cache_data_expired(credentials: tuple[str, str]) -> CacheDataT:
    """Return the path to the token cache."""

    return {
        credentials[0]: {
            "access_token": {
                "access_token": "ncw...",
                "access_token_expires": (dt.now(tz=UTC) - td(hours=1)).isoformat(),
                "refresh_token": "ryx...",
            },
            "session_id": {
                "session_id": "123...",
                "session_id_expires": (dt.now(tz=UTC) - td(hours=1)).isoformat(),
            },
        },
    }


@pytest.fixture(scope="session")
def cache_file(
    cache_data_valid: dict[str, int | str],
    tmp_path_factory: pytest.TempPathFactory,
    use_real_aiohttp: bool,  # noqa: FBT001 (is a fixture)
) -> Path:
    """Return the path to the token cache."""

    # don't pollute the cache of real tokens (from the vendor) with fake tokens
    if use_real_aiohttp:
        from cli.client import CACHE_FILE

        return CACHE_FILE

    cache_file = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    return cache_file


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def credentials_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    cache_file: Path,
) -> AsyncGenerator[CredentialsManager]:
    """Yield a credentials manager for access_token & session_id caching."""

    manager = CredentialsManager(*credentials, client_session, cache_file=cache_file)

    await manager.load_from_cache()

    try:
        yield manager
    finally:
        await manager.save_to_cache()  # for next run of tests


@pytest.fixture
async def evohome_v0(
    credentials_manager: CredentialsManager,
) -> AsyncGenerator[EvohomeClientv0]:
    """Yield an instance of a v0 EvohomeClient."""

    evo = EvohomeClientv0(credentials_manager)

    # await evo.update()

    try:
        yield evo
    finally:
        pass


@pytest.fixture
async def evohome_v2(
    credentials_manager: CredentialsManager,
) -> AsyncGenerator[EvohomeClientv2]:
    """Yield an instance of a v2 EvohomeClient."""

    evo = EvohomeClientv2(credentials_manager)

    # await evo.update()

    try:
        yield evo
    finally:
        pass
