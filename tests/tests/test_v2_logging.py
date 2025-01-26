"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import yaml
from freezegun.api import FakeDatetime

from tests.conftest import EvohomeClientv2

from .conftest import FIXTURES_V2, broker_get

if TYPE_CHECKING:
    import pytest
    from freezegun.api import FrozenDateTimeFactory
    from syrupy import SnapshotAssertion

    from tests.conftest import CredentialsManager


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


async def test_system_warnings(
    credentials_manager: CredentialsManager,
    fixture_folder: Path,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00Z")

    with patch("evohomeasync2.auth.Auth.get", broker_get(fixture_folder)):
        evo = EvohomeClientv2(credentials_manager)

        with caplog.at_level(logging.WARNING):
            await evo.update()

    assert caplog.record_tuples == snapshot
