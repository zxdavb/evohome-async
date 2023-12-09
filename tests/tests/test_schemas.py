#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from evohomeasync2 import ControlSystem
from evohomeasync2.schema import SCH_LOCN_STATUS
from evohomeasync2.schema.config import SCH_TEMPERATURE_CONTROL_SYSTEM, SCH_TIME_ZONE
from evohomeasync2.schema.const import (
    SZ_GATEWAYS,
    SZ_LOCATION_INFO,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TIME_ZONE,
)

from .helpers import TEST_DIR

WORK_DIR = f"{TEST_DIR}/schemas"


class GatewayStub:
    def __init__(self) -> None:
        self._broker = None
        self._logger = logging.getLogger(__name__)
        self.location = None


def pytest_generate_tests(metafunc: pytest.Metafunc):
    def id_fnc(folder_path: Path):
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", sorted(folders), ids=id_fnc)


# NOTE: JSON is not compliant with UserInfo schema, but is useful to test against TCS
def test_config_schemas(folder: Path):
    """Test the config schema for a location."""
    # Use pytest --log-cli-level=WARNING to see the output

    FILE_NAME = "config.json"

    if not Path(folder).joinpath(FILE_NAME).is_file():
        pytest.skip(f"No {FILE_NAME} in: {folder.name}")

    with open(Path(folder).joinpath(FILE_NAME)) as f:
        data: dict = json.load(f)

    _ = SCH_TIME_ZONE(data[SZ_LOCATION_INFO][SZ_TIME_ZONE])
    for gwy_config in data[SZ_GATEWAYS]:
        for tcs_config in gwy_config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            _ = SCH_TEMPERATURE_CONTROL_SYSTEM(tcs_config)
            _ = ControlSystem(GatewayStub(), tcs_config)


def test_status_schemas(folder: Path):
    """Test the status schema for a location."""

    FILE_NAME = "status.json"

    if not Path(folder).joinpath(FILE_NAME).is_file():
        pytest.skip(f"No {FILE_NAME} in: {folder.name}")

    with open(Path(folder).joinpath(FILE_NAME)) as f:
        data: dict = json.load(f)

    _ = SCH_LOCN_STATUS(data)
