#!/usr/bin/env python3
"""Tests for evohome-async - validate the schedule schemas."""

from __future__ import annotations

from pathlib import Path

from evohomeasync2.schema.schedule import (
    SCH_GET_SCHEDULE_DHW,
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_ZONE,
    convert_to_get_schedule,
    convert_to_put_schedule,
)

from .conftest import JsonObjectType, load_fixture

SCHEDULES_DIR = Path(__file__).parent / "schedules"


def schedule_fixture(filename: str) -> JsonObjectType:
    return load_fixture(SCHEDULES_DIR / filename)  # type: ignore[return-value]


def test_schema_schedule_dhw() -> None:
    """Test the schedule schema for dhw."""

    get_sched = schedule_fixture("schedule_dhw_get.json")
    put_sched = schedule_fixture("schedule_dhw_put.json")

    assert get_sched == SCH_GET_SCHEDULE_DHW(get_sched)
    assert put_sched == SCH_PUT_SCHEDULE_DHW(put_sched)

    assert put_sched == convert_to_put_schedule(get_sched)
    assert get_sched == convert_to_get_schedule(put_sched)


def test_schema_schedule_zone() -> None:
    """Test the schedule schema for zones."""

    get_sched = schedule_fixture("schedule_zone_get.json")
    put_sched = schedule_fixture("schedule_zone_put.json")

    assert get_sched == SCH_GET_SCHEDULE_ZONE(get_sched)
    assert put_sched == SCH_PUT_SCHEDULE_ZONE(put_sched)

    assert put_sched == convert_to_put_schedule(get_sched)
    assert get_sched == convert_to_get_schedule(put_sched)
