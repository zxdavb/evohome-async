"""Test the temperature (and its availability) of a v1 zone or DHW.

The vendor gives a thermostat's indoorTemperature, and its indoorTemperatureStatus
(Measured, NotAvailable or SensorFault), where 128 is its value for no temperature. A
temperature is available only if it was measured, and is not 128.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from evohomeasync.const import (
    SZ_ALLOWED_MODES,
    SZ_INDOOR_TEMPERATURE,
    SZ_INDOOR_TEMPERATURE_STATUS,
    SZ_MAX_HEAT_SETPOINT,
    SZ_MIN_HEAT_SETPOINT,
    SZ_THERMOSTAT,
)
from evohomeasync.entities import _temperature_status
from evohomeasync.schemas import TccSensorStatus

from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient
    from evohomeasync.typedefs import EvoThermostatInfoDictT


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "fixture_folder" not in metafunc.fixturenames:
        return

    folders = [Path(FIXTURES) / "default"]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


def _thermostat(temp: float, status: str) -> EvoThermostatInfoDictT:
    return {
        SZ_INDOOR_TEMPERATURE: temp,
        SZ_INDOOR_TEMPERATURE_STATUS: status,
        SZ_ALLOWED_MODES: ["Heat", "Off"],
        SZ_MAX_HEAT_SETPOINT: 35.0,
        SZ_MIN_HEAT_SETPOINT: 5.0,
    }


@pytest.mark.parametrize(
    ("temp", "status", "expected"),
    [
        pytest.param(
            20.5,
            TccSensorStatus.MEASURED,
            {"is_available": True, "temperature": 20.5},
            id="measured",
        ),
        pytest.param(
            128,
            TccSensorStatus.MEASURED,
            {"is_available": False},  # was: is_available True, with no temperature
            id="measured_but_none",
        ),
        pytest.param(
            128,
            TccSensorStatus.NOT_AVAILABLE,
            {"is_available": False},  # as seen
            id="not_available",
        ),
        pytest.param(
            20.5,
            TccSensorStatus.NOT_AVAILABLE,
            {"is_available": False},
            id="not_available_with_a_value",
        ),
        pytest.param(
            128,
            TccSensorStatus.SENSOR_FAULT,
            {"is_available": False},
            id="sensor_fault",
        ),
    ],
)
def test_temperature_status(
    temp: float,
    status: str,
    expected: dict[str, object],
) -> None:
    """Test a temperature is available only if measured, and not 128 (i.e. none)."""

    assert _temperature_status(_thermostat(temp, status)) == expected


async def test_temperature_measured_but_none(
    ec1: EvohomeClient,
) -> None:
    """Test a zone/DHW's temperature is None if Measured, but 128 (it was asserted)."""

    tcs = ec1.locations[0].gateways[0].systems[0]
    assert tcs.hotwater is not None  # the default fixture has a DHW

    for entity in (tcs.zones[0], tcs.hotwater):
        assert entity.temperature is not None

        thermostat = entity._status[SZ_THERMOSTAT]
        thermostat[SZ_INDOOR_TEMPERATURE] = 128
        thermostat[SZ_INDOOR_TEMPERATURE_STATUS] = TccSensorStatus.MEASURED

        assert entity.temperature_status == {"is_available": False}
        assert entity.temperature is None
