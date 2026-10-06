"""evohome-async - test config."""

from __future__ import annotations

import asyncio
import os
import warnings
from typing import TYPE_CHECKING

import pytest

import evohomeasync2 as evo2
from evohome_cli.auth import TokenCacheManager
from tests.const import (
    _DBG_USE_REAL_AIOHTTP,
    REAL_AIOHTTP_TIMEOUT,
    TEST_PASSWORD,
    TEST_USERNAME,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator


@pytest.fixture(scope="session")
def use_real_aiohttp() -> bool:
    """Return True if using the real aiohttp library.

    This indicates testing is against the vendor's servers rather than a faked server.
    """
    return _DBG_USE_REAL_AIOHTTP


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    username: str = os.getenv("TEST_USERNAME") or TEST_USERNAME
    password: str = os.getenv("TEST_PASSWORD") or TEST_PASSWORD

    return username, password


@pytest.fixture(scope="session", autouse=True)
def reset_systems(
    use_real_aiohttp: bool,  # noqa: FBT001 (is a fixture)
    credentials: tuple[str, str],
) -> Generator[None]:
    """After the last test, set every TCS to Auto, and its zones/DHW to FollowSchedule.

    The tests do not restore what they change (the test system is decommissioned), so
    this is a best-effort tidy up: any failure (e.g. a lost device) is only a warning.
    """

    yield

    if use_real_aiohttp:
        asyncio.run(_reset_systems(*credentials))


async def _reset_systems(username: str, password: str) -> None:
    """Set every TCS to Auto, and its zones/DHW to FollowSchedule (v2 API)."""

    import aiohttp  # noqa: PLC0415

    async def attempt(coro: Awaitable[object], entity: object) -> None:
        try:
            await coro
        except evo2.EvohomeError as err:
            warnings.warn(f"Unable to reset {entity}: {err}", stacklevel=1)

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=REAL_AIOHTTP_TIMEOUT)
    ) as websession:
        manager = TokenCacheManager(username, password, websession)  # the real cache
        await manager.load_from_cache()

        evo = evo2.EvohomeClient(manager)

        try:
            await evo.update()
        except evo2.EvohomeError as err:
            warnings.warn(f"Unable to reset any system: {err}", stacklevel=1)
            return

        for tcs in (
            t for loc in evo.locations for g in loc.gateways for t in g.systems
        ):
            await attempt(tcs.set_auto(), tcs)
            for zone in tcs.zones:
                await attempt(zone.reset(), zone)
            if tcs.hotwater:
                await attempt(tcs.hotwater.reset(), tcs.hotwater)

        await manager.save_to_cache()
