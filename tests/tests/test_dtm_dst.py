"""Test datetimes across DST transitions."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest

from _evohome.helpers import as_local_time
from _evohome.time_zone import EvoZoneInfo
from evohomeasync2.const import DayOfWeek
from evohomeasync2.zone import _find_switchpoint_dtms, _wall_to_aware

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import Zone
    from evohomeasync2.typedefs import (
        EvoTimeZoneT,
        EvoZonScheduleDayOfWeekT,
        EvoZonScheduleSwitchpointT,
    )

LONDON = ZoneInfo("Europe/London")  # 2026: BST from 01:00Z 29/3, until 01:00Z 25/10

# every day: 15.0C from 01:30 (skipped/repeated in London as DST starts/ends)
SCHEDULE: list[EvoZonScheduleDayOfWeekT] = [
    {
        "day_of_week": d,
        "switchpoints": [
            {"time_of_day": "01:30:00", "heat_setpoint": 15.0},
            {"time_of_day": "06:30:00", "heat_setpoint": 20.0},
            {"time_of_day": "22:00:00", "heat_setpoint": 16.0},
        ],
    }
    for d in DayOfWeek
]


def _utc(day: int, month: int, hour: int, minute: int) -> dt:
    return dt(2026, month, day, hour, minute, tzinfo=UTC)


@pytest.mark.parametrize(
    ("now", "this_start", "this_val", "next_start", "next_val"),
    [
        pytest.param(  # 00:45 GMT: next is 01:30, which is skipped (so from 02:00 BST)
            _utc(29, 3, 0, 45),
            _utc(28, 3, 22, 0),
            16.0,
            _utc(29, 3, 1, 0),
            15.0,
            id="spring-before-gap",
        ),
        pytest.param(  # 02:15 BST: this (01:30) started at 02:00 BST, not in the future
            _utc(29, 3, 1, 15),
            _utc(29, 3, 1, 0),
            15.0,
            _utc(29, 3, 5, 30),
            20.0,
            id="spring-after-gap",
        ),
        pytest.param(  # 01:15 BST (1st pass): next is 01:30 BST
            _utc(25, 10, 0, 15),
            _utc(24, 10, 21, 0),
            16.0,
            _utc(25, 10, 0, 30),
            15.0,
            id="autumn-1st-pass-before",
        ),
        pytest.param(  # 01:45 BST (1st pass): this is 01:30 BST
            _utc(25, 10, 0, 45),
            _utc(25, 10, 0, 30),
            15.0,
            _utc(25, 10, 6, 30),
            20.0,
            id="autumn-1st-pass-after",
        ),
        pytest.param(  # 01:15 GMT (2nd pass): next is 01:30 GMT, not the past 01:30 BST
            _utc(25, 10, 1, 15),
            _utc(24, 10, 21, 0),
            16.0,
            _utc(25, 10, 1, 30),
            15.0,
            id="autumn-2nd-pass-before",
        ),
        pytest.param(  # 01:45 GMT (2nd pass): this is 01:30 GMT, its most recent start
            _utc(25, 10, 1, 45),
            _utc(25, 10, 1, 30),
            15.0,
            _utc(25, 10, 6, 30),
            20.0,
            id="autumn-2nd-pass-after",
        ),
    ],
)
def test_switchpoints_across_dst(
    now: dt,
    this_start: dt,
    this_val: float,
    next_start: dt,
    next_val: float,
) -> None:
    """Test this/next switchpoints when a switchpoint is skipped/repeated by DST."""

    (this_dtm, this_sp), (next_dtm, next_sp) = _find_switchpoint_dtms(
        SCHEDULE, now, LONDON
    )

    # NB: an inter-zone == is always False for a repeated time (PEP 495), so use UTC
    assert (this_dtm.astimezone(UTC), this_sp) == (this_start, this_val)
    assert (next_dtm.astimezone(UTC), next_sp) == (next_start, next_val)

    assert this_dtm <= now < next_dtm  # i.e. this is never future, nor next past
    assert this_dtm.tzinfo is LONDON
    assert next_dtm.tzinfo is LONDON


def test_wall_to_aware() -> None:
    """Test the conversion of a local (naive) time to its first/last instants."""

    # an unambiguous time is a single instant, with fold=0
    first, last = _wall_to_aware(dt.fromisoformat("2026-07-01T12:00"), LONDON)
    assert first is last
    assert (first.fold, first.isoformat()) == (0, "2026-07-01T12:00:00+01:00")

    # a skipped time is the end of the gap, in its canonical form
    first, last = _wall_to_aware(dt.fromisoformat("2026-03-29T01:30"), LONDON)
    assert first is last
    assert first.isoformat() == "2026-03-29T02:00:00+01:00"

    # a repeated time is two instants, an hour apart
    first, last = _wall_to_aware(dt.fromisoformat("2026-10-25T01:30"), LONDON)
    assert first.isoformat() == "2026-10-25T01:30:00+01:00"
    assert last.isoformat() == "2026-10-25T01:30:00+00:00"
    assert last - first == td(0)  # NB: same tzinfo, so compared by wall-clock...
    assert last.astimezone(UTC) - first.astimezone(UTC) == td(hours=1)  # ...not so


def test_wall_to_aware_partial_hour_gap() -> None:
    """Test a skipped time where DST is not a whole hour (Lord Howe Island, +30 min)."""

    first, _ = _wall_to_aware(
        dt.fromisoformat("2026-10-04T02:10"), ZoneInfo("Australia/Lord_Howe")
    )
    assert first.isoformat() == "2026-10-04T02:30:00+11:00"


TZ_INFO_BST: EvoTimeZoneT = {
    "time_zone_id": "UnknownStandardTime",  # i.e. not in the Windows->IANA lookup
    "display_name": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
    "offset_minutes": 0,
    "current_offset_minutes": 60,
    "supports_daylight_saving": True,
}


def test_evo_zone_info_astimezone() -> None:
    """Test the fallback tzinfo (no IANA TZ) can be used to convert datetimes."""

    tzinfo = EvoZoneInfo(time_zone_info=TZ_INFO_BST, use_dst_switching=True)

    dtm = _utc(1, 7, 12, 0).astimezone(tzinfo)  # tzinfo.fromutc() calls tzinfo.dst()

    assert dtm.isoformat() == "2026-07-01T13:00:00+01:00"
    assert dtm.dst() == td(hours=1)
    assert as_local_time("2026-07-01T12:00:00Z", tzinfo) == dtm

    (this_dtm, _), (next_dtm, _) = _find_switchpoint_dtms(SCHEDULE, dtm, tzinfo)
    assert this_dtm.isoformat() == "2026-07-01T06:30:00+01:00"
    assert next_dtm.isoformat() == "2026-07-01T22:00:00+01:00"


def test_switchpoints_coalesced_in_gap() -> None:
    """Test switchpoints skipped by the same gap: only the last ever becomes active."""

    switchpoints: list[EvoZonScheduleSwitchpointT] = [
        {"time_of_day": "01:10:00", "heat_setpoint": 15.0},
        {"time_of_day": "01:40:00", "heat_setpoint": 20.0},
        {"time_of_day": "02:00:00", "heat_setpoint": 21.0},  # i.e. the end of the gap
        {"time_of_day": "22:00:00", "heat_setpoint": 16.0},
    ]
    schedule: list[EvoZonScheduleDayOfWeekT] = [
        {"day_of_week": d, "switchpoints": switchpoints} for d in DayOfWeek
    ]

    # 00:45 GMT: all three start at 02:00 BST, so next is the last of them
    _, (next_dtm, next_val) = _find_switchpoint_dtms(
        schedule, _utc(29, 3, 0, 45), LONDON
    )
    assert (next_dtm.isoformat(), next_val) == ("2026-03-29T02:00:00+01:00", 21.0)

    # 02:15 BST: ...and it is this
    (this_dtm, this_val), _ = _find_switchpoint_dtms(
        schedule, _utc(29, 3, 1, 15), LONDON
    )
    assert (this_dtm.isoformat(), this_val) == ("2026-03-29T02:00:00+01:00", 21.0)


@pytest.mark.parametrize(
    "fixture_folder", [Path(FIXTURES) / "default"], ids=["default"]
)
async def test_switchpoints_across_dst_sequential(
    zone: Zone,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the public properties through both passes of a repeated hour.

    The switchpoints must not be stale after DST ends (e.g. if they were cached).
    """

    assert zone.location.tzinfo == LONDON  # the fixture's location is GMTStandardTime
    zone._schedule = SCHEDULE

    # the same instants (and expected switchpoints) as test_switchpoints_across_dst()
    for now, this_start, this_val, next_start, next_val in [
        (_utc(25, 10, 0, 15), _utc(24, 10, 21, 0), 16.0, _utc(25, 10, 0, 30), 15.0),
        (_utc(25, 10, 0, 45), _utc(25, 10, 0, 30), 15.0, _utc(25, 10, 6, 30), 20.0),
        (_utc(25, 10, 1, 15), _utc(24, 10, 21, 0), 16.0, _utc(25, 10, 1, 30), 15.0),
        (_utc(25, 10, 1, 45), _utc(25, 10, 1, 30), 15.0, _utc(25, 10, 6, 30), 20.0),
    ]:
        freezer.move_to(now)

        assert (this_sp := zone.this_switchpoint) is not None
        assert (next_sp := zone.next_switchpoint) is not None

        assert (this_sp[0].astimezone(UTC), this_sp[1]) == (this_start, this_val)
        assert (next_sp[0].astimezone(UTC), next_sp[1]) == (next_start, next_val)
