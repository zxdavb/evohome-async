"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path

import pytest

from evohomeasync2.schemas import (
    TCC_GET_USR_ACCOUNT,
    TCC_GET_USR_LOCATIONS,
    factory_loc_status,
)

from .common import assert_schema
from .conftest import FIXTURES_V2 as FIXTURES


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


def test_user_account(fixture_folder: Path) -> None:
    """Test the user account schema against the corresponding JSON."""

    assert_schema(fixture_folder, TCC_GET_USR_ACCOUNT, "user_account.json")


def test_user_locations(fixture_folder: Path) -> None:
    """Test the user locations config schema against the corresponding JSON."""

    assert_schema(fixture_folder, TCC_GET_USR_LOCATIONS, "user_locations.json")


def test_location_status(fixture_folder: Path) -> None:
    """Test the location status schema against the corresponding JSON."""

    SCH_STATUS = factory_loc_status()

    for p in Path(fixture_folder).glob("status_*.json"):
        assert_schema(fixture_folder, SCH_STATUS, p.name)
