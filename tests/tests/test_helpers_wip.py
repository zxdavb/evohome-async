#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the helper functions."""

from __future__ import annotations

import json
from pathlib import Path

# import pytest
from evohomeasync2.schema.schedule import (
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE_ZONE,
    convert_to_get_schedule,
    convert_to_put_schedule,
)

from .helpers import TEST_DIR

WORK_DIR = Path(f"{TEST_DIR}/schedules")


# def pytest_generate_tests(metafunc: pytest.Metafunc):
#     def id_fnc(folder_path: Path):
#         return folder_path.name

#     files = [
#         f for f in Path(WORK_DIR).glob("*.json") if not f.name.startswith("_")
#     ]
#     metafunc.parametrize("file", sorted(files), ids=id_fnc)


def test_schedule_to_pascal_case() -> None:
    """Convert a schedule to snake_case, and back again."""

    get_schedule = json.load(
        Path(f"{TEST_DIR}/systems/system_001/schedule_zone.json").open()
    )
    assert get_schedule == SCH_GET_SCHEDULE_ZONE(get_schedule)

    put_schedule = convert_to_put_schedule(get_schedule)
    assert put_schedule == SCH_PUT_SCHEDULE_ZONE(put_schedule)

    assert get_schedule == convert_to_get_schedule(put_schedule)
