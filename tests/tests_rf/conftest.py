#!/usr/bin/env python3
"""evohome-async - test config."""

import logging
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from . import _DEBUG_USE_REAL_AIOHTTP
from .helpers import aiohttp
from .mocked_server import MockedServer

_LOGGER = logging.getLogger(__name__)


#######################################################################################


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evohomeasync2.base.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.broker.aiohttp", aiohttp)

    monkeypatch.setattr("evohomeasync.base.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync.broker.aiohttp", aiohttp)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    if _DEBUG_USE_REAL_AIOHTTP:
        client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    else:
        client_session = aiohttp.ClientSession(mocked_server=MockedServer(None, None))  # type: ignore[call-arg]

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture()
def user_credentials() -> tuple[str, str]:
    username: str = os.getenv("TEST_USERNAME")
    password: str = os.getenv("TEST_PASSWORD")

    return username, password
