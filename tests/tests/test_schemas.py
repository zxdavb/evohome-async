#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evohomeasync2.schema import SCH_LOCN_STATUS
from evohomeasync2.schema.config import SCH_TEMPERATURE_CONTROL_SYSTEM, SCH_TIME_ZONE

from .helpers import TEST_DIR

WORK_DIR = f"{TEST_DIR}/schemas"


def pytest_generate_tests(metafunc: pytest.Metafunc):
    def id_fnc(folder_path: Path):
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", sorted(folders), ids=id_fnc)


# NOTE: JSON is not compliant with the schema, but data is useful to test against
def test_schemas_config(folder: Path):
    """Test the config schema for a location."""

    FILE_NAME = "config.json"

    if not Path(folder).joinpath(FILE_NAME).is_file():
        pytest.skip(f"No {FILE_NAME} in: {folder.name}")

    with open(Path(folder).joinpath(FILE_NAME)) as f:
        data: dict = json.load(f)

    _ = SCH_TIME_ZONE(data["locationInfo"]["timeZone"])
    for gwy_config in data["gateways"]:
        for tcs_config in gwy_config["temperatureControlSystems"]:
            _ = SCH_TEMPERATURE_CONTROL_SYSTEM(tcs_config)


def test_schemas_status(folder: Path):
    """Test the status schema for a location."""

    FILE_NAME = "status.json"

    if not Path(folder).joinpath(FILE_NAME).is_file():
        pytest.skip(f"No {FILE_NAME} in: {folder.name}")

    with open(Path(folder).joinpath(FILE_NAME)) as f:
        data: dict = json.load(f)

    _ = SCH_LOCN_STATUS(data)
