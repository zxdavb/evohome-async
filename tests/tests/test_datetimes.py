"""evohome-async - validate the datetime handling helpers."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td, timezone as tz

import probatio as vol
import pytest

from _evohome.helpers import Case, as_aware_dtm, as_timedelta, convert_dtms_to_utc_str
from evohomeasync2 import BadApiRequestError
from evohomeasync2.schemas.helpers import factory_datetime

# a fixed +01:00 offset (e.g. London in summer); avoids a tzdata dependency
PLUS_ONE = tz(td(hours=1))


def test_convert_dtms_to_utc_str_converts_non_utc_to_utc() -> None:
    """A non-UTC aware dt is sent as the correct UTC instant, not relabelled."""

    # 22:10 at +01:00 is 21:10 UTC; the trailing 'Z' must reflect that
    until = dt(2024, 7, 10, 22, 10, tzinfo=PLUS_ONE)

    assert convert_dtms_to_utc_str({"time_until": until}) == {
        "time_until": "2024-07-10T21:10:00Z"
    }


def test_convert_dtms_to_utc_str_leaves_utc_unchanged() -> None:
    """An already-UTC aware dt formats to the same instant (the fix is idempotent)."""

    until = dt(2024, 7, 10, 21, 10, tzinfo=UTC)

    assert convert_dtms_to_utc_str(until) == "2024-07-10T21:10:00Z"


def test_convert_dtms_to_utc_str_rejects_naive() -> None:
    """A naive dt is rejected, as astimezone() would assume the local TZ."""

    naive = dt.fromisoformat("2024-07-10T22:10:00")  # no offset

    with pytest.raises(BadApiRequestError):
        convert_dtms_to_utc_str({"time_until": naive})


def test_convert_dtms_to_utc_str_leaves_plain_strings_alone() -> None:
    """Only datetime instances are converted; plain strings pass through."""

    assert convert_dtms_to_utc_str({"name": "kitchen"}) == {"name": "kitchen"}


# --- setter input: as_aware_dtm() ---------------------------------------------------


def test_as_aware_dtm_passes_through_aware_dt() -> None:
    aware = dt(2024, 7, 10, 21, 10, tzinfo=UTC)

    assert as_aware_dtm(aware) is aware


def test_as_aware_dtm_parses_aware_iso_string() -> None:
    assert as_aware_dtm("2024-07-10T22:10:00+01:00") == dt(
        2024, 7, 10, 22, 10, tzinfo=PLUS_ONE
    )


def test_as_aware_dtm_rejects_naive_dt() -> None:
    naive = dt.fromisoformat("2024-07-10T22:10:00")  # no offset

    with pytest.raises(BadApiRequestError):
        as_aware_dtm(naive)


def test_as_aware_dtm_rejects_naive_string() -> None:
    with pytest.raises(BadApiRequestError):
        as_aware_dtm("2024-07-10T22:10:00")


def test_as_aware_dtm_rejects_unparsable_string() -> None:
    with pytest.raises(BadApiRequestError):
        as_aware_dtm("not-a-datetime")


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


@pytest.mark.parametrize(
    ("timespan", "expected"),
    [
        pytest.param("1.00:00:00", td(days=1), id="day"),
        pytest.param("99.00:00:00", td(days=99), id="days"),
        pytest.param("01:00:00", td(hours=1), id="hour"),
        pytest.param("365.23:45:00", td(days=365, hours=23, minutes=45), id="mixed"),
        pytest.param("", None, id="empty"),
        pytest.param("P1D", None, id="iso_8601"),
        pytest.param("1.00:00", None, id="no_seconds"),
        pytest.param("999999999.00:00:00", td(days=999999999), id="max_days"),
        pytest.param("1000000000.00:00:00", None, id="too_many_days"),
        pytest.param("24:00:00", None, id="hours_out_of_range"),
        pytest.param("00:60:00", None, id="minutes_out_of_range"),
        pytest.param("00:00:60", None, id="seconds_out_of_range"),
        pytest.param("99.99:99:99", None, id="all_out_of_range"),
    ],
)
def test_as_timedelta(timespan: str, expected: td | None) -> None:
    """Test as_timedelta() parses a vendor TimeSpan, and returns None if it can't."""
    assert as_timedelta(timespan) == expected
