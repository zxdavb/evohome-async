"""Tests for evohome-async - validate the instantiation of entities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from .common import serializable_attrs
from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from syrupy.assertion import SnapshotAssertion

    from evohomeasync2.control_system import ControlSystem
    from evohomeasync2.gateway import Gateway
    from evohomeasync2.location import Location
    from tests.conftest import EvohomeClientV2


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


def _first_system(
    evohome_v2: EvohomeClientV2,
) -> tuple[Location, Gateway, ControlSystem] | None:
    for location in evohome_v2.locations:
        for gateway in location.gateways:
            if gateway.systems:
                return location, gateway, gateway.systems[0]
    return None


async def test_system_snapshot(
    evohome_v2: EvohomeClientV2,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    # architecture is: loc -> gwy -> tcs -> dhw|zon

    for loc in evohome_v2.locations:  # is 0-many
        assert serializable_attrs(loc) == snapshot(name=f"loc_{loc.id}")

        for gwy in loc.gateways:  # 0is -1
            assert serializable_attrs(gwy) == snapshot(name=f"loc_{loc.id}_gwy")

            for tcs in gwy.systems:  # is 0-1 (may be exactly 1)
                assert serializable_attrs(tcs) == snapshot(name=f"loc_{loc.id}_tcs")

                if dhw := tcs.hotwater:  # is 0-1
                    await dhw.get_schedule()
                    assert serializable_attrs(dhw) == snapshot(name=f"loc_{loc.id}_dhw")

                for z in tcs.zones:  # is 1-12
                    await z.get_schedule()  # needed for serializable_attrs(z), below

                zones = {z.id: serializable_attrs(z) for z in tcs.zones}
                assert yaml.dump(zones, indent=4) == snapshot(name=f"loc_{loc.id}_zon")


async def _test_system_schedules(
    evohome_v2: EvohomeClientV2,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    hierarchy = _first_system(evohome_v2)
    if hierarchy is None:
        pytest.skip("Fixture has no location->gateway->TCS hierarchy")

    _, _, tcs = hierarchy

    schedules = await tcs.get_schedules()

    assert schedules == snapshot(name=f"{tcs.id}_schedules")  # needs freezer

    with patch("_evohome.auth.AbstractAuth.request"):
        result = await tcs.set_schedules(schedules)
    assert result is True

    with patch("_evohome.auth.AbstractAuth.request"):
        result = await tcs.set_schedules(schedules, match_by_name=True)
    assert result is True

    data = [(z.this_switchpoint, z.next_switchpoint) for z in tcs.zones]
    if dhw := tcs.hotwater:
        data.append((dhw.this_switchpoint, dhw.next_switchpoint))

    assert schedules == snapshot(name="switchpoints")  # needs freezer
