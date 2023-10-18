#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""

import json
from pathlib import Path
import pytest

from schema import SCH_LOCN_CONFIG, SCH_LOCN_STATUS


TEST_DIR = Path(__file__).resolve().parent
WORK_DIR = f"{TEST_DIR}/schemas"


def pytest_generate_tests(metafunc: pytest.Metafunc):
    def id_fnc(folder_path: Path):
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", folders, ids=id_fnc)


def _test_schema(folder: Path, schema: str, file_name: str):
    if not Path(folder).joinpath(file_name).is_file():
        pytest.skip(f"No {file_name} in: {folder.name}")

    with open(Path(folder).joinpath(file_name)) as f:
        data: dict = json.load(f)

    _ = schema(data)


def test_schemas_config(folder: Path):
    _test_schema(folder, SCH_LOCN_CONFIG, "locn_config.json")


def test_schemas_status(folder: Path):
    _test_schema(folder, SCH_LOCN_STATUS, "locn_status.json")
