"""Fixtures for the tests of the vendor's v1 API: a client, set up from vendor.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from evohomeasync import EvohomeClient as EvohomeClientV1
from tests.const import URL_BASE_V1

from .vendor import DHW_ID, LOC_ID, USR_ID, USR_INFO, USR_LOCS, ZON_ID

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync import ControlSystem, HotWater, Location, Zone
    from tests.tests.aioresponses import AioResponses


@pytest.fixture
async def ec1(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> EvohomeClientV1:
    """Return a v1 client, set up (config & status), with no record of its requests.

    Its session id is in the token cache, so is not requested.
    """

    mock.get(f"{URL_BASE_V1}/accountInfo", payload=USR_INFO)
    mock.get(f"{URL_BASE_V1}/locations?userId={USR_ID}&allData=True", payload=USR_LOCS)

    ec1 = EvohomeClientV1(credentials_manager)

    await ec1.setup()

    mock.requests.clear()  # so the test sees only its own requests
    return ec1


@pytest.fixture
def loc(
    ec1: EvohomeClientV1,
) -> Location:
    """Return the location (of vendor.py's LOC_ID)."""
    return ec1.location_by_id[str(LOC_ID)]


@pytest.fixture
def tcs(
    loc: Location,
) -> ControlSystem:
    """Return the TCS (of the location: v1 has no id of its own for a TCS)."""
    assert loc.tcs is not None  # mypy
    return loc.tcs


@pytest.fixture
def zone(
    tcs: ControlSystem,
) -> Zone:
    """Return the first zone (of vendor.py's ZON_ID, which is alive)."""
    return tcs.zone_by_id[str(ZON_ID)]


@pytest.fixture
def dhw(
    tcs: ControlSystem,
) -> HotWater:
    """Return the DHW (of vendor.py's DHW_ID)."""
    assert tcs.hotwater is not None  # mypy
    assert tcs.hotwater.id == str(DHW_ID)
    return tcs.hotwater
