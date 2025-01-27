"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from freezegun.api import FakeDatetime

from .common import get_property_methods
from .conftest import FIXTURES_V2

if TYPE_CHECKING:
    import pytest
    from freezegun.api import FrozenDateTimeFactory
    from syrupy import SnapshotAssertion

    from tests.conftest import EvohomeClientv2


def fake_datetime_representer(
    dumper: yaml.Dumper, data: FakeDatetime
) -> yaml.nodes.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data.isoformat())


yaml.add_representer(FakeDatetime, fake_datetime_representer)


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

    def serializable_attrs(obj: object) -> dict[str, Any]:
        result = {}
        for k in get_property_methods(obj):  # + list(vars(obj).keys()):
            if not k.startswith("_") and k != "zone_by_name":
                try:
                    result[k] = yaml.dump(getattr(obj, k))
                except TypeError:  # not all attrs are serializable
                    continue

        return result

    freezer.move_to("2025-01-01T00:00:00Z")

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
