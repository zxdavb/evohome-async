#!/usr/bin/env python3
"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from pytest_snapshot.plugin import Snapshot  # type: ignore[import-untyped]

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


async def test_system_snapshot(  # type: ignore[no-any-unimported]
    install: str, token_manager: TokenManager, snapshot: Snapshot
) -> None:
    """Test the user account schema against the corresponding JSON."""

    def obj_to_dict(obj: object) -> dict[str, Any]:
        return {
            attr: getattr(obj, attr)
            for attr in get_property_methods(obj)
            if attr not in ("zoneId", "zone_type")
        }

    with patch("evohomeasync2.broker.Broker.get", broker_get(install)):
        evo = evo2.EvohomeClient(token_manager, token_manager.websession)

        await evo.login()

    assert evo

    loc = evo.locations[0]
    snapshot.assert_match(yaml.dump(obj_to_dict(loc), indent=4), "location.yml")

    gwy = loc._gateways[0]
    snapshot.assert_match(yaml.dump(obj_to_dict(gwy), indent=4), "gateway.yml")

    tcs = gwy._control_systems[0]
    snapshot.assert_match(yaml.dump(obj_to_dict(tcs), indent=4), "control_system.yml")

    dhw = tcs.hotwater
    snapshot.assert_match(yaml.dump(obj_to_dict(dhw), indent=4), "hot_water.yml")

    zones = {z.zoneId: obj_to_dict(z) for z in tcs._zones}
    snapshot.assert_match(yaml.dump(zones, indent=4), "zones.yml")
