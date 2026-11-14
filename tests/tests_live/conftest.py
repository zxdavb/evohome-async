"""Fixtures for the tests against the vendor's real servers.

These tests are skipped unless _DBG_USE_REAL_AIOHTTP (in tests/const.py) is True, and
the user's credentials are in the env vars TEST_USERNAME and TEST_PASSWORD. Its token
cache is the CLI's (so tokens are reused between runs, to avoid the vendor's rate
limits); a test that would invalidate it (i.e. that POSTs credentials) is also skipped
unless _DBG_TEST_CRED_URLS.

Each PUT is made (and so changes the test system), and, only if
_DBG_WAIT_FOR_COMM_TASKS, its comm task is then polled until it ends (succeeded or
failed: as expected), or skipped after TIMEOUT_COMM_TASK seconds (e.g. as the gateway
is offline). After the last test, the location under test is reset (best effort): its
TCS to Auto, and its zones and DHW to FollowSchedule.
"""

from __future__ import annotations

import asyncio
import os
import warnings
from typing import TYPE_CHECKING

import aiohttp
import pytest

import evohomeasync2 as evo2
from evohome_cli.auth import TokenCacheManager
from tests.const import _DBG_USE_REAL_AIOHTTP, TIMEOUT_REAL_AIOHTTP

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator


@pytest.fixture(scope="session")
def use_real_aiohttp() -> bool:
    """Return True (if enabled): these tests are against the vendor's servers."""
    return _DBG_USE_REAL_AIOHTTP


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return the user's credentials (skip the test if there are none)."""

    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")

    if not username or not password:
        pytest.skip("No credentials (set TEST_USERNAME and TEST_PASSWORD)")

    return username, password


@pytest.fixture(scope="session", autouse=True)
def reset_systems() -> Generator[None]:
    """After the last test, reset the first location (best effort).

    That is, set its TCS to Auto, and its zones/DHW to FollowSchedule (via v2). Any
    failure (e.g. a lost device) is only a warning.
    """

    yield

    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")

    if _DBG_USE_REAL_AIOHTTP and username and password:
        asyncio.run(_reset_systems(username, password))


async def _reset_systems(username: str, password: str) -> None:
    """Reset the first location (TCS to Auto, zones/DHW to FollowSchedule)."""

    async def attempt(coro: Awaitable[object], entity: object) -> None:
        try:
            await coro
        except (evo2.EvohomeError, TimeoutError) as err:  # TimeoutError is not wrapped
            warnings.warn(f"Unable to reset {entity}: {err}", stacklevel=1)

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=TIMEOUT_REAL_AIOHTTP)
    ) as websession:
        manager = TokenCacheManager(username, password, websession)  # the real cache
        await manager.load_from_cache()

        ec2 = evo2.EvohomeClient(manager)

        try:
            await ec2.setup()
        except (evo2.EvohomeError, TimeoutError) as err:  # TimeoutError is not wrapped
            warnings.warn(f"Unable to reset any system: {err}", stacklevel=1)
            return

        for tcs in (t for g in ec2.locations[0].gateways for t in g.systems):
            await attempt(tcs.set_auto(), tcs)
            for zone in tcs.zones:
                await attempt(zone.reset(), zone)
            if tcs.hotwater:
                await attempt(tcs.hotwater.reset(), tcs.hotwater)

        await manager.save_to_cache()
