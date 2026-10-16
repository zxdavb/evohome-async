"""Tests for evohome-async - validate the instantiation of entities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from .common import serializable_attrs
from .conftest import FIXTURES_V0 as FIXTURES

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from syrupy.assertion import SnapshotAssertion

    from evohomeasync import EvohomeClient as EvohomeClientV0


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_system_snapshot(
    evohome_v0: EvohomeClientV0,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    # architecture is: loc -> tcs -> dhw|zon (as for v2, but without gateways)

    for loc in evohome_v0.locations:  # is 0-many
        assert serializable_attrs(loc) == snapshot(name=f"loc_{loc.id}")

        if (tcs := loc.tcs) is None:  # is 0-1
            continue

        assert serializable_attrs(tcs) == snapshot(name=f"loc_{loc.id}_tcs")

        if dhw := tcs.hotwater:  # is 0-1
            assert serializable_attrs(dhw) == snapshot(name=f"loc_{loc.id}_dhw")

        zones = {z.id: serializable_attrs(z) for z in tcs.zones}
        assert yaml.dump(zones, indent=4) == snapshot(name=f"loc_{loc.id}_zon")
