#!/usr/bin/env python3
"""evohome-async - test config."""

from __future__ import annotations

import functools
import json
import os
from collections.abc import AsyncGenerator, Callable
from datetime import datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, TypeVar

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2
from evohomeasync2.client import TokenManager

from .common import SessionManager  # incl. support for cache file
from .const import _DBG_USE_REAL_AIOHTTP
from .faked_server import FakedServer

if TYPE_CHECKING:
    import aiohttp

# used to construct the default token cache
TEST_USERNAME: Final = "spotty.blackcat@gmail.com"  # SECRET "username@email.com"
TEST_PASSWORD: Final = "ziQajn732m5JYQ!"  # "P@ssw0rd!!"  # noqa: S105


_FNC = TypeVar("_FNC", bound=Callable[..., Any])


# Global flag to indicate if AuthenticationFailedError has been encountered
global_auth_failed = False


# decorator to skip remaining tests if an AuthenticationFailedError is encountered
def skipif_auth_failed(fnc: _FNC) -> _FNC:
    """Decorator to skip tests if AuthenticationFailedError is encountered."""

    @functools.wraps(fnc)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        global global_auth_failed

        if global_auth_failed:
            pytest.skip("Unable to authenticate")

        try:
            return await fnc(*args, **kwargs)

        except (
            evo1.AuthenticationFailedError,
            evo2.AuthenticationFailedError,
        ) as err:
            if not _DBG_USE_REAL_AIOHTTP:
                raise

            global_auth_failed = True
            pytest.fail(f"Unable to authenticate: {err}")

    return wrapper  # type: ignore[return-value]


@pytest.fixture(autouse=False)
def zpatches_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
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
async def session_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    token_cache: Path,
) -> AsyncGenerator[SessionManager, None]:
    """Yield a token manager for the v1 API."""

    manager = SessionManager(*credentials, client_session, token_cache=token_cache)

    # await manager.load_session_id()  # restoresession_id from cache

    try:
        yield manager
    finally:
        await manager.save_session_id()  # save auth tokens to cache


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def token_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    token_cache: Path,
) -> AsyncGenerator[TokenManager, None]:
    """Yield a token manager for the v2 API."""

    manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    # await manager.load_access_token()  # restore auth tokens from cache

    try:
        yield manager
    finally:
        await manager.save_access_token()  # save auth tokens to cache


@pytest.fixture
async def evohome_v1(
    credentials: tuple[str, str],
    client_session: aiohttp.ClientSession,
) -> AsyncGenerator[evo1.EvohomeClient, None]:
    """Yield an instance of a v1 EvohomeClient."""

    evo = evo1.EvohomeClient(*credentials, websession=client_session)

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

    try:
        yield evo
    finally:
        pass
