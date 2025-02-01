"""Tests for evohome-async - validate the schema of HA's debug JSON (older ver)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from evohome.helpers import camel_to_snake, convert_keys_to_snake_case
from evohomeasync2 import Location
from evohomeasync2.schemas.config import factory_tcs, factory_time_zone
from evohomeasync2.schemas.const import (
    S2_GATEWAY_ID,
    S2_GATEWAY_INFO,
    S2_GATEWAYS,
    S2_LOCATION_ID,
    S2_LOCATION_INFO,
    S2_SUPPORTS_DAYLIGHT_SAVING,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    S2_TIME_ZONE,
    S2_USE_DAYLIGHT_SAVE_SWITCHING,
)
from evohomeasync2.schemas.status import factory_loc_status

from .conftest import ClientStub
from .const import TEST_DIR

if TYPE_CHECKING:
    import pytest

WORK_DIR = f"{TEST_DIR}/schemas_0"


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
SCH_LOCN_STATUS: Final = factory_loc_status()


def test_config_refresh(config: dict[str, Any], status: dict[str, Any]) -> None:
    """Test the loading a config, then an update_status() on top of that."""

    # hack because old JSON from HA's evohome integration didn't have location_id, etc.
    if not config[S2_LOCATION_INFO].get(S2_LOCATION_ID):
        config[S2_LOCATION_INFO][S2_LOCATION_ID] = status[S2_LOCATION_ID]

    # hack because old JSON from HA's evohome integration didn't include this data
    if config[S2_LOCATION_INFO].get(S2_USE_DAYLIGHT_SAVE_SWITCHING) is None:
        config[S2_LOCATION_INFO][S2_USE_DAYLIGHT_SAVE_SWITCHING] = config[
            S2_LOCATION_INFO
        ][S2_TIME_ZONE][S2_SUPPORTS_DAYLIGHT_SAVING]

    # hack because the JSON is from HA's evohome integration, not vendor's TCC servers
    if not config[S2_GATEWAYS][0].get(S2_GATEWAY_ID):
        config[S2_GATEWAYS][0][S2_GATEWAY_INFO] = {
            S2_GATEWAY_ID: status[S2_GATEWAYS][0][S2_GATEWAY_ID]
        }

    config = convert_keys_to_snake_case(config)
    status = convert_keys_to_snake_case(status)

    loc = Location(ClientStub(), config)  # type: ignore[arg-type]
    loc._update_status(status)  # type: ignore[arg-type]


def test_config_schemas(config: dict[str, Any]) -> None:
    """Test the config schema for a location."""

    _ = SCH_TIME_ZONE(config[S2_LOCATION_INFO][S2_TIME_ZONE])

    for gwy_config in config[S2_GATEWAYS]:
        for tcs_config in gwy_config[S2_TEMPERATURE_CONTROL_SYSTEMS]:
            _ = SCH_TCS_CONFIG(tcs_config)


def test_status_schemas(status: dict[str, Any]) -> None:
    """Test the status schema for a location."""

    _ = SCH_LOCN_STATUS(status)


# def test_came_to_snake() -> None:
#     """Test the status schema for a location."""

assert camel_to_snake("camel2_camel2_case") == "camel2_camel2_case"
assert camel_to_snake("getHTTPResponseCode") == "get_http_response_code"
assert camel_to_snake("HTTPResponseCodeXYZ") == "http_response_code_xyz"
