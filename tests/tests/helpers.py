#!/usr/bin/env python3
"""Tests for evohome-async - helper functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import voluptuous as vol

TEST_DIR = Path(__file__).resolve().parent


def _test_schema(folder: Path, schema: vol.Schema, file_name: str) -> None:
    if not Path(folder).joinpath(file_name).is_file():
        pytest.skip(f"No {file_name} in: {folder.name}")

    with open(Path(folder).joinpath(file_name)) as f:
        data: dict = json.load(f)

    _ = schema(data)
