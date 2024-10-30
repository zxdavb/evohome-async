#!/usr/bin/env python3
"""Tests for evohome-async - validate the schedule schemas."""

from __future__ import annotations

import json
from pathlib import Path

import voluptuous as vol

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


def _test_schedule_schema(file_name: str, schema: vol.Schema) -> dict:
    def read_dict_from_file(file_name: str) -> dict:
        with open(WORK_DIR.joinpath(file_name)) as f:
            data: dict = json.load(f)  # is camelCase, as per vendor's schema
        return data

    return schema(read_dict_from_file(file_name))  # type: ignore[no-any-return]


def _test_schema_schedule_dhw() -> None:
    get_sched = _test_schedule_schema("schedule_dhw_get.json", SCH_GET_SCHEDULE_DHW)
    put_sched = _test_schedule_schema("schedule_dhw_put.json", SCH_PUT_SCHEDULE_DHW)

    assert put_sched == convert_to_put_schedule(get_sched)
    assert get_sched == convert_to_get_schedule(put_sched)


def _test_schema_schedule_zone() -> None:
    get_sched = _test_schedule_schema("schedule_zone_get.json", SCH_GET_SCHEDULE_ZONE)
    put_sched = _test_schedule_schema("schedule_zone_put.json", SCH_PUT_SCHEDULE_ZONE)

    assert put_sched == convert_to_put_schedule(get_sched)
    assert get_sched == convert_to_get_schedule(put_sched)


def test_schema_schedule_dhw() -> None:
    """Test the schedule schema for dhw."""
    _test_schema_schedule_dhw()


def test_schema_schedule_zone() -> None:
    """Test the schedule schema for zones."""
    _test_schema_schedule_zone()
