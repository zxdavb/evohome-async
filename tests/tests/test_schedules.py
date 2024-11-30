#!/usr/bin/env python3
"""Tests for evohome-async - validate the schedule schemas."""

from __future__ import annotations

from pathlib import Path

from evohome.helpers import convert_keys_to_snake_case
from evohomeasync2.schemas import SCH_GET_SCHEDULE_DHW, SCH_GET_SCHEDULE_ZONE

from .conftest import JsonObjectType, load_fixture

SCHEDULES_DIR = Path(__file__).parent / "schedules"


def schedule_file(filename: str) -> JsonObjectType:
    return load_fixture(SCHEDULES_DIR / filename)  # type: ignore[return-value]


SCHEDULE = convert_keys_to_snake_case(
    {
        "dailySchedules": [
            {
                "dayOfWeek": "Monday",
                "switchpoints": [
                    {"heatSetpoint": 23.2, "timeOfDay": "06:30:00"},
                    {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Tuesday",
                "switchpoints": [
                    {"heatSetpoint": 19.2, "timeOfDay": "06:30:00"},
                    {"heatSetpoint": 18.2, "timeOfDay": "08:00:00"},
                    {"heatSetpoint": 19.3, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Wednesday",
                "switchpoints": [
                    {"heatSetpoint": 19.1, "timeOfDay": "06:30:00"},
                    {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Thursday",
                "switchpoints": [
                    {"heatSetpoint": 19.1, "timeOfDay": "06:30:00"},
                    {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Friday",
                "switchpoints": [
                    {"heatSetpoint": 19.1, "timeOfDay": "06:30:00"},
                    {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Saturday",
                "switchpoints": [
                    {"heatSetpoint": 19.1, "timeOfDay": "07:30:00"},
                    {"heatSetpoint": 18.5, "timeOfDay": "11:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
                ],
            },
            {
                "dayOfWeek": "Sunday",
                "switchpoints": [
                    {"heatSetpoint": 19.1, "timeOfDay": "07:30:00"},
                    {"heatSetpoint": 18.5, "timeOfDay": "11:00:00"},
                    {"heatSetpoint": 19.1, "timeOfDay": "17:00:00"},
                    {"heatSetpoint": 14.8, "timeOfDay": "21:30:00"},
                ],
            },
        ]
    }
)


def _test_schema_schedule_dhw() -> None:
    """Test the schedule schema for dhw."""

    get_sched = schedule_file("schedule_dhw_get.json")
    _ = schedule_file("schedule_dhw_put.json")

    assert get_sched == SCH_GET_SCHEDULE_DHW(get_sched)
    # assert put_sched == SCH_PUT_SCHEDULE_DHW(put_sched)

    # assert put_sched == convert_to_put_schedule(get_sched)
    # assert get_sched == convert_to_get_schedule(put_sched)


def _test_schema_schedule_zone() -> None:
    """Test the schedule schema for zones."""

    get_sched = schedule_file("schedule_zone_get.json")
    _ = schedule_file("schedule_zone_put.json")

    assert get_sched == SCH_GET_SCHEDULE_ZONE(get_sched)
    # assert put_sched == SCH_PUT_SCHEDULE_ZONE(put_sched)

    # assert put_sched == convert_to_put_schedule(get_sched)
    # assert get_sched == convert_to_get_schedule(put_sched)


def test_find_switchpoints() -> None:
    """Test the find_switchpoints method."""

    from evohomeasync2.zone import _find_switchpoints

    schedule = SCHEDULE["daily_schedules"]

    assert _find_switchpoints(schedule, "Monday", "00:00:00") == (
        {"heat_setpoint": 14.8, "time_of_day": "21:30:00"},
        -1,
        {"heat_setpoint": 23.2, "time_of_day": "06:30:00"},
        0,
    )

    assert _find_switchpoints(schedule, "Tuesday", "07:59:59") == (
        {"heat_setpoint": 19.2, "time_of_day": "06:30:00"},
        0,
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, "Tuesday", "08:00:00") == (
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
        {"heat_setpoint": 19.3, "time_of_day": "17:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, "Tuesday", "08:00:01") == (
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
        {"heat_setpoint": 19.3, "time_of_day": "17:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, "Sunday", "23:59:59") == (
        {"heat_setpoint": 14.8, "time_of_day": "21:30:00"},
        0,
        {"heat_setpoint": 23.2, "time_of_day": "06:30:00"},
        1,
    )
