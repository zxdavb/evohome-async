"""Tests for evohome-async - validate the instantiation of entities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from .common import serializable_attrs
from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from syrupy.assertion import SnapshotAssertion

    from evohomeasync import EvohomeClient as EvohomeClientV1


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
    ec1: EvohomeClientV1,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    # architecture is: loc -> gwy -> tcs -> dhw|zon (as for v2)

    for loc in ec1.locations:  # is 0-many
        assert serializable_attrs(loc) == snapshot(name=f"loc_{loc.id}")

        for gwy in loc.gateways:  # is 0-1
            assert serializable_attrs(gwy) == snapshot(name=f"loc_{loc.id}_gwy")

            for tcs in gwy.systems:  # is exactly 1
                assert loc.tcs is tcs
                assert serializable_attrs(tcs) == snapshot(name=f"loc_{loc.id}_tcs")

                if dhw := tcs.hotwater:  # is 0-1
                    assert serializable_attrs(dhw) == snapshot(name=f"loc_{loc.id}_dhw")

                zones = {z.id: serializable_attrs(z) for z in tcs.zones}
                assert yaml.dump(zones, indent=4) == snapshot(name=f"loc_{loc.id}_zon")
