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
    from pathlib import Path

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


async def test_v2_update_is_unchanged(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update() is still setup() plus the status of every location."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        ec2 = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then Location\.get_status\(\)"
        ):
            await ec2.update()

        zone = get_zon(ec2)
        assert zone is not None  # the default/ fixture has zones
        assert zone.status["zone_id"] == zone.id  # update() got the status too

        loc = get_loc(ec2)
        with pytest.warns(DeprecationWarning, match=r"use \.get_status\(\)"):
            status = await loc.update()
        assert status == await loc.get_status()


async def test_v2_update_without_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update(dont_update_status=True) still gets the config only (as setup())."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        ec2 = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then Location\.get_status\(\)"
        ):
            await ec2.update(dont_update_status=True)

    zone = get_zon(ec2)
    assert zone is not None  # the default/ fixture has zones

    with pytest.raises(exc.EvohomeError):
        _ = zone.status


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

        result = await ec1.get_status()  # also gets the config, as it is first
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then \.get_status\(\)"
        ):
            assert result == await ec1.update()

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


@pytest.mark.parametrize(
    ("evo_cls", "target", "fixtures"),
    [
        pytest.param(evo1.EvohomeClient, "evohomeasync", FIXTURES_V1, id="v1"),
        pytest.param(evo2.EvohomeClient, "evohomeasync2", FIXTURES_V2, id="v2"),
    ],
)
async def test_vx_client_tcs(
    credentials_manager: TokenCacheManager,
    evo_cls: type[evo1.EvohomeClient | evo2.EvohomeClient],
    target: str,
    fixtures: Path,
) -> None:
    """Test the deprecated EvohomeClient.tcs is the TCS of the single location."""

    with patch(f"{target}.auth.Auth.get", auth_get(fixtures / "default")):
        ec = evo_cls(credentials_manager)
        await ec.setup()

    with pytest.warns(DeprecationWarning, match=r"use Location\.tcs"):
        tcs = ec.tcs

    assert tcs is ec.locations[0].tcs is not None


@pytest.mark.parametrize(
    ("evo_cls", "target", "fixture", "match"),
    [
        pytest.param(
            evo1.EvohomeClient,
            "evohomeasync",
            FIXTURES_V1 / "system_009",
            "not a single location",
            id="v1_multi_location",
        ),
        pytest.param(
            evo2.EvohomeClient,
            "evohomeasync2",
            FIXTURES_V2 / "system_009",
            "not a single location",
            id="v2_multi_location",
        ),
        pytest.param(
            evo2.EvohomeClient,
            "evohomeasync2",
            FIXTURES_V2 / "null_system_1",
            "has no TCS",
            id="v2_no_tcs",
        ),
    ],
)
async def test_vx_client_tcs_raises(
    credentials_manager: TokenCacheManager,
    evo_cls: type[evo1.EvohomeClient | evo2.EvohomeClient],
    target: str,
    fixture: Path,
    match: str,
) -> None:
    """Test the deprecated EvohomeClient.tcs raises if there is no single TCS."""

    with patch(f"{target}.auth.Auth.get", auth_get(fixture)):
        ec = evo_cls(credentials_manager)
        await ec.setup()

    with (
        pytest.warns(DeprecationWarning, match=r"use Location\.tcs"),
        pytest.raises(exc.ClientStateError, match=match),
    ):
        _ = ec.tcs


async def test_v1_location_get_temperatures(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test the deprecated v1 Location.get_temperatures() is that of its TCS."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V1 / "default")):
        ec1 = evo1.EvohomeClient(credentials_manager)
        await ec1.setup()

    loc = ec1.locations[0]
    assert loc.tcs is not None

    with pytest.warns(DeprecationWarning, match=r"use Location\.tcs\.get_temp"):
        temps = await loc.get_temperatures(dont_update_status=True)

    assert temps == await loc.tcs.get_temperatures(dont_update_status=True)
    assert temps  # the default fixture has zones


async def test_v1_location_get_temperatures_raises(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test the deprecated v1 Location.get_temperatures() raises if it has no TCS."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V1 / "system_009")):
        ec1 = evo1.EvohomeClient(credentials_manager)
        await ec1.setup()

    loc = ec1.location_by_id["3164610"]  # this location has no devices
    assert loc.tcs is None

    with (
        pytest.warns(DeprecationWarning, match=r"use Location\.tcs\.get_temp"),
        pytest.raises(exc.ClientStateError, match="has no TCS"),
    ):
        await loc.get_temperatures(dont_update_status=True)
