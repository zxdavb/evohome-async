#!/usr/bin/env python3
"""Tests for evohome-async - validate the helper functions."""

from __future__ import annotations

import json
from pathlib import Path

from evohomeasync2.schema.schedule import (
    SCH_GET_SCHEDULE_DHW,
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE_DHW,
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
#     metafunc.parametrize("path", sorted(files), ids=id_fnc)


def test_get_schedule_zon() -> None:
    """Convert a zone's get schedule to snake_case, and back again."""

    # th = Path(f"{TEST_DIR}/systems_0/system_001/schedule_zone.json")
    path = Path(f"{WORK_DIR}/schedule_zone_get.json")

    with open(path) as f:
        get_schedule = json.load(f)

    assert get_schedule == SCH_GET_SCHEDULE_ZONE(get_schedule)

    put_schedule = convert_to_put_schedule(get_schedule)
    assert put_schedule == SCH_PUT_SCHEDULE_ZONE(put_schedule)

    assert get_schedule == convert_to_get_schedule(put_schedule)


def test_get_schedule_dhw() -> None:
    """Convert a dhw's get schedule to snake_case, and back again."""

    path = Path(f"{WORK_DIR}/schedule_dhw_get.json")

    with open(path) as f:
        get_schedule = json.load(f)

    assert get_schedule == SCH_GET_SCHEDULE_DHW(get_schedule)

    put_schedule = convert_to_put_schedule(get_schedule)
    assert put_schedule == SCH_PUT_SCHEDULE_DHW(put_schedule)

    assert get_schedule == convert_to_get_schedule(put_schedule)
