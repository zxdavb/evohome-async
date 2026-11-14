"""Test the temperature (and its availability) of a v1 zone or DHW.

The vendor gives a thermostat's indoorTemperature, and its indoorTemperatureStatus
(Measured, NotAvailable or SensorFault), where 128 is its value for no temperature. A
temperature is available only if it was measured, and is not 128.

The statuses are given as plain strings, as the vendor's JSON has them (the v1 schemas
do not convert them to enums).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from evohomeasync.const import (
    SZ_INDOOR_TEMPERATURE,
    SZ_INDOOR_TEMPERATURE_STATUS,
    SZ_THERMOSTAT,
)
from evohomeasync.schemas import TccSensorStatus

from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient


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


@pytest.mark.parametrize(
    ("temp", "status", "expected"),
    [
        pytest.param(
            20.5,
            TccSensorStatus.MEASURED.value,
            {"is_available": True, "temperature": 20.5},
            id="measured",
        ),
        pytest.param(
            128,
            TccSensorStatus.MEASURED.value,
            {"is_available": False},  # was: is_available True, with no temperature
            id="measured_but_none",
        ),
        pytest.param(
            128,
            TccSensorStatus.NOT_AVAILABLE.value,
            {"is_available": False},  # as seen
            id="not_available",
        ),
        pytest.param(
            20.5,
            TccSensorStatus.NOT_AVAILABLE.value,
            {"is_available": False},
            id="not_available_with_a_value",
        ),
        pytest.param(
            128,
            TccSensorStatus.SENSOR_FAULT.value,
            {"is_available": False},
            id="sensor_fault",
        ),
    ],
)
async def test_temperature_status(
    ec1: EvohomeClient,
    temp: float,
    status: str,
    expected: dict[str, object],
) -> None:
    """Test a temperature is available only if measured, and not 128 (i.e. none)."""

    tcs = ec1.locations[0].gateways[0].systems[0]
    assert tcs.hotwater is not None  # the default fixture has a DHW

    for entity in (tcs.zones[0], tcs.hotwater):
        thermostat = entity._status[SZ_THERMOSTAT]
        thermostat[SZ_INDOOR_TEMPERATURE] = temp
        thermostat[SZ_INDOOR_TEMPERATURE_STATUS] = status

        assert entity.temperature_status == expected
        assert entity.temperature == expected.get("temperature")  # None if none
