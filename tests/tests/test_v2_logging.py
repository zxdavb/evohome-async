"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from tests.conftest import EvohomeClientV2

from .conftest import FIXTURES_V2 as FIXTURES, auth_get, load_fixture

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

    if "multi_location_fixtures" in metafunc.fixturenames:
        multi = [p for p in sorted(folders) if _num_locations(p) > 1]
        metafunc.parametrize(
            "multi_location_fixtures", multi, ids=(p.name for p in multi)
        )


def _num_locations(folder: Path) -> int:
    """Return the number of locations in a fixture (0 if it has no config)."""

    file = folder / "user_locations.json"
    return len(load_fixture(file)) if file.is_file() else 0


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
        evo = EvohomeClientV2(credentials_manager)

        with caplog.at_level(logging.WARNING):
            await evo.update()

    assert caplog.record_tuples == snapshot


async def test_multi_location_warning_once_per_config_load(
    credentials_manager: TokenCacheManager,
    multi_location_fixtures: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A multi-location warning should be emitted only once per config load."""

    num = _num_locations(multi_location_fixtures)
    warning = (
        f"There are {num} locations. Reduce the risk of exceeding API rate "
        "limits by individually updating only necessary locations."
    )

    def warnings() -> list[str]:
        msgs = [
            msg
            for logger, level, msg in caplog.record_tuples
            if logger == "evohomeasync2"
            and level == logging.WARNING
            and msg.startswith("There are")
        ]
        caplog.clear()
        return msgs

    with (
        patch("evohomeasync2.auth.Auth.get", auth_get(multi_location_fixtures)),
        caplog.at_level(logging.WARNING),
    ):
        evo = EvohomeClientV2(credentials_manager)

        await evo.update()  # config will be loaded: warn
        assert warnings() == [warning]

        await evo.update()  # status update only: don't warn again
        assert warnings() == []

        await evo.update(_reset_config=True)  # config reloaded: warn again
        assert warnings() == [warning]

        # test no warnings are given when status updates are skipped
        evo = EvohomeClientV2(credentials_manager)

        await evo.update(dont_update_status=True)  # no status updates: don't warn
        assert warnings() == []
