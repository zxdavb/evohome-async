#!/usr/bin/env python3
"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from pathlib import Path

import pytest

import evohomeasync2 as evo2
from evohomeasync2.schema import SCH_GET_USER_ACCOUNT, SCH_GET_USER_LOCATIONS

from .common import TEST_DIR, test_schema

WORK_DIR = f"{TEST_DIR}/systems_0"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    def id_fnc(folder_path: Path) -> str:
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", sorted(folders), ids=id_fnc)


def test_user_account(folder: Path) -> None:
    """Test the user account schema against the corresponding JSON."""
    test_schema(folder, SCH_GET_USER_ACCOUNT, "user_account.json")


def test_user_locations(folder: Path) -> None:
    """Test the user locations config schema against the corresponding JSON."""
    test_schema(folder, SCH_GET_USER_LOCATIONS, "user_locations.json")


def test_location_status(folder: Path) -> None:
    """Test the location status schema against the corresponding JSON."""
    for p in Path(folder).glob("status_*.json"):
        test_schema(folder, evo2.Location.STATUS_SCHEMA, p.name)
