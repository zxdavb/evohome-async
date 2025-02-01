"""Tests for evohome-async - validate the instantiation of entities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from .common import serializable_attrs
from .conftest import FIXTURES_V2

if TYPE_CHECKING:
    import pytest
    from freezegun.api import FrozenDateTimeFactory
    from syrupy import SnapshotAssertion

    from tests.conftest import EvohomeClientv2


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p
        for p in Path(FIXTURES_V2).glob("*")
        if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_system_snapshot(
    evohome_v2: EvohomeClientv2,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00Z")

    # architecture is: loc -> gwy -> tcs -> dhw|zon

    loc = evohome_v2.locations[0]
    assert serializable_attrs(loc) == snapshot(name="location")

    gwy = loc.gateways[0]
    assert serializable_attrs(gwy) == snapshot(name="gateway")

    tcs = gwy.systems[0]
    assert serializable_attrs(tcs) == snapshot(name="control_system")

    if dhw := tcs.hotwater:
        await dhw.get_schedule()
        assert serializable_attrs(dhw) == snapshot(name="hot_water")

    for z in tcs.zones:
        await z.get_schedule()

    zones = {z.id: serializable_attrs(z) for z in tcs.zones}
    assert yaml.dump(zones, indent=4) == snapshot(name="zones")
