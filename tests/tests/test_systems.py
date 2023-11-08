#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evohomeasync2.schema import SCH_FULL_CONFIG, SCH_LOCN_STATUS, SCH_USER_ACCOUNT

TEST_DIR = Path(__file__).resolve().parent
WORK_DIR = f"{TEST_DIR}/systems"


def pytest_generate_tests(metafunc: pytest.Metafunc):
    def id_fnc(folder_path: Path):
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", sorted(folders), ids=id_fnc)


def _test_schema(folder: Path, schema: str, file_name: str):
    if not Path(folder).joinpath(file_name).is_file():
        pytest.skip(f"No {file_name} in: {folder.name}")

    with open(Path(folder).joinpath(file_name)) as f:
        data: dict = json.load(f)

    _ = schema(data)


def test_user_account(folder: Path):
    """Test the user account schema against the corresponding JSON."""
    _test_schema(folder, SCH_USER_ACCOUNT, "user_account.json")


def test_user_locations(folder: Path):
    """Test the user locations config schema against the corresponding JSON."""
    _test_schema(folder, SCH_FULL_CONFIG, "user_locations.json")


def test_location_status(folder: Path):
    """Test the location status schema against the corresponding JSON."""
    for p in Path(folder).glob("status_*.json"):
        _test_schema(folder, SCH_LOCN_STATUS, p.name)
