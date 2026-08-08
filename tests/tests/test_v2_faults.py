"""Tests for evohome-async - handling of active faults, incl. unknown fault types."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt

import pytest

from evohomeasync2.const import FaultType
from evohomeasync2.schemas.helpers import Case
from evohomeasync2.schemas.status import factory_active_faults
from evohomeasync2.zone import ActiveFaultsBase

_SINCE = dt(2026, 6, 28, 0, 2, 25, tzinfo=UTC)


def test_active_faults_known_type() -> None:
    """Test a known faultType is coerced to the user-facing enum."""

    fault = factory_active_faults(Case.PYTHONIC)(
        {"fault_type": "BoilerServiceRequired", "since": "2026-06-28T00:02:25"}
    )

    assert fault["fault_type"] is FaultType.SYS_B_SR


def test_active_faults_unknown_type() -> None:
    """Test an unknown faultType is passed thru as a str, rather than raising.

    The vendor's list of fault types is incomplete, and an unknown value must not
    invalidate the entire location status (see: home-assistant/core#178493).
    """

    # the vendor case: validate only
    fault = factory_active_faults(Case.VENDOR)(
        {"faultType": "NoSuchFaultType", "since": "2026-06-28T00:02:25"}
    )

    assert fault["faultType"] == "NoSuchFaultType"

    # the pythonic case: coerce, or pass thru
    fault = factory_active_faults(Case.PYTHONIC)(
        {"fault_type": "NoSuchFaultType", "since": "2026-06-28T00:02:25"}
    )

    assert fault["fault_type"] == "no_such_fault_type"
    assert not isinstance(fault["fault_type"], FaultType)


class _FaultyEntity(ActiveFaultsBase[None]):
    """A minimal entity, to exercise the active faults logging."""

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger("evohomeasync2")


@pytest.mark.parametrize(
    ("fault_type", "expected"),
    [
        (FaultType.SYS_B_SR, str(FaultType.SYS_B_SR)),
        # the schema passes through unknown values as snake_case strs, not FaultTypes
        ("no_such_fault_type", "no_such_fault_type (unknown)"),
    ],
)
def test_active_fault_warning(
    caplog: pytest.LogCaptureFixture,
    fault_type: FaultType | str,
    expected: str,
) -> None:
    """Test a fault type absent from FaultType is flagged as unknown when logged."""

    entity = _FaultyEntity("8419116")

    with caplog.at_level(logging.WARNING):
        entity._update_faults([{"fault_type": fault_type, "since": _SINCE}])

    assert caplog.record_tuples == [
        (
            "evohomeasync2",
            logging.WARNING,
            f"_FaultyEntity(id='8419116'): Active fault: {_SINCE.isoformat()} {expected}",
        )
    ]
