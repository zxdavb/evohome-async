#!/usr/bin/env python3
"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from syrupy import SnapshotAssertion

import evohomeasync2 as evo2

from .conftest import FIXTURES_DIR, TokenManager, broker_get
from .helpers import get_property_methods


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p.name
        for p in Path(FIXTURES_DIR).glob("*")
        if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("install", sorted(folders))


async def test_system_snapshot(
    install: str, token_manager: TokenManager, snapshot: SnapshotAssertion
) -> None:
    """Test the user account schema against the corresponding JSON."""

    def obj_to_dict(obj: object) -> dict[str, Any]:
        DEPRECATED_ATTRS = (  # attrs only in _Deprecated classes
            "activeFaults",
            "dhwId",
            "gatewayId",
            "locationId",
            "systemId",
            "zone_type",
            "zoneId",
        )
        return {
            attr: getattr(obj, attr)
            for attr in get_property_methods(obj)
            if attr not in DEPRECATED_ATTRS
        }

    with patch("evohomeasync2.session.Auth.get", broker_get(install)):
        evo = evo2.EvohomeClientNew(token_manager.websession, token_manager)

        await evo.login()

    assert evo

    loc = evo.locations[0]
    assert yaml.dump(obj_to_dict(loc), indent=4) == snapshot(name="location")

    gwy = loc._gateways[0]
    assert yaml.dump(obj_to_dict(gwy), indent=4) == snapshot(name="gateway")

    tcs = gwy._control_systems[0]
    assert yaml.dump(obj_to_dict(tcs), indent=4) == snapshot(name="control_system")

    dhw = tcs.hotwater
    assert yaml.dump(obj_to_dict(dhw), indent=4) == snapshot(name="hot_water")

    zones = {z.id: obj_to_dict(z) for z in tcs._zones}
    assert yaml.dump(zones, indent=4) == snapshot(name="zones")
