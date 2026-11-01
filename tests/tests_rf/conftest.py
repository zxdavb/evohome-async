"""Fixtures for the real-API tests."""

from __future__ import annotations

import asyncio
import os
import warnings
from typing import TYPE_CHECKING

import aiohttp
import pytest

import evohomeasync2 as evo2
from evohome_cli.auth import TokenCacheManager
from tests.common import get_loc
from tests.const import (
    _DBG_USE_REAL_AIOHTTP,
    TEST_PASSWORD,
    TEST_USERNAME,
    TIMEOUT_REAL_AIOHTTP,
)

from .common import skipif_auth_failed, timed_out_comm_task

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator

    from evohomeasync2 import EvohomeClient as EvohomeClientV2


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


@pytest.fixture
async def loc(
    ec2: EvohomeClientV2,
) -> evo2.Location:
    """Return the location under test (see get_loc()), with its config and status.

    The client (the ec2 fixture, which the test may also use) is set up, as is the
    location's status fetched. If either fails to authenticate, so do any later tests.
    """

    # TODO: the *_urls tests use the client only to find the entities under test; they
    # could do so via the URLs alone

    await skipif_auth_failed(ec2.setup)()
    loc = get_loc(ec2)
    await skipif_auth_failed(loc.get_status)()

    return loc


@pytest.fixture
def tcs(
    loc: evo2.Location,
) -> evo2.ControlSystem:
    """Return the TCS of the location under test; skip the test if there is none."""

    if (tcs := loc.tcs) is None:
        pytest.skip("The location under test has no TCS")
    return tcs


@pytest.fixture
def zone(
    tcs: evo2.ControlSystem,
) -> evo2.Zone:
    """Return the first zone of the TCS under test; skip the test if there is none."""

    if not tcs.zones:
        pytest.skip("The TCS under test has no zones")
    return tcs.zones[0]


@pytest.fixture
def dhw(
    tcs: evo2.ControlSystem,
) -> evo2.HotWater:
    """Return the DHW of the TCS under test; skip the test if there is none."""

    if (dhw := tcs.hotwater) is None:
        pytest.skip("The TCS under test has no DHW")
    return dhw


@pytest.fixture(autouse=True)
def skipif_comm_task_timed_out() -> None:
    """Skip the test if an earlier comm task timed out (only if waited for).

    The gateway carries out its tasks one at a time, so after such a timeout its queue
    is likely backed up, and the tests that follow would likely time out too.
    """

    if task_id := timed_out_comm_task():
        pytest.skip(f"An earlier comm task ({task_id}) did not succeed in time")


@pytest.fixture(scope="session", autouse=True)
def reset_systems(
    *,
    use_real_aiohttp: bool,
    credentials: tuple[str, str],
) -> Generator[None]:
    """After the last test, reset the location under test (see TEST_LOC_IDX).

    That is, set its TCS to Auto, and its zones/DHW to FollowSchedule. Only against the
    vendor's server. The tests do not restore what they change (the test system is
    decommissioned), so this is a best-effort tidy up: any failure (e.g. a lost device)
    is only a warning.
    """

    yield

    if use_real_aiohttp:
        asyncio.run(_reset_systems(*credentials))


async def _reset_systems(username: str, password: str) -> None:
    """Reset the location under test (TCS to Auto, zones/DHW to FollowSchedule)."""

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
            for loc in ec2.locations:
                await loc.get_status()
        except (evo2.EvohomeError, TimeoutError) as err:  # TimeoutError is not wrapped
            warnings.warn(f"Unable to reset any system: {err}", stacklevel=1)
            return

        for tcs in (t for g in get_loc(ec2).gateways for t in g.systems):
            await attempt(tcs.set_auto(), tcs)
            for zone in tcs.zones:
                await attempt(zone.reset(), zone)
            if tcs.hotwater:
                await attempt(tcs.hotwater.reset(), tcs.hotwater)

        await manager.save_to_cache()
