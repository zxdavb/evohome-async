"""Fixtures for the tests of the vendor's v2 API: a client, set up from vendor.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from evohomeasync2 import EvohomeClient as EvohomeClientV2
from tests.const import URL_BASE_V2

from .vendor import LOC_ID, LOC_STATUS, USR_ACCOUNT, USR_ID, USR_LOCATIONS

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync2 import ControlSystem, HotWater, Location, Zone
    from tests.tests.aioresponses import AioResponses


@pytest.fixture
async def ec2(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> EvohomeClientV2:
    """Return a v2 client, set up (config & status), with no record of its requests.

    Its access token is in the token cache, so is not requested.
    """

    mock.get(f"{URL_BASE_V2}/userAccount", payload=USR_ACCOUNT)
    mock.get(
        f"{URL_BASE_V2}/location/installationInfo"
        f"?userId={USR_ID}&includeTemperatureControlSystems=True",
        payload=USR_LOCATIONS,
    )
    mock.get(
        f"{URL_BASE_V2}/location/{LOC_ID}/status?includeTemperatureControlSystems=True",
        payload=LOC_STATUS,
    )

    ec2 = EvohomeClientV2(credentials_manager)

    await ec2.setup()
    await ec2.locations[0].get_status()

    mock.requests.clear()  # so the test sees only its own requests
    return ec2


@pytest.fixture
def loc(
    ec2: EvohomeClientV2,
) -> Location:
    """Return the location (of vendor.py's LOC_ID)."""
    return ec2.location_by_id[LOC_ID]


@pytest.fixture
def tcs(
    loc: Location,
) -> ControlSystem:
    """Return the TCS (of vendor.py's TCS_ID)."""
    assert loc.tcs is not None  # mypy
    return loc.tcs


@pytest.fixture
def zone(
    tcs: ControlSystem,
) -> Zone:
    """Return the first zone (of vendor.py's ZON_ID)."""
    return tcs.zones[0]


@pytest.fixture
def dhw(
    tcs: ControlSystem,
) -> HotWater:
    """Return the DHW (of vendor.py's DHW_ID)."""
    assert tcs.hotwater is not None  # mypy
    return tcs.hotwater
