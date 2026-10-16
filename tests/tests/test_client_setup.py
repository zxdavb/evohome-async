"""Tests for evohome-async - the setup() and get_status() methods of both clients."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2
from _evohome import exceptions as exc
from tests.common import get_loc, get_tcs, get_zon

from .conftest import FIXTURES_V0, FIXTURES_V2, auth_get

if TYPE_CHECKING:
    from _evohome.helpers import Validator
    from evohome_cli.auth import TokenCacheManager


async def test_v2_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config only, and Location.get_status() the status."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        evo = evo2.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = evo.locations

        await evo.setup()

        loc = get_loc(evo)  # the config is available...
        zone = get_zon(evo)
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
        evo = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then Location\.get_status\(\)"
        ):
            await evo.update()

        zone = get_zon(evo)
        assert zone is not None  # the default/ fixture has zones
        assert zone.status["zone_id"] == zone.id  # update() got the status too

        loc = get_loc(evo)
        with pytest.warns(DeprecationWarning, match=r"use \.get_status\(\)"):
            status = await loc.update()
        assert status == await loc.get_status()


async def test_v2_update_without_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update(dont_update_status=True) still gets the config only (as setup())."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        evo = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then Location\.get_status\(\)"
        ):
            await evo.update(dont_update_status=True)

    zone = get_zon(evo)
    assert zone is not None  # the default/ fixture has zones

    with pytest.raises(exc.EvohomeError):
        _ = zone.status


async def test_v1_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config and, as v1 has them in one GET, the status."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V0 / "default")):
        evo = evo1.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = evo.locations

        await evo.setup()

        assert get_tcs(evo).zones[0].temperature is not None


async def test_v1_get_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test get_status() gets the latest status every time it is called."""

    mock_get = auth_get(FIXTURES_V0 / "default")
    calls: list[str] = []

    async def get(self: object, url: str, /, schema: Validator[Any]) -> object:
        calls.append(url)
        return await mock_get(self, url, schema)

    with patch("evohomeasync.auth.Auth.get", get):
        evo = evo1.EvohomeClient(credentials_manager)

        result = await evo.get_status()  # also gets the config, as it is first
        with pytest.warns(
            DeprecationWarning, match=r"use \.setup\(\), then \.get_status\(\)"
        ):
            assert result == await evo.update()

        calls.clear()
        await evo.get_status()

    assert len(calls) == 1
    assert calls[0].startswith("locations?userId=")


async def test_v2_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location.tcs is the TCS of a location (each has 0-1 TCSs)."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "system_004")):
        evo = evo2.EvohomeClient(credentials_manager)
        await evo.setup()

    *locs, loc_sans_gwy = evo.locations  # the last location has no gateway

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
        evo = evo2.EvohomeClient(credentials_manager)
        await evo.setup()

    assert get_loc(evo).tcs is None


async def test_v1_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test Location.tcs has the location's devices, or is None if it has none."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V0 / "default")):
        evo = evo1.EvohomeClient(credentials_manager)
        await evo.setup()

    loc = get_loc(evo)
    assert (tcs := loc.tcs) is not None
    assert tcs.hotwater is not None  # the default/ fixture has a DHW

    dev_ids = {str(d["device_id"]) for d in loc.config["devices"]}
    assert dev_ids == set(tcs.zone_by_id) | {tcs.hotwater.id}

    config = copy.deepcopy(loc.config)
    config["devices"] = []

    assert (await evo1.entities.create_location(evo, config)).tcs is None


async def test_vx_location_tcs(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test each location's TCS has the same DHW/zones via the v1 and v2 APIs.

    The system_009/ fixtures are of the same (multi-location) account, captured at the
    same time. Its locations are in a different order for each API.
    """

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V0 / "system_009")):
        evo_v1 = evo1.EvohomeClient(credentials_manager)
        await evo_v1.setup()

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "system_009")):
        evo_v2 = evo2.EvohomeClient(credentials_manager)
        await evo_v2.setup()

    def devices(tcs: evo1.ControlSystem | evo2.ControlSystem | None) -> set[str] | None:
        if tcs is None:
            return None
        dhw = {tcs.hotwater.id} if tcs.hotwater else set()
        return {z.id for z in tcs.zones} | dhw

    v1_devs = {loc.id: devices(loc.tcs) for loc in evo_v1.locations}
    v2_devs = {loc.id: devices(loc.tcs) for loc in evo_v2.locations}

    assert v1_devs == v2_devs
    assert v1_devs == {
        "2738909": {"3432521"},
        "3164610": None,  # this location has no devices (v1), nor gateway (v2)
        "8380809": {"3744415", "6860918"},
    }
