"""Tests for evohome-async - the mapping of Windows TZ ids to IANA TZ ids."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from zoneinfo import ZoneInfo

import pytest

from _evohome.time_zone import iana_tz_from_windows_tz


@pytest.mark.parametrize(
    ("time_zone_id", "expected"),
    [
        pytest.param("GMTStandardTime", "Europe/London", id="v2-gmt"),
        pytest.param("GMT Standard Time", "Europe/London", id="v1-gmt"),
        pytest.param("WAustraliaStandardTime", "Australia/Perth", id="v2-dot"),
        pytest.param("W. Australia Standard Time", "Australia/Perth", id="v1-dot"),
        pytest.param(
            "PacificStandardTimeMexico", "America/Tijuana", id="v2-pacific-mexico"
        ),
        pytest.param(
            "MountainStandardTimeMexico", "America/Mazatlan", id="v2-mountain-mexico"
        ),
        pytest.param(
            "CentralStandardTimeMexico", "America/Mexico_City", id="v2-central-mexico"
        ),
        pytest.param(
            "Central Standard Time (Mexico)",
            "America/Mexico_City",
            id="v1-central-mexico",
        ),
    ],
)
def test_iana_tz_from_windows_tz(
    time_zone_id: str,
    expected: str,
) -> None:
    """Test Windows TZ ids, in the forms used by the v1 and v2 APIs."""
    assert iana_tz_from_windows_tz(time_zone_id) == expected


def test_iana_tz_from_windows_tz_unknown() -> None:
    """Test an unknown Windows TZ id raises KeyError (the caller falls back)."""
    with pytest.raises(KeyError):
        iana_tz_from_windows_tz("NoSuchStandardTime")


# as offered by the vendor (with its OffsetMinutes), so without the sign of the offset
@pytest.mark.parametrize(
    ("time_zone_id", "offset_minutes"),
    [
        pytest.param("DatelineStandardTime", -720, id="dateline"),
        pytest.param("UTC11", -660, id="utc-11"),
        pytest.param("UTC02", -120, id="utc-02"),
        pytest.param("UTC", 0, id="utc"),
        pytest.param("UTC12", 720, id="utc+12"),
    ],
)
def test_iana_tz_from_windows_tz_fixed_offset(
    time_zone_id: str,
    offset_minutes: int,
) -> None:
    """Test the vendor's fixed-offset TZ ids map to an IANA TZ with that offset."""

    tzinfo = ZoneInfo(iana_tz_from_windows_tz(time_zone_id))

    for month in (1, 7):  # i.e. no DST
        assert dt(2026, month, 1, tzinfo=UTC).astimezone(tzinfo).utcoffset() == td(
            minutes=offset_minutes
        )
