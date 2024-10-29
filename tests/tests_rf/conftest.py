#!/usr/bin/env python3
"""evohome-async - test config."""

import logging
import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Final

import pytest
import pytest_asyncio

from .faked_server import FakedServer

# normally, we want these debug flags to be False
_DBG_USE_REAL_AIOHTTP = False
_DBG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema

if _DBG_USE_REAL_AIOHTTP:
    import aiohttp

    from evohomeasync2.client import TOKEN_CACHE
else:
    from .faked_server import aiohttp  # type: ignore[no-redef]

    # so we don't pollute a real token cache with fake tokens
    TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tst")  # type: ignore[misc]


_LOGGER = logging.getLogger(__name__)


#######################################################################################


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evohomeasync2.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.base.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.session.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.client.aiohttp", aiohttp)

    monkeypatch.setattr("evohomeasync.base.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync.broker.aiohttp", aiohttp)


@pytest_asyncio.fixture
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    if _DBG_USE_REAL_AIOHTTP:
        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    else:
        client_session = aiohttp.ClientSession(faked_server=FakedServer(None, None))  # type: ignore[call-arg]

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture()
def user_credentials() -> tuple[str, str]:
    username: str = os.getenv("TEST_USERNAME") or "username@email.com"
    password: str = os.getenv("TEST_PASSWORD") or "password!"

    return username, password
