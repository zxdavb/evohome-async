#!/usr/bin/env python3
"""Tests for evohome-async - validate the schema of HA's debug JSON (newer ver)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from evohome.helpers import convert_keys_to_snake_case
from evohomeasync2 import Location
from evohomeasync2.schemas import TCC_GET_LOC_STATUS
from evohomeasync2.schemas.config import factory_tcs, factory_time_zone
from evohomeasync2.schemas.const import (
    S2_GATEWAYS,
    S2_LOCATION_INFO,
    S2_SUPPORTS_DAYLIGHT_SAVING,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    S2_TIME_ZONE,
    S2_USE_DAYLIGHT_SAVE_SWITCHING,
)

from .common import TEST_DIR
from .conftest import ClientStub

if TYPE_CHECKING:
    import pytest

WORK_DIR = f"{TEST_DIR}/schemas_1"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    def id_fnc(folder_path: Path) -> str:
        return folder_path.name

    folders = [
        p for p in Path(WORK_DIR).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]
    metafunc.parametrize("folder", sorted(folders), ids=id_fnc)


# These schemas have camelCase keys, as per the vendor's schema
SCH_TCS_CONFIG: Final = factory_tcs()
SCH_TIME_ZONE: Final = factory_time_zone()


def test_config_refresh(config: dict[str, Any], status: dict[str, Any]) -> None:
    """Test the loading a config, then an update_status() on top of that."""

    # hack because old JSON from HA's evohome integration didn't include this data
    if config[S2_LOCATION_INFO].get(S2_USE_DAYLIGHT_SAVE_SWITCHING) is None:
        config[S2_LOCATION_INFO][S2_USE_DAYLIGHT_SAVE_SWITCHING] = config[
            S2_LOCATION_INFO
        ][S2_TIME_ZONE][S2_SUPPORTS_DAYLIGHT_SAVING]

    config = convert_keys_to_snake_case(config)
    status = convert_keys_to_snake_case(status)

    # for this, we need snake_case keys
    loc = Location(ClientStub(), config)  # type: ignore[arg-type]
    loc._update_status(status)


def test_config_schemas(config: dict[str, Any]) -> None:
    """Test the config schema for a location."""

    _ = SCH_TIME_ZONE(config[S2_LOCATION_INFO][S2_TIME_ZONE])

    for gwy_config in config[S2_GATEWAYS]:
        for tcs_config in gwy_config[S2_TEMPERATURE_CONTROL_SYSTEMS]:
            _ = SCH_TCS_CONFIG(tcs_config)


def test_status_schemas(status: dict[str, Any]) -> None:
    """Test the status schema for a location."""

    _ = TCC_GET_LOC_STATUS(status)
