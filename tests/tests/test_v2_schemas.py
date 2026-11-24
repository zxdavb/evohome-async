"""Test the v2 schemas against fixtures of the vendor's JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evohomeasync2.schemas.account import TCC_GET_USR_ACCOUNT
from evohomeasync2.schemas.config import TCC_GET_USR_LOCATIONS
from evohomeasync2.schemas.const import (
    S2_ALLOWED_SYSTEM_MODES,
    S2_GATEWAYS,
    S2_SYSTEM_MODE,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    TccSystemMode,
)
from evohomeasync2.schemas.status import factory_loc_status

from .common import assert_schema
from .conftest import FIXTURES_V2 as FIXTURES

# every TCS seen in the wild has one of each (see: TccSystemMode)
_ON_MODES = (TccSystemMode.AUTO, TccSystemMode.HEAT)  # i.e. follow its schedule
_OFF_MODES = (TccSystemMode.HEATING_OFF, TccSystemMode.OFF)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and not p.name.startswith("_")
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


def test_user_account(
    fixture_folder: Path,
) -> None:
    """Test the user account schema against the corresponding JSON."""

    assert_schema(fixture_folder, TCC_GET_USR_ACCOUNT, "user_account.json")


def test_user_locations(
    fixture_folder: Path,
) -> None:
    """Test the user locations (config) schema against the corresponding JSON."""

    assert_schema(fixture_folder, TCC_GET_USR_LOCATIONS, "user_locations.json")


def test_user_locations_system_modes(
    fixture_folder: Path,
) -> None:
    """Test that each TCS offers system modes for both on and off.

    The schema does not check which modes a TCS offers (a TCS lacking an off mode
    would be valid), so this test keeps the fixtures to the systems seen in the wild:
    a synthesised fixture should be plausible, and no TCS lacking either mode has
    been seen.
    """

    path = fixture_folder / "user_locations.json"
    if not path.is_file():
        pytest.skip(f"No {path.name} in: {fixture_folder.name}")

    locations = TCC_GET_USR_LOCATIONS(json.loads(path.read_text()))

    for gwy in (g for loc in locations for g in loc[S2_GATEWAYS]):
        for tcs in gwy[S2_TEMPERATURE_CONTROL_SYSTEMS]:
            modes = {m[S2_SYSTEM_MODE] for m in tcs[S2_ALLOWED_SYSTEM_MODES]}

            assert modes.intersection(_ON_MODES), f"No on mode in: {sorted(modes)}"
            assert modes.intersection(_OFF_MODES), f"No off mode in: {sorted(modes)}"


def test_location_status(
    fixture_folder: Path,
) -> None:
    """Test the location (status) schema against the corresponding JSON."""

    SCH_STATUS = factory_loc_status()

    for p in Path(fixture_folder).glob("status_*.json"):
        assert_schema(fixture_folder, SCH_STATUS, p.name)
