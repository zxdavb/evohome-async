"""evohome-async - validate the datetime handling helpers."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td, timezone as tz

import pytest
import voluptuous as vol

from _evohome.helpers import convert_datetimes_to_str
from evohomeasync2 import BadApiRequestError
from evohomeasync2.schemas.helpers import Case, factory_datetime

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


# --- inbound: factory_datetime() coercer (schema validator) -------------------------


def test_factory_datetime_coerces_z_to_aware_utc() -> None:
    """A 'Z' (UTC) string coerces to an aware UTC datetime."""

    coerce = factory_datetime(Case.PYTHONIC)

    assert coerce("2023-11-30T22:10:00Z") == dt(2023, 11, 30, 22, 10, tzinfo=UTC)


def test_factory_datetime_coerces_naive_to_naive() -> None:
    """A naive string (e.g. fault 'since') coerces to a naive datetime."""

    coerce = factory_datetime(Case.PYTHONIC)
    since = coerce("2023-10-09T01:45:00")

    assert isinstance(since, dt)
    assert since.tzinfo is None  # the vendor sends 'since' without an offset


def test_factory_datetime_is_idempotent() -> None:
    """A datetime passes through unchanged, so re-validation succeeds."""

    coerce = factory_datetime(Case.PYTHONIC)
    aware = dt(2023, 11, 30, 22, 10, tzinfo=UTC)

    assert coerce(aware) is aware


def test_factory_datetime_vendor_validates_but_keeps_string() -> None:
    """Case.VENDOR validates the format but keeps the original string."""

    validate = factory_datetime(Case.VENDOR)

    assert validate("2023-11-30T22:10:00Z") == "2023-11-30T22:10:00Z"
    with pytest.raises(vol.Invalid):
        validate("not-a-datetime")
