"""Test the setup() and get_status() methods of both clients."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2
from _evohome import exceptions as exc
from tests.common import get_loc, get_tcs, get_zon

from .conftest import FIXTURES_V1, FIXTURES_V2, auth_get

if TYPE_CHECKING:
    from _evohome.helpers import Validator
    from evohome_cli.auth import TokenCacheManager


async def test_v2_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config only, and Location.get_status() the status."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        ec2 = evo2.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = ec2.locations

        await ec2.setup()

        loc = get_loc(ec2)  # the config is available...
        zone = get_zon(ec2)
        assert zone is not None  # the default/ fixture has zones

        with pytest.raises(exc.EvohomeError):  # ... but not the status
            _ = zone.status

        status = await loc.get_status()

        assert status["location_id"] == loc.id
        assert zone.status["zone_id"] == zone.id  # no longer raises


async def test_v1_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config and, as v1 has them in one GET, the status."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V1 / "default")):
        ec1 = evo1.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = ec1.locations

        await ec1.setup()

        assert get_tcs(ec1).zones[0].temperature is not None


async def test_v1_get_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test get_status() gets the latest status every time it is called."""

    mock_get = auth_get(FIXTURES_V1 / "default")
    calls: list[str] = []

    async def get(self: object, url: str, /, schema: Validator[Any]) -> object:
        calls.append(url)
        return await mock_get(self, url, schema)

    with patch("evohomeasync.auth.Auth.get", get):
        ec1 = evo1.EvohomeClient(credentials_manager)

        await ec1.get_status()  # also gets the config, as it is first

        calls.clear()
        await ec1.get_status()

    assert len(calls) == 1
    assert calls[0].startswith("locations?userId=")


async def test_v2_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location.tcs is the TCS of a location (each has 0-1 TCSs)."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "system_004")):
        ec2 = evo2.EvohomeClient(credentials_manager)
        await ec2.setup()

    *locs, loc_sans_gwy = ec2.locations  # the last location has no gateway

    for loc in locs:
        assert loc.tcs is loc.gateways[0].systems[0]

    assert loc_sans_gwy.tcs is None


@pytest.mark.parametrize(
    "fixture",
    [
        pytest.param("null_system_1", id="no_gateway"),
        pytest.param("null_system_2", id="no_tcs"),
    ],
)
async def test_v2_location_tcs_none(
    credentials_manager: TokenCacheManager,
    fixture: str,
) -> None:
    """Test Location.tcs is None if the location has no TCS."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / fixture)):
        ec2 = evo2.EvohomeClient(credentials_manager)
        await ec2.setup()

    assert get_loc(ec2).tcs is None


async def test_v1_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location.tcs has the location's devices, or is None if it has none."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V1 / "default")):
        ec1 = evo1.EvohomeClient(credentials_manager)
        await ec1.setup()

    loc = get_loc(ec1)
    assert (tcs := loc.tcs) is not None
    assert tcs is loc.gateways[0].systems[0]
    assert tcs.hotwater is not None  # the default/ fixture has a DHW

    dev_ids = {str(d["device_id"]) for d in loc.config["devices"]}
    assert dev_ids == set(tcs.zone_by_id) | {tcs.hotwater.id}

    config = copy.deepcopy(loc.config)
    config["devices"] = []

    assert (await evo1.entities.create_location(ec1, config)).tcs is None


async def test_vx_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test each location's gateway/TCS has the same ids via the v1 and v2 APIs.

    The system_009/ fixtures are of the same (multi-location) account, captured at the
    same time. Its locations are in a different order for each API.
    """

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V1 / "system_009")):
        ec1 = evo1.EvohomeClient(credentials_manager)
        await ec1.setup()

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "system_009")):
        ec2 = evo2.EvohomeClient(credentials_manager)
        await ec2.setup()

    def devices(tcs: evo1.ControlSystem | evo2.ControlSystem | None) -> set[str] | None:
        if tcs is None:
            return None
        dhw = {tcs.hotwater.id} if tcs.hotwater else set()
        return {z.id for z in tcs.zones} | dhw

    for loc in ec1.locations + ec2.locations:
        assert len(loc.gateways) <= 1  # a location has 0-1 gateways...
        assert all(len(g.systems) <= 1 for g in loc.gateways)  # ...each with 0-1 TCSs

        gwy = loc.gateways[0] if loc.gateways else None
        assert loc.tcs is (gwy.systems[0] if gwy and gwy.systems else None)

    v1_gwys = {
        loc.id: [(g.id, g.mac_address) for g in loc.gateways] for loc in ec1.locations
    }
    v2_gwys = {
        loc.id: [(g.id, g.mac_address) for g in loc.gateways] for loc in ec2.locations
    }

    assert v1_gwys == v2_gwys
    assert v1_gwys == {
        "2738909": [("2499896", "00D02DEE4E56")],
        "3164610": [],
        "8380809": [("2678129", "00D02D67C990")],
    }

    v1_devs = {loc.id: devices(loc.tcs) for loc in ec1.locations}
    v2_devs = {loc.id: devices(loc.tcs) for loc in ec2.locations}

    assert v1_devs == v2_devs
    assert v1_devs == {
        "2738909": {"3432521"},
        "3164610": None,  # this location has no devices (v1), nor gateway (v2)
        "8380809": {"3744415", "6860918"},
    }
