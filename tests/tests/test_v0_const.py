"""Tests for evohome-async v0 schema - the vendor's enum values."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import evohomeasync as evo0
from _evohome.helpers import convert_str_enums_to_pascal_case
from evohomeasync.schemas import (
    TccDhwMode,
    TccSensorStatus,
    TccSetpointStatus,
    TccSystemMode,
    TccThermostatMode,
    TccThermostatModelType,
)

if TYPE_CHECKING:
    from enum import StrEnum


# the enums with PascalCase values: these may be sent in a request body
PASCAL_CASE_ENUMS = (
    TccDhwMode,
    TccSensorStatus,
    TccSetpointStatus,
    TccSystemMode,
    TccThermostatMode,
)


@pytest.mark.parametrize("member", [m for e in PASCAL_CASE_ENUMS for m in e], ids=str)
def test_v0_enum_survives_put(member: StrEnum) -> None:
    """Check a PascalCase enum value is sent unchanged (see AbstractAuth.request())."""

    assert convert_str_enums_to_pascal_case({"x": member})["x"] == member.value


def test_v0_model_type_mangled_by_put() -> None:
    """Check why a TccThermostatModelType must never be sent in a request body."""

    member = TccThermostatModelType.DOMESTIC_HOT_WATER
    assert convert_str_enums_to_pascal_case({"x": member})["x"] == "DOMESTICHotWater"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SZ_DHW_OFF", "DHWOff"),
        ("SZ_DHW_ON", "DHWOn"),
        ("SZ_DOMESTIC_HOT_WATER", "DOMESTIC_HOT_WATER"),
        ("SZ_EMEA_ZONE", "EMEA_ZONE"),
        ("SZ_HOLD", "Hold"),
        ("SZ_SCHEDULED", "Scheduled"),
        ("SZ_TEMPORARY", "Temporary"),
    ],
)
def test_v0_deprecated_aliases(name: str, value: str) -> None:
    """Check the deprecated SZ_* exports (now enum members) keep their values."""

    assert getattr(evo0, name) == value
