"""Test the v2 schema factories (active faults, config) and the regexes they use."""

from __future__ import annotations

from datetime import datetime as dt
from enum import StrEnum
from typing import Any

import probatio as vol
import pytest

from _evohome.helpers import TCC_TIMESPAN_REGEX, Case, camel_to_snake
from evohomeasync2.const import SZ_FAULT_TYPE, SZ_SINCE, FaultType as EvoFaultType
from evohomeasync2.schemas.config import factory_system_mode, factory_zon_config
from evohomeasync2.schemas.const import (
    REGEX_DHW_ID,
    REGEX_GATEWAY_ID,
    REGEX_LOCATION_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
    S2_FAULT_TYPE,
    TccFaultType,
)
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
def test_regex_entity_ids(
    regex: str,
    value: str,
    *,
    is_valid: bool,
) -> None:
    """Test an entity ID must be wholly numeric (vol.Match anchors only at the start)."""

    schema = vol.Schema(vol.Match(regex))

    if is_valid:
        assert schema(value) == value
    else:
        with pytest.raises(vol.Invalid):
            schema(value)


@pytest.mark.parametrize(
    ("value", "is_valid"),
    [
        ("00:10:00", True),
        ("01:00:00", True),
        ("1.00:00:00", True),
        ("99.00:00:00", True),
        ("365.23:45:00", True),
        ("", False),
        ("1 day", False),
        ("1.00:00", False),
        ("24:00:00", False),
        ("-1.00:00:00", False),  # not expected (nor anything under 5 minutes)
        ("00:10:00.5", False),  # nor fractional seconds
        ("00:10:00\n", False),
    ],
)
def test_regex_tcc_timespan(
    value: str,
    *,
    is_valid: bool,
) -> None:
    """Test a vendor TimeSpan (e.g. a maxDuration) must be [d.]hh:mm:ss, and nothing else."""

    schema = vol.Schema(vol.Match(TCC_TIMESPAN_REGEX))

    if is_valid:
        assert schema(value) == value
    else:
        with pytest.raises(vol.Invalid):
            schema(value)


def _zon_config(
    schedule_capabilities: dict[str, Any] | None = None, **setpoint_capabilities: Any
) -> dict[str, Any]:
    """Return a zone's config (as per the default fixture), with these capabilities."""

    return {
        "zoneId": "3432521",
        "modelType": "HeatingZone",
        "setpointCapabilities": {
            "maxHeatSetpoint": 35.0,
            "minHeatSetpoint": 5.0,
            "valueResolution": 0.5,
            "canControlHeat": True,
            "canControlCool": False,
            "allowedSetpointModes": [
                "PermanentOverride",
                "FollowSchedule",
                "TemporaryOverride",
            ],
            "maxDuration": "1.00:00:00",
            "timingResolution": "00:10:00",
        }
        | setpoint_capabilities,
        "scheduleCapabilities": {
            "maxSwitchpointsPerDay": 6,
            "minSwitchpointsPerDay": 1,
            "timingResolution": "00:10:00",
            "setpointValueResolution": 0.5,
        }
        | (schedule_capabilities or {}),
        "name": "Dead Zone",
        "zoneType": "RadiatorZone",
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.1, 0.1), (0.5, 0.5), (1.0, 1.0), (1, 1.0)],  # JSON may send 1, not 1.0
)
def test_factory_zon_config_value_resolution(
    value: float,
    expected: float,
) -> None:
    """Test a zone's (and its schedule's) value resolution is one of 0.1, 0.5 or 1.0."""

    result = factory_zon_config()(
        _zon_config({"setpointValueResolution": value}, valueResolution=value)
    )

    assert result["setpointCapabilities"]["valueResolution"] == expected
    assert result["scheduleCapabilities"]["setpointValueResolution"] == expected


@pytest.mark.parametrize(
    "capabilities",
    [
        {"valueResolution": 0.25},
        {"maxDuration": "1 day"},
        {
            "vacationHoldCapabilities": {
                "isChangeable": True,
                "isCancelable": True,
                "maxDuration": "1 day",
            }
        },
        {
            "vacationHoldCapabilities": {
                "isChangeable": True,
                "isCancelable": True,
                "minDuration": "1 day",
            }
        },
    ],
    ids=[
        "value_resolution",
        "max_duration",
        "vacation_hold_max_duration",
        "vacation_hold_min_duration",
    ],
)
def test_factory_zon_config_rejects(
    capabilities: dict[str, Any],
) -> None:
    """Test a zone's config is rejected if a setpoint capability is malformed."""

    with pytest.raises(vol.Invalid):
        factory_zon_config()(_zon_config(**capabilities))


def test_factory_zon_config_rejects_setpoint_value_resolution() -> None:
    """Test a zone's config is rejected if its schedule's setpointValueResolution is."""

    with pytest.raises(vol.Invalid):
        factory_zon_config()(_zon_config({"setpointValueResolution": 0.25}))


@pytest.mark.parametrize(
    "timespans",
    [
        {"maxDuration": "1 day", "timingResolution": "01:00:00"},
        {"maxDuration": "1.00:00:00", "timingResolution": "1 hour"},
    ],
    ids=["max_duration", "timing_resolution"],
)
def test_factory_system_mode_rejects(
    timespans: dict[str, str],
) -> None:
    """Test a TCS's allowed system mode is rejected if one of its TimeSpans is malformed."""

    system_mode = {
        "systemMode": "AutoWithEco",
        "canBePermanent": True,
        "canBeTemporary": True,
        "timingMode": "Duration",
    }

    schema = factory_system_mode()
    assert schema(
        system_mode | {"maxDuration": "1.00:00:00", "timingResolution": "01:00:00"}
    )

    with pytest.raises(vol.Invalid):
        schema(system_mode | timespans)
