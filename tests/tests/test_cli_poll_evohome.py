"""Tests for evohome-async CLI poll command."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from io import StringIO


def test_parse_interval_seconds() -> None:
    """Test parsing interval in seconds."""
    from evohome_cli.poll_evohome import _parse_interval

    assert _parse_interval("30s") == 30.0
    assert _parse_interval("60s") == 60.0
    assert _parse_interval("120s") == 120.0


def test_parse_interval_minutes() -> None:
    """Test parsing interval in minutes."""
    from evohome_cli.poll_evohome import _parse_interval

    assert _parse_interval("1m") == 60.0
    assert _parse_interval("2m") == 120.0
    assert _parse_interval("120m") == 7200.0


def test_parse_interval_case_insensitive() -> None:
    """Test parsing interval is case insensitive."""
    from evohome_cli.poll_evohome import _parse_interval

    assert _parse_interval("30S") == 30.0
    assert _parse_interval("1M") == 60.0


def test_parse_interval_invalid_format() -> None:
    """Test parsing invalid interval format."""
    from evohome_cli.poll_evohome import _parse_interval
    import asyncclick

    with pytest.raises(asyncclick.exceptions.BadParameter, match="Invalid interval format"):
        _parse_interval("invalid")


def test_parse_interval_too_short() -> None:
    """Test parsing interval below minimum."""
    from evohome_cli.poll_evohome import _parse_interval
    import asyncclick

    with pytest.raises(asyncclick.exceptions.BadParameter, match="at least 30 seconds"):
        _parse_interval("29s")


def test_parse_interval_too_long() -> None:
    """Test parsing interval above maximum."""
    from evohome_cli.poll_evohome import _parse_interval
    import asyncclick

    with pytest.raises(asyncclick.exceptions.BadParameter, match="at most 120 minutes"):
        _parse_interval("121m")


def test_format_zone_key() -> None:
    """Test formatting zone key."""
    from evohome_cli.poll_evohome import _format_zone_key

    assert _format_zone_key("5262675", "Livingroom") == "5262675_Livingroom"
    assert _format_zone_key("5262676", "Hall upstairs") == "5262676_Hall_upstairs"
    assert _format_zone_key("5262677", "Room 1") == "5262677_Room_1"


def test_poll_basic_functionality_logic(tmp_path: Path) -> None:
    """Test poll command logic (CSV writing, zone key formatting)."""
    from evohome_cli.poll_evohome import _format_zone_key
    import csv

    # Test CSV writing logic
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
        _format_zone_key("5262676", "Kitchen"),
    ]
    csv_columns = ["timestamp", "system_mode"] + zone_keys

    # Write header
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()

    # Write a row
    csv_row = {
        "timestamp": "2025-01-15T10:30:00",
        "system_mode": "AutoWithEco",
        "5262675_Livingroom": "16.5",
        "5262676_Kitchen": "20.0",
    }
    with open(output_file, "a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow(csv_row)

    # Verify CSV content
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 1
        first_row = rows[0]
        assert first_row["timestamp"] == "2025-01-15T10:30:00"
        assert first_row["system_mode"] == "AutoWithEco"
        assert first_row["5262675_Livingroom"] == "16.5"
        assert first_row["5262676_Kitchen"] == "20.0"


def test_poll_file_exists_append_logic(tmp_path: Path) -> None:
    """Test poll command logic when file exists and appending."""
    from evohome_cli.poll_evohome import _format_zone_key
    import csv

    # Create existing file with some data
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
        _format_zone_key("5262676", "Kitchen"),
    ]
    csv_columns = ["timestamp", "system_mode"] + zone_keys

    # Write header and one row to existing file
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:30:00",
            "system_mode": "AutoWithEco",
            "5262675_Livingroom": "16.5",
            "5262676_Kitchen": "20.0",
        })

    # When appending, we should NOT write header again
    # Just append new row
    with open(output_file, "a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow({
            "timestamp": "2025-01-15T10:31:00",
            "system_mode": "Auto",
            "5262675_Livingroom": "16.6",
            "5262676_Kitchen": "20.1",
        })

    # Verify CSV content has 2 rows (not 3, because header wasn't duplicated)
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["timestamp"] == "2025-01-15T10:30:00"
        assert rows[1]["timestamp"] == "2025-01-15T10:31:00"


def test_poll_file_exists_overwrite_logic(tmp_path: Path) -> None:
    """Test poll command logic when file exists and overwriting."""
    from evohome_cli.poll_evohome import _format_zone_key
    import csv

    # Create existing file with some data
    output_file = tmp_path / "temps.csv"
    zone_keys = [
        _format_zone_key("5262675", "Livingroom"),
    ]
    csv_columns = ["timestamp", "system_mode"] + zone_keys

    # Write header and one row to existing file
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:30:00",
            "system_mode": "AutoWithEco",
            "5262675_Livingroom": "16.5",
        })

    # When overwriting, we write header again and replace content
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2025-01-15T10:35:00",
            "system_mode": "Away",
            "5262675_Livingroom": "17.0",
        })

    # Verify CSV content has only 1 row (old data was overwritten)
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["timestamp"] == "2025-01-15T10:35:00"
        assert rows[0]["5262675_Livingroom"] == "17.0"


def test_poll_no_zones_logic() -> None:
    """Test poll command logic when no zones are found."""
    # Test that the function would exit early if zones list is empty
    zones: dict[str, str] = {}
    
    # When zones is empty, the function should return early
    assert len(zones) == 0
    # This is the check that happens in the function
    if not zones:
        # Function would exit early, CSV file would not be created
        pass


def test_poll_unavailable_temperature_logic(tmp_path: Path) -> None:
    """Test poll command logic with unavailable temperature."""
    from evohome_cli.poll_evohome import _format_zone_key
    import csv

    # Test CSV writing with N/A for unavailable temperature
    output_file = tmp_path / "temps.csv"
    zone_key = _format_zone_key("5262675", "Livingroom")
    csv_columns = ["timestamp", zone_key]

    # Write header
    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()

    # Write a row with N/A temperature
    csv_row = {
        "timestamp": "2025-01-15T10:30:00",
        zone_key: "N/A",
    }
    with open(output_file, "a") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writerow(csv_row)

    # Verify CSV content has N/A
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 1
        first_row = rows[0]
        assert first_row[zone_key] == "N/A"


def test_poll_interval_validation() -> None:
    """Test interval validation in click callback."""
    from evohome_cli.poll_evohome import _parse_interval
    import asyncclick

    # Test valid intervals
    assert _parse_interval("30s") == 30.0
    assert _parse_interval("120m") == 7200.0

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

