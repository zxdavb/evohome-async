"""evohome-async - validate the datetime handling helpers."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td, timezone as tz

import pytest

from _evohome.helpers import convert_datetimes_to_str
from evohomeasync2 import BadApiRequestError

# a fixed +01:00 offset (e.g. London in summer); avoids a tzdata dependency
PLUS_ONE = tz(td(hours=1))


def test_convert_datetimes_to_str_converts_non_utc_to_utc() -> None:
    """A non-UTC aware dt is sent as the correct UTC instant, not relabelled."""

    # 22:10 at +01:00 is 21:10 UTC; the trailing 'Z' must reflect that
    until = dt(2024, 7, 10, 22, 10, tzinfo=PLUS_ONE)

    assert convert_datetimes_to_str({"time_until": until}) == {
        "time_until": "2024-07-10T21:10:00Z"
    }


def test_convert_datetimes_to_str_leaves_utc_unchanged() -> None:
    """An already-UTC aware dt formats to the same instant (the fix is idempotent)."""

    until = dt(2024, 7, 10, 21, 10, tzinfo=UTC)

    assert convert_datetimes_to_str(until) == "2024-07-10T21:10:00Z"


def test_convert_datetimes_to_str_rejects_naive() -> None:
    """A naive dt is rejected, as astimezone() would assume the local TZ."""

    naive = dt.fromisoformat("2024-07-10T22:10:00")  # no offset

    with pytest.raises(BadApiRequestError):
        convert_datetimes_to_str({"time_until": naive})


def test_convert_datetimes_to_str_leaves_plain_strings_alone() -> None:
    """Only datetime instances are converted; plain strings pass through."""

    assert convert_datetimes_to_str({"name": "kitchen"}) == {"name": "kitchen"}
