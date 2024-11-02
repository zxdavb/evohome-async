#!/usr/bin/env python3
"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from syrupy import SnapshotAssertion

import evohomeasync2 as evo2

from .conftest import FIXTURES_DIR
from .helpers import get_property_methods


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p.name
        for p in Path(FIXTURES_DIR).glob("*")
        if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("install", sorted(folders))


async def test_system_snapshot(
    evohome_v2: evo2.EvohomeClientNew,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    def serializable_attrs(obj: object) -> dict[str, Any]:
        result = {}
        for k in list(vars(obj).keys()) + get_property_methods(obj):
            if not k.startswith("_"):
                try:
                    result[k] = yaml.dump(getattr(obj, k))
                except TypeError:  # not all attrs are serializable
                    continue

        return result

    loc = evohome_v2.locations[0]
    assert serializable_attrs(loc) == snapshot(name="location")

    gwy = loc.gateways[0]
    assert serializable_attrs(gwy) == snapshot(name="gateway")

    tcs = gwy.control_systems[0]
    assert serializable_attrs(tcs) == snapshot(name="control_system")

    if dhw := tcs.hotwater:
        assert serializable_attrs(dhw) == snapshot(name="hot_water")

    zones = {z.id: serializable_attrs(z) for z in tcs.zones}
    assert yaml.dump(zones, indent=4) == snapshot(name="zones")
