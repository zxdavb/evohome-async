"""Test the schedule schemas."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td, timezone as tz
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest

from _evohome.helpers import convert_keys_to_snake_case
from evohomeasync2 import exceptions as exc
from evohomeasync2.const import DayOfWeek
from evohomeasync2.schemas.schedule import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE
from evohomeasync2.zone import Zone, _dt_to_dow_and_tod, _find_switchpoints

from .conftest import JsonObjectType, load_fixture

if TYPE_CHECKING:
    from collections.abc import Callable

    from evohomeasync2.typedefs import EvoZonScheduleDayOfWeekT

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

    get_sched = schedule_file("schedule_dhw.json")

    assert get_sched == TCC_GET_DHW_SCHEDULE(get_sched)


def test_schema_schedule_zone() -> None:
    """Test the schedule schema for zones."""

    get_sched = schedule_file("schedule_zone.json")

    assert get_sched == TCC_GET_ZON_SCHEDULE(get_sched)


def test_find_switchpoints() -> None:
    """Test the find_switchpoints method."""

    schedule: list[EvoZonScheduleDayOfWeekT] = SCHEDULE["daily_schedules"]  # type: ignore[assignment]

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


def _schedule() -> list[EvoZonScheduleDayOfWeekT]:
    """Return SCHEDULE's days, as validated by the zone's schema (so typed)."""
    return Zone.SCH_SCHEDULE(SCHEDULE)["daily_schedules"]


def test_find_switchpoints_within_its_first_minute() -> None:
    """Test a switchpoint is this one from its start (not from a minute later)."""

    schedule = _schedule()

    for time_of_day in ("08:00:00", "08:00:30", "08:00:59"):
        assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, time_of_day) == (
            {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
            0,
            {"heat_setpoint": 19.3, "time_of_day": "17:00:00"},
            0,
        ), time_of_day


def test_find_switchpoints_days_not_in_order() -> None:
    """Test the days are found by their day_of_week, not their position."""

    schedule = list(reversed(_schedule()))

    assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, "07:59:59") == (
        {"heat_setpoint": 19.2, "time_of_day": "06:30:00"},
        0,
        {"heat_setpoint": 18.2, "time_of_day": "08:00:00"},
        0,
    )


@pytest.mark.parametrize(
    "days",
    [
        pytest.param(  # Tuesday is absent
            lambda d: [x for x in d if x["day_of_week"] != DayOfWeek.TUESDAY],
            id="absent",
        ),
        pytest.param(  # Tuesday has no switchpoints
            lambda d: [
                x if x["day_of_week"] != DayOfWeek.TUESDAY else x | {"switchpoints": []}
                for x in d
            ],
            id="empty",
        ),
    ],
)
def test_find_switchpoints_day_without_switchpoints(
    days: Callable[[list[EvoZonScheduleDayOfWeekT]], list[EvoZonScheduleDayOfWeekT]],
) -> None:
    """Test a day without switchpoints is skipped (this is earlier, next is later)."""

    schedule = days(_schedule())

    assert _find_switchpoints(schedule, DayOfWeek.TUESDAY, "12:00:00") == (
        {"heat_setpoint": 14.9, "time_of_day": "21:30:00"},  # Monday's last
        -1,
        {"heat_setpoint": 19.1, "time_of_day": "06:30:00"},  # Wednesday's first
        1,
    )


def test_find_switchpoints_one_day_only() -> None:
    """Test a schedule with switchpoints on only one day (they repeat weekly)."""

    schedule: list[EvoZonScheduleDayOfWeekT] = [
        {
            "day_of_week": DayOfWeek.MONDAY,
            "switchpoints": [{"heat_setpoint": 21.0, "time_of_day": "06:30:00"}],
        }
    ]

    assert _find_switchpoints(schedule, DayOfWeek.MONDAY, "05:00:00") == (
        {"heat_setpoint": 21.0, "time_of_day": "06:30:00"},
        -7,  # i.e. a week ago
        {"heat_setpoint": 21.0, "time_of_day": "06:30:00"},
        0,
    )


def test_find_switchpoints_no_switchpoints() -> None:
    """Test _find_switchpoints raises InvalidGetScheduleError if no day has any."""

    schedule: list[EvoZonScheduleDayOfWeekT] = [
        {"day_of_week": d, "switchpoints": []} for d in DayOfWeek
    ]

    with pytest.raises(exc.InvalidGetScheduleError) as err:
        _find_switchpoints(schedule, DayOfWeek.MONDAY, "08:00:00")

    assert err.value.reason is exc.ResponseErrorReason.SWITCHPOINTS_MISSING


def test_find_switchpoints_empty_schedule() -> None:
    """Test _find_switchpoints raises InvalidGetScheduleError on empty schedule."""

    with pytest.raises(exc.InvalidGetScheduleError, match="daily schedules are empty"):
        _find_switchpoints([], DayOfWeek.MONDAY, "08:00:00")


@pytest.mark.parametrize(
    ("dtm", "tz_info", "expected_dow", "expected_tod"),
    [
        # Monday morning UTC, stays Monday in UTC
        (
            dt(2026, 2, 23, 8, 30, tzinfo=UTC),  # Monday
            UTC,
            DayOfWeek.MONDAY,
            "08:30:00",
        ),
        # Sunday 23:30 UTC -> Monday 00:30 in UTC+1
        (
            dt(2026, 2, 22, 23, 30, tzinfo=UTC),  # Sunday in UTC
            tz(offset=td(hours=1)),  # UTC+1
            DayOfWeek.MONDAY,
            "00:30:00",
        ),
        # Monday 00:30 UTC -> Sunday 23:30 in UTC-1
        (
            dt(2026, 2, 23, 0, 30, tzinfo=UTC),  # Monday in UTC
            tz(offset=td(hours=-1)),  # UTC-1
            DayOfWeek.SUNDAY,
            "23:30:00",
        ),
        # Friday in a named timezone
        (
            dt(2026, 2, 27, 12, 0, tzinfo=UTC),  # Friday
            ZoneInfo("Europe/London"),  # UTC+0 in February
            DayOfWeek.FRIDAY,
            "12:00:00",
        ),
        # Saturday in Berlin (UTC+1 in winter)
        (
            dt(2026, 2, 28, 23, 45, tzinfo=UTC),  # Saturday 23:45 UTC
            ZoneInfo("Europe/Berlin"),  # UTC+1
            DayOfWeek.SUNDAY,
            "00:45:00",
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
