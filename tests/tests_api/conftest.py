"""Fixtures for the tests of the vendor's APIs (they know of neither v1 nor v2).

Every request is answered by `mock` (an AioResponses), which is active for every test:
so no request can reach the vendor, and one that has not been registered fails (as a
ClientConnectionError, i.e. an ApiCallFailedError of CONNECTION_FAILED).

The client fixtures (ec1, ec2) register the GETs of their setup on `mock`, set up the
client, and then clear its record of requests: so a test sees only its own requests.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import aiohttp
import pytest

from tests.tests.aioresponses import AioResponses

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator
    from pathlib import Path

    from evohome_cli.auth import CacheDataT


@pytest.fixture(scope="session")
def use_real_aiohttp() -> bool:
    """Return False: these tests never reach the vendor (see `mock`).

    So the token cache is a temporary one (see cache_path).
    """
    return False


@pytest.fixture
def cache_path(
    cache_data_valid: CacheDataT,
    tmp_path: Path,
) -> Path:
    """Return the path to a token cache of the test's own (with unexpired tokens).

    It is not shared, as the client saves its tokens to it (e.g. after a test of
    authentication has cleared them), so no test depends on another.
    """

    cache_path = tmp_path / ".evo-cache.tst"
    cache_path.write_text(json.dumps(cache_data_valid))
    return cache_path


@pytest.fixture
async def client_session() -> AsyncGenerator[aiohttp.ClientSession]:
    """Yield a (real) aiohttp.ClientSession, whose requests `mock` answers."""

    client_session = aiohttp.ClientSession()

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(autouse=True)
def mock() -> Generator[AioResponses]:
    """Yield the mock of the vendor's server, for the test to register responses on."""

    with AioResponses() as mock:
        yield mock
