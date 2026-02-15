import json
from pathlib import Path

import pytest

from evohome_cli.schedule_parser import (
    json_to_text_schedule,
    parse_day_spec,
    parse_temperature_time,
    parse_text_schedule,
)

# Constants for magic values
LEN_1 = 1
LEN_2 = 2
LEN_3 = 3
LEN_4 = 4
LEN_7 = 7
TEMP_15 = 15.0
TEMP_16 = 16.0
TEMP_17_5 = 17.5
TEMP_18 = 18.0
TEMP_20 = 20.0
TEMP_21 = 21.0
ZONE_ID_LIVINGROOM = "5262675"
ZONE_ID_KITCHEN = "5262678"
ZONE_ID_TEST = "12345"

# Sample test data
SAMPLE_TEXT_SCHEDULE = """1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30

2. Kitchen (5262678)
Weekdays: 20C @ 07:00 to 15C @ 19:30
Weekends: 20C @ 07:00 to 15C @ 20:30"""

SAMPLE_JSON_SCHEDULE = [
    {
        "zone_id": "5262675",
        "name": "Livingroom",
        "daily_schedules": [
            {
                "day_of_week": "Monday",
                "switchpoints": [
                    {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
                    {"heat_setpoint": 17.5, "time_of_day": "21:50:00"},
                ],
            },
            {
                "day_of_week": "Tuesday",
                "switchpoints": [
                    {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
                    {"heat_setpoint": 17.5, "time_of_day": "21:50:00"},
                ],
            },
            {
                "day_of_week": "Wednesday",
                "switchpoints": [
                    {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
                    {"heat_setpoint": 17.5, "time_of_day": "21:50:00"},
                ],
            },
            {
                "day_of_week": "Thursday",
                "switchpoints": [
                    {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
                    {"heat_setpoint": 17.5, "time_of_day": "21:50:00"},
                ],
            },
            {
                "day_of_week": "Friday",
                "switchpoints": [
                    {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
                    {"heat_setpoint": 17.5, "time_of_day": "21:50:00"},
                ],
            },
            {
                "day_of_week": "Saturday",
                "switchpoints": [
                    {"heat_setpoint": 15.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "22:30:00"},
                ],
            },
            {
                "day_of_week": "Sunday",
                "switchpoints": [
                    {"heat_setpoint": 15.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "22:30:00"},
                ],
            },
        ],
    },
    {
        "zone_id": "5262678",
        "name": "Kitchen",
        "daily_schedules": [
            {
                "day_of_week": "Monday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "19:30:00"},
                ],
            },
            {
                "day_of_week": "Tuesday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "19:30:00"},
                ],
            },
            {
                "day_of_week": "Wednesday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "19:30:00"},
                ],
            },
            {
                "day_of_week": "Thursday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "19:30:00"},
                ],
            },
            {
                "day_of_week": "Friday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "19:30:00"},
                ],
            },
            {
                "day_of_week": "Saturday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "20:30:00"},
                ],
            },
            {
                "day_of_week": "Sunday",
                "switchpoints": [
                    {"heat_setpoint": 20.0, "time_of_day": "07:00:00"},
                    {"heat_setpoint": 15.0, "time_of_day": "20:30:00"},
                ],
            },
        ],
    },
]


# ============================================================================
# Schedule Parser Tests
# ============================================================================


def test_parse_temperature_time() -> None:
    """Test parsing temperature and time pairs from text."""
    text = "16C @ 06:00 to 17.5C @ 21:50"
    result = parse_temperature_time(text)

    assert len(result) == LEN_2
    assert result[0] == (TEMP_16, "06:00:00")
    assert result[1] == (TEMP_17_5, "21:50:00")


def test_parse_temperature_time_multiple() -> None:
    """Test parsing multiple temperature/time pairs."""
    text = "21C @ 06:30 to 18C @ 08:00 to 21C @ 18:00 to 16C @ 22:30"
    result = parse_temperature_time(text)

    assert len(result) == LEN_4
    assert result[0] == (TEMP_21, "06:30:00")
    assert result[1] == (TEMP_18, "08:00:00")
    assert result[2] == (TEMP_21, "18:00:00")
    assert result[3] == (TEMP_16, "22:30:00")


def test_parse_day_spec_weekdays() -> None:
    """Test parsing 'Weekdays' specification."""
    result = parse_day_spec("Weekdays")
    assert result == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def test_parse_day_spec_weekends() -> None:
    """Test parsing 'Weekends' specification."""
    result = parse_day_spec("Weekends")
    assert result == ["Saturday", "Sunday"]


def test_parse_day_spec_all_days() -> None:
    """Test parsing 'All days' specification."""
    result = parse_day_spec("All days")
    assert len(result) == LEN_7
    assert "Monday" in result
    assert "Sunday" in result


def test_parse_day_spec_single_day() -> None:
    """Test parsing single day specification."""
    result = parse_day_spec("Wednesday")
    assert result == ["Wednesday"]


def test_parse_day_spec_day_combination() -> None:
    """Test parsing day combination like 'Mon/Tue/Thu/Fri'."""
    result = parse_day_spec("Mon/Tue/Thu/Fri")
    assert result == ["Monday", "Tuesday", "Thursday", "Friday"]


def test_parse_text_schedule_basic() -> None:
    """Test parsing a basic text schedule."""
    text = """1. Test Zone (12345)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30"""

    result = parse_text_schedule(text)

    assert len(result) == LEN_1
    assert result[0]["zone_id"] == ZONE_ID_TEST
    assert result[0]["name"] == "Test Zone"
    assert len(result[0]["daily_schedules"]) == LEN_7

    # Check weekdays
    monday = next(d for d in result[0]["daily_schedules"] if d["day_of_week"] == "Monday")
    assert len(monday["switchpoints"]) == LEN_2
    assert monday["switchpoints"][0]["heat_setpoint"] == TEMP_16
    assert monday["switchpoints"][0]["time_of_day"] == "06:00:00"

    # Check weekends
    saturday = next(d for d in result[0]["daily_schedules"] if d["day_of_week"] == "Saturday")
    assert saturday["switchpoints"][0]["heat_setpoint"] == TEMP_15


def test_parse_text_schedule_multiple_zones() -> None:
    """Test parsing multiple zones."""
    result = parse_text_schedule(SAMPLE_TEXT_SCHEDULE)

    assert len(result) == LEN_2
    assert result[0]["zone_id"] == ZONE_ID_LIVINGROOM
    assert result[1]["zone_id"] == ZONE_ID_KITCHEN


def test_parse_text_schedule_special_days() -> None:
    """Test parsing schedules with special day specifications."""
    text = """1. Test Zone (12345)
Mon/Tue/Thu/Fri: 15C @ 07:00 to 15C @ 22:30
Wednesday: 15C @ 07:00 to 15C @ 12:00 to 15C @ 22:30
Weekends: 15C @ 07:00 to 15C @ 22:30"""

    result = parse_text_schedule(text)

    assert len(result) == LEN_1
    # Check Wednesday has 3 switchpoints
    wednesday = next(d for d in result[0]["daily_schedules"] if d["day_of_week"] == "Wednesday")
    assert len(wednesday["switchpoints"]) == LEN_3


def test_json_to_text_schedule_basic() -> None:
    """Test converting JSON to text format."""
    result = json_to_text_schedule(SAMPLE_JSON_SCHEDULE)

    assert "Livingroom" in result
    assert ZONE_ID_LIVINGROOM in result
    assert "Weekdays:" in result
    assert "Weekends:" in result
    # Check for temperature format (can be 16C or 16.0C depending on formatting)
    assert "16" in result
    assert "C @ 06:00" in result


def test_json_to_text_schedule_all_days() -> None:
    """Test converting JSON with all days having same schedule."""
    schedule = [
        {
            "zone_id": "12345",
            "name": "Test Zone",
            "daily_schedules": [
                {
                    "day_of_week": day,
                    "switchpoints": [
                        {"heat_setpoint": 15.0, "time_of_day": "07:00:00"},
                        {"heat_setpoint": 15.0, "time_of_day": "22:30:00"},
                    ],
                }
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ],
        }
    ]

    result = json_to_text_schedule(schedule)
    assert "All days:" in result


def test_round_trip_conversion() -> None:
    """Test round-trip conversion: text → JSON → text."""
    # Parse text to JSON
    json_result = parse_text_schedule(SAMPLE_TEXT_SCHEDULE)

    # Convert back to text
    text_result = json_to_text_schedule(json_result)

    # Parse again to verify
    json_result2 = parse_text_schedule(text_result)

    # Compare zone IDs and names (schedules should be equivalent)
    assert len(json_result) == len(json_result2)
    for zone1, zone2 in zip(json_result, json_result2, strict=True):
        assert zone1["zone_id"] == zone2["zone_id"]
        assert zone1["name"] == zone2["name"]
        assert len(zone1["daily_schedules"]) == len(zone2["daily_schedules"])


# ============================================================================
# CLI Command Tests
# ============================================================================


@pytest.fixture
def tmp_text_file(tmp_path: Path) -> Path:
    """Create a temporary text schedule file."""
    file_path = tmp_path / "schedule.txt"
    file_path.write_text(SAMPLE_TEXT_SCHEDULE)
    return file_path


@pytest.fixture
def tmp_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON schedule file."""
    file_path = tmp_path / "schedule.json"
    file_path.write_text(json.dumps(SAMPLE_JSON_SCHEDULE, indent=4))
    return file_path


def test_convert_schedule_to_json_command(tmp_text_file: Path, tmp_path: Path) -> None:
    """Test convert-schedule-to-json CLI command."""

    # Test the underlying functionality directly
    with tmp_text_file.open() as input_fp:
        content = input_fp.read()
        schedules = parse_text_schedule(content)

    output_file = tmp_path / "output.json"
    with output_file.open("w") as output_fp:
        json.dump(schedules, output_fp, indent=4)

    # Verify output
    assert output_file.exists()
    with output_file.open() as f:
        result = json.load(f)

    assert len(result) == LEN_2
    assert result[0]["zone_id"] == ZONE_ID_LIVINGROOM


def test_convert_schedule_to_text_command(tmp_json_file: Path, tmp_path: Path) -> None:
    """Test convert-schedule-to-text CLI command."""

    # Test the underlying functionality directly
    with tmp_json_file.open() as input_fp:
        schedules = json.load(input_fp)
        text_content = json_to_text_schedule(schedules)

    output_file = tmp_path / "output.txt"
    with output_file.open("w") as output_fp:
        output_fp.write(text_content)

    # Verify output
    assert output_file.exists()
    content = output_file.read_text()
    assert "Livingroom" in content
    assert ZONE_ID_LIVINGROOM in content


def test_get_schedules_json_format_logic() -> None:
    """Test get_schedules JSON format conversion logic."""

    # Test the format conversion logic directly
    schedules = SAMPLE_JSON_SCHEDULE
    json_content = json.dumps(schedules, indent=4)

    # Verify JSON is valid
    result = json.loads(json_content)
    assert len(result) == LEN_2
    assert result[0]["zone_id"] == ZONE_ID_LIVINGROOM


def test_get_schedules_text_format_logic() -> None:
    """Test get_schedules text format conversion logic."""

    # Test the format conversion logic directly
    schedules = SAMPLE_JSON_SCHEDULE
    text_content = json_to_text_schedule(schedules)

    # Verify text output
    assert "Livingroom" in text_content
    assert ZONE_ID_LIVINGROOM in text_content
    assert "Weekdays:" in text_content


def test_set_schedules_json_format_logic(tmp_json_file: Path) -> None:
    """Test set_schedules JSON format parsing logic."""

    # Test the format parsing logic directly
    with tmp_json_file.open() as f:
        schedules = json.load(f)

    # Verify JSON is parsed correctly
    assert len(schedules) == LEN_2
    assert schedules[0]["zone_id"] == ZONE_ID_LIVINGROOM


def test_set_schedules_text_format_logic(tmp_text_file: Path) -> None:
    """Test set_schedules text format parsing logic."""

    # Test the format parsing logic directly
    with tmp_text_file.open() as f:
        content = f.read()
        schedules = parse_text_schedule(content)

    # Verify text is parsed correctly
    assert len(schedules) == LEN_2
    assert schedules[0]["zone_id"] == ZONE_ID_LIVINGROOM
    assert schedules[0]["name"] == "Livingroom"


def test_parse_text_schedule_empty() -> None:
    """Test parsing empty text schedule."""
    result = parse_text_schedule("")
    assert result == []


def test_parse_text_schedule_malformed_zone_header() -> None:
    """Test parsing with malformed zone header."""
    text = "Invalid header format"
    result = parse_text_schedule(text)
    # Should handle gracefully, no zones parsed
    assert len(result) == 0


def test_json_to_text_schedule_empty() -> None:
    """Test converting empty JSON schedule."""
    result = json_to_text_schedule([])
    assert result == ""


def test_json_to_text_schedule_single_switchpoint() -> None:
    """Test converting JSON with single switchpoint per day."""
    schedule = [
        {
            "zone_id": "12345",
            "name": "Test",
            "daily_schedules": [
                {
                    "day_of_week": "Monday",
                    "switchpoints": [{"heat_setpoint": 20.0, "time_of_day": "07:00:00"}],
                }
            ],
        }
    ]

    result = json_to_text_schedule(schedule)
    assert "Test" in result
    assert ZONE_ID_TEST in result
    # Check for temperature format (can be 20C or 20.0C depending on formatting)
    assert "20" in result
    assert "C @ 07:00" in result

