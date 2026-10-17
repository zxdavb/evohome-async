"""Test the warnings logged by the v2 client."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from evohomeasync2 import EvohomeClient as EvohomeClientV2

from .conftest import FIXTURES_V2 as FIXTURES, auth_get

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from syrupy.assertion import SnapshotAssertion

    from evohome_cli.auth import TokenCacheManager


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    if "fixture_folder" in metafunc.fixturenames:
        metafunc.parametrize(
            "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
        )


async def test_system_warnings(
    credentials_manager: TokenCacheManager,
    fixture_folder: Path,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    with patch("evohomeasync2.auth.Auth.get", auth_get(fixture_folder)):
        ec2 = EvohomeClientV2(credentials_manager)

        with caplog.at_level(logging.WARNING):
            await ec2.setup()
            for loc in ec2.locations:
                await loc.get_status()

    assert caplog.record_tuples == snapshot
