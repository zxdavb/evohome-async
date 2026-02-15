"""Parse and convert between text and JSON schedule formats."""

from __future__ import annotations

import re
from typing import Any

# Day name mappings
DAY_NAMES: dict[str, str] = {
    "Monday": "Monday",
    "Tuesday": "Tuesday",
    "Wednesday": "Wednesday",
    "Thursday": "Thursday",
    "Friday": "Friday",
    "Saturday": "Saturday",
    "Sunday": "Sunday",
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sun": "Sunday",
}

# Reverse mapping: full name to abbreviation
DAY_ABBREVIATIONS: dict[str, str] = {
    "Monday": "Mon",
    "Tuesday": "Tue",
    "Wednesday": "Wed",
    "Thursday": "Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun",
}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKENDS = ["Saturday", "Sunday"]
ALL_DAYS = WEEKDAYS + WEEKENDS


def parse_temperature_time(text: str) -> list[tuple[float, str]]:
    """Parse a schedule line like '16C @ 06:00 to 17.5C @ 21:50'."""
    # Pattern to match: temperatureC @ HH:MM
    pattern = r"(\d+\.?\d*)C\s*@\s*(\d{1,2}):(\d{2})"
    matches = re.findall(pattern, text)

    switchpoints = []
    for temp_str, hour, minute in matches:
        temp = float(temp_str)
        # Convert time to HH:MM:SS format
        time_str = f"{int(hour):02d}:{int(minute):02d}:00"
        switchpoints.append((temp, time_str))

    return switchpoints


def parse_day_spec(day_spec: str) -> list[str]:
    """Parse day specification like 'Weekdays', 'Weekends', 'Mon/Tue/Thu/Fri', 'Wednesday'."""
    spec = day_spec.strip().rstrip(":")

    if spec == "Weekdays":
        return WEEKDAYS
    if spec == "Weekends":
        return WEEKENDS
    if spec == "All days":
        return ALL_DAYS

    if "/" in spec:
        # Handle "Mon/Tue/Thu/Fri" format
        days = []
        for part in spec.split("/"):
            clean_part = part.strip()
            if clean_part in DAY_NAMES:
                days.append(DAY_NAMES[clean_part])
        return days

    # Single day like "Wednesday" or try to match partial names
    res = []
    if spec in DAY_NAMES:
        res = [DAY_NAMES[spec]]
    else:
        for full_name, abbr in DAY_NAMES.items():
            if spec.lower() == full_name.lower() or spec.lower() == abbr.lower():
                res = [full_name]
                break
    return res


# Sequence constants
NUM_PARTS_DAY_SCHED = 2


def parse_text_schedule(text: str) -> list[dict[str, Any]]:
    """Parse the text schedule format and return JSON structure."""
    lines = text.strip().split("\n")
    schedules = []
    current_zone: dict[str, Any] | None = None

    for line in (line.strip() for line in lines):
        if not line:
            continue

        # Check if this is a zone header: "1. Livingroom (5262675)"
        if zone_match := re.match(r"^\d+\.\s+(.+?)\s+\((\d+)\)$", line):
            if current_zone:
                schedules.append(current_zone)

            current_zone = {
                "zone_id": zone_match.group(2),
                "name": zone_match.group(1).strip(),
                "daily_schedules": [],
            }
            continue

        # Check if this is a schedule line
        if current_zone and ":" in line:
            parts = line.split(":", 1)
            if len(parts) != NUM_PARTS_DAY_SCHED:
                continue

            day_spec, schedule_text = parts[0].strip(), parts[1].strip()
            days = parse_day_spec(day_spec)
            switchpoints_data = parse_temperature_time(schedule_text)

            switchpoints = [
                {"heat_setpoint": temp, "time_of_day": time_str}
                for temp, time_str in switchpoints_data
            ]

            for day in days:
                daily_schedule = {"day_of_week": day, "switchpoints": switchpoints}
                # Replace existing schedule for this day if it exists
                current_zone["daily_schedules"] = [
                    ds
                    for ds in current_zone["daily_schedules"]
                    if ds["day_of_week"] != day
                ]
                current_zone["daily_schedules"].append(daily_schedule)

    if current_zone:
        schedules.append(current_zone)

    # Sort daily schedules by day of week
    day_order = {day: idx for idx, day in enumerate(ALL_DAYS)}
    for schedule in schedules:
        schedule["daily_schedules"].sort(
            key=lambda x: day_order.get(x["day_of_week"], 999)
        )

    return schedules


def _switchpoints_equal(sp1: list[dict[str, Any]], sp2: list[dict[str, Any]]) -> bool:
    """Check if two switchpoint lists are equal."""
    if len(sp1) != len(sp2):
        return False
    for s1, s2 in zip(sp1, sp2, strict=False):
        if s1.get("heat_setpoint") != s2.get("heat_setpoint"):
            return False
        if s1.get("time_of_day") != s2.get("time_of_day"):
            return False
    return True


def _format_switchpoints(switchpoints: list[dict[str, Any]]) -> str:
    """Format switchpoints as text: '16C @ 06:00 to 17.5C @ 21:50'."""
    parts = []
    for sp in switchpoints:
        temp = sp.get("heat_setpoint", 0.0)
        # Format temperature: use integer if whole number, otherwise decimal
        temp_str = str(int(temp)) if temp == int(temp) else str(temp)
        time_str = sp.get("time_of_day", "00:00:00")
        # Convert HH:MM:SS to HH:MM
        time_parts = time_str.split(":")
        time_short = f"{time_parts[0]}:{time_parts[1]}"
        parts.append(f"{temp_str}C @ {time_short}")
    return " to ".join(parts)


def _group_days_by_schedule(
    daily_schedules: list[dict[str, Any]],
) -> dict[tuple[Any, ...], list[str]]:
    """Group days by their switchpoint pattern."""
    # Create a hashable key from switchpoints
    groups: dict[tuple[Any, ...], list[str]] = {}

    for daily in daily_schedules:
        day = daily["day_of_week"]
        switchpoints = daily["switchpoints"]
        # Create a tuple key from switchpoints
        key = tuple(
            (sp.get("heat_setpoint"), sp.get("time_of_day")) for sp in switchpoints
        )
        if key not in groups:
            groups[key] = []
        groups[key].append(day)

    return groups


def _format_day_spec(days: list[str]) -> str:
    """Format a list of days into the best day specification."""
    days_set = set(days)

    if days_set == set(ALL_DAYS):
        return "All days"
    if days_set == set(WEEKDAYS):
        return "Weekdays"
    if days_set == set(WEEKENDS):
        return "Weekends"

    # Subset of weekdays or weekends or single day
    if days_set.issubset(set(WEEKDAYS)) and len(days) > 1:
        order = WEEKDAYS
    elif days_set.issubset(set(WEEKENDS)) and len(days) > 1:
        order = WEEKENDS
    elif len(days) == 1:
        return days[0]
    else:
        order = ALL_DAYS

    day_order = {day: idx for idx, day in enumerate(order)}
    sorted_days = sorted(days, key=lambda d: day_order.get(d, 999))
    abbrs = [DAY_ABBREVIATIONS.get(day, day) for day in sorted_days]
    return "/".join(abbrs)


def json_to_text_schedule(schedules: list[Any]) -> str:
    """Convert JSON schedule format to text schedule format."""
    lines = []
    zone_num = 1

    for schedule in schedules:
        zone_id = schedule.get("zone_id", "")
        name = schedule.get("name", "")
        daily_schedules = schedule.get("daily_schedules", [])

        # Zone header
        lines.append(f"{zone_num}. {name} ({zone_id})")

        # Group days by their switchpoint patterns
        groups = _group_days_by_schedule(daily_schedules)

        # Sort groups by the first day in each group (for consistent output)
        day_order = {day: idx for idx, day in enumerate(ALL_DAYS)}

        def sort_key(
            group_item: tuple[tuple[Any, ...], list[str]],
            order: dict[str, int] = day_order,
        ) -> int:
            """Sort by the minimum day index in the group."""
            _, days_list = group_item
            if not days_list:
                return 999
            return min(order.get(day, 999) for day in days_list)

        sorted_groups = sorted(groups.items(), key=sort_key)

        # Format each group
        for _switchpoint_key, days_list in sorted_groups:
            # Get the switchpoints from the first day in this group
            switchpoints = None
            for daily in daily_schedules:
                if daily["day_of_week"] in days_list:
                    switchpoints = daily["switchpoints"]
                    break

            if switchpoints:
                day_spec = _format_day_spec(days_list)
                switchpoint_text = _format_switchpoints(switchpoints)
                lines.append(f"{day_spec}: {switchpoint_text}")

        zone_num += 1
        # Add blank line between zones (except after last)
        if zone_num <= len(schedules):
            lines.append("")

    return "\n".join(lines)
