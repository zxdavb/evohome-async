"""Tests for evohome-async - the mapping of Windows TZ ids to IANA TZ ids."""

from __future__ import annotations

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
def test_iana_tz_from_windows_tz(time_zone_id: str, expected: str) -> None:
    """Test Windows TZ ids, in the forms used by the v1 and v2 APIs."""
    assert iana_tz_from_windows_tz(time_zone_id) == expected


def test_iana_tz_from_windows_tz_unknown() -> None:
    """Test an unknown Windows TZ id raises KeyError (the caller falls back)."""
    with pytest.raises(KeyError):
        iana_tz_from_windows_tz("NoSuchStandardTime")
