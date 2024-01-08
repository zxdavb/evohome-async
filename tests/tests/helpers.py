#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import voluptuous as vol  # type: ignore[import-untyped]

TEST_DIR = Path(__file__).resolve().parent


def _test_schema(folder: Path, schema: vol.Schema, file_name: str):  # type: ignore[no-any-unimported]
    if not Path(folder).joinpath(file_name).is_file():
        pytest.skip(f"No {file_name} in: {folder.name}")

    with open(Path(folder).joinpath(file_name)) as f:
        data: dict = json.load(f)

    _ = schema(data)
