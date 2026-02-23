"""Tests for evohome-async - validate the schedule schemas."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td, timezone as tz
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest

from _evohome.helpers import convert_keys_to_snake_case
from evohomeasync2 import exceptions as exc
from evohomeasync2.schemas import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE, DayOfWeek
from evohomeasync2.zone import _dt_to_dow_and_tod, _find_switchpoints

from .conftest import JsonObjectType, load_fixture

if TYPE_CHECKING:
    from evohomeasync2.schemas import DayOfWeekT

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


def test_schema_schedule_dhw() -> None:
    """Test the schedule schema for dhw."""

    get_sched = schedule_file("schedule_dhw_get.json")
    _ = schedule_file("schedule_dhw_put.json")

    assert get_sched == TCC_GET_DHW_SCHEDULE(get_sched)
    # assert put_sched == TCC_PUT_DHW_SCHEDULE(put_sched)

    # assert put_sched == convert_to_put_schedule(get_sched)
    # assert get_sched == convert_to_get_schedule(put_sched)


def test_schema_schedule_zone() -> None:
    """Test the schedule schema for zones."""

    get_sched = schedule_file("schedule_zone_get.json")
    _ = schedule_file("schedule_zone_put.json")

    assert get_sched == TCC_GET_ZON_SCHEDULE(get_sched)
    # assert put_sched == TCC_PUT_ZON_SCHEDULE(put_sched)

    # assert put_sched == convert_to_put_schedule(get_sched)
    # assert get_sched == convert_to_get_schedule(put_sched)


def test_find_switchpoints() -> None:
    """Test the find_switchpoints method."""

    schedule: list[DayOfWeekT] = SCHEDULE["daily_schedules"]  # type: ignore[assignment]

    assert _find_switchpoints(schedule, DayOfWeek.MONDAY, "00:00:00") == (
        {"heat_setpoint": 14.8, "time_of_day": "21:30:00"},
        -1,
        {"heat_setpoint": 23.2, "time_of_day": "06:30:00"},
        0,
    )

    assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, "07:59:59") == (
        {"heat_setpoint": 19.2, "time_of_day": "06:30:00"},
        0,
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, "08:00:00") == (
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
        {"heat_setpoint": 19.3, "time_of_day": "17:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, "08:00:01") == (
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
        {"heat_setpoint": 19.3, "time_of_day": "17:00:00"},
        0,
    )

    assert _find_switchpoints(schedule, DayOfWeek.SUNDAY, "23:59:59") == (
        {"heat_setpoint": 14.8, "time_of_day": "21:30:00"},
        0,
        {"heat_setpoint": 23.2, "time_of_day": "06:30:00"},
        1,
    )


def test_find_switchpoints_invalid_day() -> None:
    """Test _find_switchpoints with an invalid day_of_week value."""

    schedule: list[DayOfWeekT] = SCHEDULE["daily_schedules"]  # type: ignore[assignment]

    with pytest.raises(TypeError, match="Invalid parameter"):
        _find_switchpoints(schedule, "Montag", "08:00:00")  # type: ignore[arg-type]


def test_find_switchpoints_empty_schedule() -> None:
    """Test _find_switchpoints raises InvalidScheduleError on empty schedule."""

    with pytest.raises(exc.InvalidScheduleError, match="daily schedules are empty"):
        _find_switchpoints([], DayOfWeek.MONDAY, "08:00:00")


@pytest.mark.parametrize(
    ("dtm", "tz_info", "expected_dow", "expected_tod"),
    [
        # Monday morning UTC, stays Monday in UTC
        (
            dt(2026, 2, 23, 8, 30, tzinfo=UTC),  # Monday
            UTC,
            DayOfWeek.MONDAY,
            "08:30",
        ),
        # Sunday 23:30 UTC -> Monday 00:30 in UTC+1
        (
            dt(2026, 2, 22, 23, 30, tzinfo=UTC),  # Sunday in UTC
            tz(offset=td(hours=1)),  # UTC+1
            DayOfWeek.MONDAY,
            "00:30",
        ),
        # Monday 00:30 UTC -> Sunday 23:30 in UTC-1
        (
            dt(2026, 2, 23, 0, 30, tzinfo=UTC),  # Monday in UTC
            tz(offset=td(hours=-1)),  # UTC-1
            DayOfWeek.SUNDAY,
            "23:30",
        ),
        # Friday in a named timezone
        (
            dt(2026, 2, 27, 12, 0, tzinfo=UTC),  # Friday
            ZoneInfo("Europe/London"),  # UTC+0 in February
            DayOfWeek.FRIDAY,
            "12:00",
        ),
        # Saturday in Berlin (UTC+1 in winter)
        (
            dt(2026, 2, 28, 23, 45, tzinfo=UTC),  # Saturday 23:45 UTC
            ZoneInfo("Europe/Berlin"),  # UTC+1
            DayOfWeek.SUNDAY,
            "00:45",
        ),
    ],
)
def test_dt_to_dow_and_tod(
    dtm: dt,
    tz_info: tz,
    expected_dow: DayOfWeek,
    expected_tod: str,
) -> None:
    """Test _dt_to_dow_and_tod returns locale-independent day names."""

    dow, tod = _dt_to_dow_and_tod(dtm, tz_info)

    assert dow == expected_dow
    assert dow in DayOfWeek  # always a valid enum member
    assert tod == expected_tod
