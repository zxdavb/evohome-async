#!/usr/bin/env python3
"""evohome-async - test config."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2
from evohomeasync2.client import TokenManager

from .faked_server import FakedServer

#
# normally, we want debug flags to be False
_DBG_USE_REAL_AIOHTTP = False
_DBG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema

if TYPE_CHECKING:
    import aiohttp

# used to construct the default token cache
DEFAULT_USERNAME: Final[str] = "username@email.com"
DEFAULT_PASSWORD: Final[str] = "P@ssw0rd!!"  # noqa: S105


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the evohomeasync and evohomeasync2 modules."""

    if _DBG_USE_REAL_AIOHTTP:
        import aiohttp
    else:
        from .faked_server import aiohttp  # type: ignore[no-redef]

    monkeypatch.setattr("evohomeasync.auth.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.auth.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.client.aiohttp", aiohttp)


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Yield a client session, which may be faked."""

    if _DBG_USE_REAL_AIOHTTP:
        import aiohttp
    else:
        from .faked_server import aiohttp  # type: ignore[no-redef]

    if _DBG_USE_REAL_AIOHTTP:
        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    else:
        client_session = aiohttp.ClientSession(faked_server=FakedServer(None, None))  # type: ignore[call-arg]

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    username: str = os.getenv("TEST_USERNAME") or DEFAULT_USERNAME
    password: str = os.getenv("TEST_PASSWORD") or DEFAULT_PASSWORD

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
    token_data: dict[str, Any],
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Return the path to the token cache."""

    # don't pollute the real token cache with fake tokens
    if _DBG_USE_REAL_AIOHTTP:
        from evohomeasync2.client import TOKEN_CACHE

        return TOKEN_CACHE

    token_cache = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    return token_cache


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def token_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    token_cache: Path,
) -> AsyncGenerator[TokenManager, None]:
    """Yield a token manager."""

    token_manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    await token_manager.load_access_token()  # restore auth tokens from cache

    try:
        yield token_manager
    finally:
        await token_manager.save_access_token()  # save auth tokens to cache


@pytest.fixture
async def evohome_v1(
    credentials: tuple[str, str],
    client_session: aiohttp.ClientSession,
) -> AsyncGenerator[evo1.EvohomeClient, None]:
    """Yield an instance of a v1 EvohomeClient."""

    evo = evo1.EvohomeClient(*credentials, websession=client_session)

    try:
        yield evo

    except evo1.AuthenticationFailed as err:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip(f"Unable to authenticate: {err}")


@pytest.fixture
async def evohome_v2(
    token_manager: TokenManager,
) -> AsyncGenerator[evo2.EvohomeClientNew, None]:
    """Yield an instance of a v2 EvohomeClient."""

    evo = evo2.EvohomeClientNew(token_manager)

    try:
        yield evo

    except evo2.AuthenticationFailedError as err:
        if not _DBG_USE_REAL_AIOHTTP:
            raise
        pytest.skip(f"Unable to authenticate: {err}")
