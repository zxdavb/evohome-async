"""Tests for evohome-async - validate the schemas of vendor's RESTful JSON."""

from __future__ import annotations

from datetime import datetime as dt
from enum import StrEnum

import probatio as vol
import pytest

from _evohome.helpers import camel_to_snake, convert_keys_to_snake_case
from evohomeasync2.const import (
    SZ_FAULT_TYPE,
    SZ_MODEL_TYPE,
    SZ_SINCE,
    FaultType as EvoFaultType,
    TcsModelType as EvoTcsModelType,
)
from evohomeasync2.schemas.config import factory_tcs
from evohomeasync2.schemas.const import (
    REGEX_DHW_ID,
    REGEX_GATEWAY_ID,
    REGEX_LOCATION_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
    S2_FAULT_TYPE,
    S2_MODEL_TYPE,
    TccFaultType,
    TccTcsModelType,
)
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


@pytest.mark.parametrize(
    ("case", "key", "expected"),
    [
        (Case.VENDOR, S2_MODEL_TYPE, TccTcsModelType.SARATOGA),
        (Case.PYTHONIC, SZ_MODEL_TYPE, EvoTcsModelType.SARATOGA),
    ],
    ids=["vendor", "pythonic"],
)
def test_factory_tcs_saratoga(case: Case, key: str, expected: StrEnum) -> None:
    """Test a TCS modelType of 'Saratoga' is a known member (see: #145)."""

    payload = {
        "systemId": "1234567",
        "modelType": "Saratoga",
        "allowedSystemModes": [
            {"systemMode": "Auto", "canBePermanent": True, "canBeTemporary": False}
        ],
        "zones": [
            {
                "zoneId": "2345678",
                "modelType": "HeatingZone",
                "name": "Lounge",
                "setpointCapabilities": {
                    "maxHeatSetpoint": 35.0,
                    "minHeatSetpoint": 5.0,
                    "valueResolution": 0.5,
                    "canControlHeat": True,
                    "canControlCool": False,
                    "allowedSetpointModes": ["FollowSchedule"],
                    "maxDuration": "1.00:00:00",
                    "timingResolution": "00:10:00",
                },
                "zoneType": "RadiatorZone",
            }
        ],
    }

    result = factory_tcs(case)(
        payload if case is Case.VENDOR else convert_keys_to_snake_case(payload)
    )

    if case is Case.VENDOR:
        assert result[key] == expected
    else:
        assert result[key] is expected


@pytest.mark.parametrize(
    "regex",
    [REGEX_DHW_ID, REGEX_GATEWAY_ID, REGEX_LOCATION_ID, REGEX_SYSTEM_ID, REGEX_ZONE_ID],
    ids=["dhw", "gateway", "location", "system", "zone"],
)
@pytest.mark.parametrize(
    ("value", "is_valid"),
    [
        ("1234567", True),
        ("", False),
        ("not-an-id", False),
        ("123abc", False),
        ("abc123", False),
        ("1234567\n", False),
    ],
)
def test_regex_entity_ids(regex: str, value: str, *, is_valid: bool) -> None:
    """Test an entity ID must be wholly numeric (vol.Match anchors only at the start)."""

    schema = vol.Schema(vol.Match(regex))

    if is_valid:
        assert schema(value) == value
    else:
        with pytest.raises(vol.Invalid):
            schema(value)
