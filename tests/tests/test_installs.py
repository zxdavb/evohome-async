#!/usr/bin/env python3
"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
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

    with patch("evohomeasync2.broker.Broker.get", broker_get(install)):
        evo = evo2.EvohomeClient(token_manager, token_manager.websession)

        await evo.login()

    assert evo

    loc = evo.locations[0]
    gwy = loc._gateways[0]
    tcs = gwy._control_systems[0]

    value = {
        "loc": {attr: getattr(loc, attr) for attr in get_property_methods(loc)},
        "gwy": {attr: getattr(gwy, attr) for attr in get_property_methods(gwy)},
        "tcs": {attr: getattr(tcs, attr) for attr in get_property_methods(tcs)},
    }

    snapshot.assert_match(str(value), install)
