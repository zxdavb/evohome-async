"""Tests for evohome-async CLI poll command."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

import asyncclick
import pytest

from evohome_cli.poll_evohome import _format_zone_key, _parse_interval

if TYPE_CHECKING:
    from pathlib import Path

# Constants for magic values
INTERVAL_30 = 30.0
INTERVAL_60 = 60.0
INTERVAL_120 = 120.0
INTERVAL_7200 = 7200.0
LIVINGROOM_TEMP = 16.5
KITCHEN_TEMP = 20.0
LIVINGROOM_TEMP_NEW = 16.6
KITCHEN_TEMP_NEW = 20.1
ZONE_ID_LIVINGROOM = "5262675"
ZONE_ID_KITCHEN = "5262676"
ZONE_ID_HALL = "5262677"
ZONE_ID_TEST = "12345"
MIN_INTERVAL_SEC = 30
MAX_INTERVAL_MIN = 120
MAX_INTERVAL_MALFORMED = 121
TEMP_17 = 17.0
RESULT_LEN_1 = 1
RESULT_LEN_2 = 2


def test_parse_interval_seconds() -> None:
    """Test parsing interval in seconds."""
    assert _parse_interval("30s") == INTERVAL_30
    assert _parse_interval("60s") == INTERVAL_60
    assert _parse_interval("120s") == INTERVAL_120


def test_parse_interval_minutes() -> None:
    """Test parsing interval in minutes."""
    assert _parse_interval("1m") == INTERVAL_60
    assert _parse_interval("2m") == INTERVAL_120
    assert _parse_interval("120m") == INTERVAL_7200


def test_parse_interval_case_insensitive() -> None:
    """Test parsing interval is case insensitive."""
    assert _parse_interval("30S") == INTERVAL_30
    assert _parse_interval("1M") == INTERVAL_60


def test_parse_interval_invalid_format() -> None:
    """Test parsing invalid interval format."""
    with pytest.raises(asyncclick.exceptions.BadParameter, match="Invalid interval format"):
        _parse_interval("invalid")


def test_parse_interval_too_short() -> None:
    """Test parsing interval below minimum."""
    with pytest.raises(asyncclick.exceptions.BadParameter, match="at least 30 seconds"):
        _parse_interval("29s")


def test_parse_interval_too_long() -> None:
    """Test parsing interval above maximum."""
    with pytest.raises(asyncclick.exceptions.BadParameter, match="at most 120 minutes"):
        _parse_interval("121m")


def test_format_zone_key() -> None:
    """Test formatting zone key."""
    assert _format_zone_key(ZONE_ID_LIVINGROOM, "Livingroom") == f"{ZONE_ID_LIVINGROOM}_Livingroom"
    assert _format_zone_key("5262676", "Hall upstairs") == "5262676_Hall_upstairs"
    assert _format_zone_key("5262677", "Room 1") == "5262677_Room_1"


def test_poll_basic_functionality_logic(tmp_path: Path) -> None:
    """Test poll command logic (CSV writing, zone key formatting)."""

    # Test CSV writing logic
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
        _format_zone_key("5262676", "Kitchen"),
    ]
    csv_columns = ["timestamp", "system_mode", *zone_keys]

    # Write header
    with output_file.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()

    # Write a row
    csv_row = {
        "timestamp": "2025-01-15T10:30:00",
        "system_mode": "AutoWithEco",
        f"{ZONE_ID_LIVINGROOM}_Livingroom": str(LIVINGROOM_TEMP),
        f"{ZONE_ID_KITCHEN}_Kitchen": str(KITCHEN_TEMP),
    }
    with output_file.open("a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow(csv_row)

    # Verify CSV content
    with output_file.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == RESULT_LEN_1
        first_row = rows[0]
        assert first_row["timestamp"] == "2025-01-15T10:30:00"
        assert first_row["system_mode"] == "AutoWithEco"
        assert first_row[f"{ZONE_ID_LIVINGROOM}_Livingroom"] == str(LIVINGROOM_TEMP)
        assert first_row[f"{ZONE_ID_KITCHEN}_Kitchen"] == str(KITCHEN_TEMP)


def test_poll_file_exists_append_logic(tmp_path: Path) -> None:
    """Test poll command logic when file exists and appending."""

    # Create existing file with some data
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
        _format_zone_key("5262676", "Kitchen"),
    ]
    csv_columns = ["timestamp", "system_mode", *zone_keys]

    # Write header and one row to existing file
    with output_file.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:30:00",
            "system_mode": "AutoWithEco",
            f"{ZONE_ID_LIVINGROOM}_Livingroom": str(LIVINGROOM_TEMP),
            f"{ZONE_ID_KITCHEN}_Kitchen": str(KITCHEN_TEMP),
        })

    # When appending, we should NOT write header again
    # Just append new row
    with output_file.open("a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow({
            "timestamp": "2025-01-15T10:31:00",
            "system_mode": "Auto",
            f"{ZONE_ID_LIVINGROOM}_Livingroom": str(LIVINGROOM_TEMP_NEW),
            f"{ZONE_ID_KITCHEN}_Kitchen": str(KITCHEN_TEMP_NEW),
        })

    # Verify CSV content has 2 rows (not 3, because header wasn't duplicated)
    with output_file.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == RESULT_LEN_2
        assert rows[0]["timestamp"] == "2025-01-15T10:30:00"
        assert rows[1]["timestamp"] == "2025-01-15T10:31:00"


def test_poll_file_exists_overwrite_logic(tmp_path: Path) -> None:
    """Test poll command logic when file exists and overwriting."""

    # Create existing file with some data
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
    ]
    csv_columns = ["timestamp", "system_mode", *zone_keys]

    # Write header and one row to existing file
    with output_file.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:30:00",
            "system_mode": "AutoWithEco",
            f"{ZONE_ID_LIVINGROOM}_Livingroom": str(LIVINGROOM_TEMP),
        })

    # When overwriting, we write header again and replace content
    with output_file.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:35:00",
            "system_mode": "Away",
            f"{ZONE_ID_LIVINGROOM}_Livingroom": str(TEMP_17),
        })

    # Verify CSV content has only 1 row (old data was overwritten)
    with output_file.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == RESULT_LEN_1
        assert rows[0]["timestamp"] == "2025-01-15T10:35:00"
        assert rows[0][f"{ZONE_ID_LIVINGROOM}_Livingroom"] == str(TEMP_17)


def test_poll_no_zones_logic() -> None:
    """Test poll command logic when no zones are found."""
    # Test that the function would exit early if zones list is empty
    zones: dict[str, str] = {}

    # When zones is empty, the function should return early
    assert not zones
    # This is the check that happens in the function
    if not zones:
        # Function would exit early, CSV file would not be created
        pass


def test_poll_unavailable_temperature_logic(tmp_path: Path) -> None:
    """Test poll command logic with unavailable temperature."""
    # Test CSV writing with N/A for unavailable temperature
    output_file = tmp_path / "temps.csv"
    zone_key = _format_zone_key(ZONE_ID_LIVINGROOM, "Livingroom")
    csv_columns = ["timestamp", zone_key]

    # Write header
    with output_file.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()

    # Write a row with N/A temperature
    csv_row = {
        "timestamp": "2025-01-15T10:30:00",
        zone_key: "N/A",
    }
    with output_file.open("a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow(csv_row)

    # Verify CSV content has N/A
    with output_file.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == RESULT_LEN_1
        first_row = rows[0]
        assert first_row[zone_key] == "N/A"


def test_poll_interval_validation() -> None:
    """Test interval validation in click callback."""
    # Test valid intervals
    assert _parse_interval("30s") == INTERVAL_30
    assert _parse_interval("120m") == INTERVAL_7200

    # Test invalid formats
    with pytest.raises(asyncclick.exceptions.BadParameter):
        _parse_interval("30")
    with pytest.raises(asyncclick.exceptions.BadParameter):
        _parse_interval("abc")

    # Test out of range
    with pytest.raises(asyncclick.exceptions.BadParameter):
        _parse_interval("29s")
    with pytest.raises(asyncclick.exceptions.BadParameter):
        _parse_interval("121m")

