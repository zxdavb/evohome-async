"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from datetime import datetime as dt
from enum import StrEnum

import pytest

from _evohome.helpers import camel_to_snake
from evohomeasync2.const import SZ_FAULT_TYPE, SZ_SINCE, FaultType as EvoFaultType
from evohomeasync2.schemas.const import S2_FAULT_TYPE, TccFaultType
from evohomeasync2.schemas.helpers import Case
from evohomeasync2.schemas.status import factory_active_faults

_KNOWN = "BoilerServiceRequired"
_UNKNOWN = "NoSuchFaultType"
_SINCE = "2026-06-28T00:02:25"


@pytest.mark.parametrize(
    ("case", "payload", "expected"),
    [
        (
            Case.VENDOR,
            {"faultType": _KNOWN, "since": _SINCE},
            {S2_FAULT_TYPE: TccFaultType.SYS_B_SR},
        ),
        (
            Case.PYTHONIC,  # after convert_keys_to_snake_case()
            {"fault_type": _KNOWN, "since": _SINCE},
            {SZ_FAULT_TYPE: EvoFaultType.SYS_B_SR},
        ),
        (
            Case.VENDOR,
            {"faultType": _UNKNOWN, "since": _SINCE},
            {S2_FAULT_TYPE: _UNKNOWN},
        ),
        (
            Case.PYTHONIC,  # after convert_keys_to_snake_case()
            {"fault_type": _UNKNOWN, "since": _SINCE},
            {SZ_FAULT_TYPE: camel_to_snake(_UNKNOWN)},
        ),
    ],
    ids=["vendor_known", "pythonic_known", "vendor_unknown", "pythonic_unknown"],
)
def test_factory_active_faults(
    case: Case,
    payload: dict[str, str],
    expected: dict[str, str],
) -> None:
    """Test a faultType is validated/coerced while tolerating unknown values.

    A fault type absent from the vendor's incomplete list must not raise, but be
    passed through as a plain str, in the casing convention of its case.
    """

    result = factory_active_faults(case)(payload)

    since = result.pop(SZ_SINCE)
    if case is Case.VENDOR:
        assert since == _SINCE
    else:
        assert isinstance(since, dt)

    # an equal str is not enough, as StrEnum members compare equal to their values
    ((key, value),) = expected.items()

    if case is Case.VENDOR:  # is validated only: the value is passed through as-is
        assert result[key] is payload[key]

    elif isinstance(value, StrEnum):  # is coerced to the enum member itself
        assert result[key] is value

    else:  # is an unknown value: a plain str, and not an enum member
        assert not isinstance(result[key], StrEnum)
