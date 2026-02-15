# Schedule JSON Format Documentation

This document describes the structure of the schedule JSON format used by the `get_schedules` and `set_schedules` CLI commands.

## Overview

The schedule JSON format is used to backup and restore heating schedules for zones and domestic hot water (DHW) systems. The format is an array of schedule objects, where each object represents the complete schedule for a single zone or DHW system.

## Structure

### Root Level

The root element is a JSON array containing one or more schedule objects:

```json
[
  { /* schedule object */ },
  { /* schedule object */ },
  ...
]
```

### Schedule Object

Each schedule object represents the schedule for a single zone or DHW system. It contains the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `zone_id` | `string` | Yes* | The unique identifier for a zone. Required for zone schedules. |
| `dhw_id` | `string` | Yes* | The unique identifier for a domestic hot water system. Required for DHW schedules. |
| `name` | `string` | No | Human-readable name of the zone or DHW system (e.g., "Livingroom", "Kitchen"). |
| `daily_schedules` | `array` | Yes | Array of daily schedule objects, one for each day of the week. |

\* **Note**: Exactly one of `zone_id` or `dhw_id` must be present. Use `zone_id` for heating zones and `dhw_id` for domestic hot water systems.

### Daily Schedule Object

Each daily schedule object represents the schedule for a single day of the week:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `day_of_week` | `string` | Yes | The day name. Must be one of: `"Monday"`, `"Tuesday"`, `"Wednesday"`, `"Thursday"`, `"Friday"`, `"Saturday"`, `"Sunday"`. |
| `switchpoints` | `array` | Yes | Array of switchpoint objects defining temperature changes throughout the day. |

### Switchpoint Object

Switchpoints define when the temperature (or DHW state) changes. The structure differs slightly between zones and DHW:

#### Zone Switchpoint

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `heat_setpoint` | `float` | Yes | The target temperature in degrees (e.g., `16.0`, `21.5`). |
| `time_of_day` | `string` | Yes | Time in 24-hour format as `"HH:MM:SS"` (e.g., `"06:00:00"`, `"21:50:00"`). |

#### DHW Switchpoint

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dhw_state` | `string` | Yes | The state of the hot water system (e.g., `"On"`, `"Off"`). |
| `time_of_day` | `string` | Yes | Time in 24-hour format as `"HH:MM:SS"` (e.g., `"06:00:00"`, `"22:00:00"`). |

## Complete Example

Here is a complete example showing schedules for two zones:

```json
[
  {
    "zone_id": "5262675",
    "name": "Livingroom",
    "daily_schedules": [
      {
        "day_of_week": "Monday",
        "switchpoints": [
          {
            "heat_setpoint": 16.0,
            "time_of_day": "06:00:00"
          },
          {
            "heat_setpoint": 17.5,
            "time_of_day": "21:50:00"
          }
        ]
      },
      {
        "day_of_week": "Tuesday",
        "switchpoints": [
          {
            "heat_setpoint": 16.0,
            "time_of_day": "06:00:00"
          },
          {
            "heat_setpoint": 17.5,
            "time_of_day": "21:50:00"
          }
        ]
      },
      {
        "day_of_week": "Wednesday",
        "switchpoints": [
          {
            "heat_setpoint": 16.0,
            "time_of_day": "06:00:00"
          },
          {
            "heat_setpoint": 17.5,
            "time_of_day": "21:50:00"
          }
        ]
      },
      {
        "day_of_week": "Thursday",
        "switchpoints": [
          {
            "heat_setpoint": 16.0,
            "time_of_day": "06:00:00"
          },
          {
            "heat_setpoint": 17.5,
            "time_of_day": "21:50:00"
          }
        ]
      },
      {
        "day_of_week": "Friday",
        "switchpoints": [
          {
            "heat_setpoint": 16.0,
            "time_of_day": "06:00:00"
          },
          {
            "heat_setpoint": 17.5,
            "time_of_day": "21:50:00"
          }
        ]
      },
      {
        "day_of_week": "Saturday",
        "switchpoints": [
          {
            "heat_setpoint": 15.0,
            "time_of_day": "07:00:00"
          },
          {
            "heat_setpoint": 15.0,
            "time_of_day": "22:30:00"
          }
        ]
      },
      {
        "day_of_week": "Sunday",
        "switchpoints": [
          {
            "heat_setpoint": 15.0,
            "time_of_day": "07:00:00"
          },
          {
            "heat_setpoint": 15.0,
            "time_of_day": "22:30:00"
          }
        ]
      }
    ]
  },
  {
    "zone_id": "5262676",
    "name": "Kitchen",
    "daily_schedules": [
      {
        "day_of_week": "Monday",
        "switchpoints": [
          {
            "heat_setpoint": 20.0,
            "time_of_day": "07:00:00"
          },
          {
            "heat_setpoint": 15.0,
            "time_of_day": "19:30:00"
          }
        ]
      }
      /* ... other days ... */
    ]
  }
]
```

## Field Constraints and Notes

### Day of Week

- Must be exactly one of the seven day names: `"Monday"`, `"Tuesday"`, `"Wednesday"`, `"Thursday"`, `"Friday"`, `"Saturday"`, `"Sunday"`
- Case-sensitive
- Typically, all seven days should be included in `daily_schedules`, though the API may accept partial schedules

### Time Format

- `time_of_day` must be in 24-hour format: `"HH:MM:SS"`
- Hours: `00` to `23`
- Minutes: `00` to `59`
- Seconds: `00` to `59`
- Examples: `"06:00:00"`, `"21:50:00"`, `"23:59:59"`

### Temperature Setpoints

- `heat_setpoint` is a floating-point number
- Typical range: `5.0` to `35.0` degrees (exact range depends on system capabilities)
- Can include decimal values (e.g., `16.5`, `21.0`)

### Switchpoints

- Switchpoints should be ordered chronologically within each day
- The first switchpoint of the day sets the initial temperature/state
- Subsequent switchpoints change the temperature/state at the specified time
- There is no limit on the number of switchpoints per day, but typically 2-6 switchpoints are used

## Usage with CLI Commands

### Getting Schedules

Use the `get_schedules` command to export all schedules from a system:

```bash
evo-client -u username -p password get_schedules --loc-idx 0 -o schedules.json
```

This will create a JSON file in the format described above, containing schedules for all zones and DHW systems in the specified location.

### Setting Schedules

Use the `set_schedules` command to restore schedules from a JSON file:

```bash
evo-client -u username -p password set_schedules --loc-idx 0 -i schedules.json
```

The command will match schedules to zones/DHW by ID (or by name if using the `match_by_name` option in the API). Schedules that cannot be matched will be logged as warnings but will not cause the command to fail.

### Getting a Single Schedule

To get the schedule for a specific zone:

```bash
evo-client -u username -p password get_schedule 5262675 --loc-idx 0 -o zone_schedule.json
```

Note: The `get_schedule` command returns a slightly different format (wrapped in a zone_id object), but the `daily_schedules` structure is the same.

## API Format Differences

The evohome-async library uses **snake_case** for field names in the exported/imported JSON format (as shown in this documentation), which is more Python-friendly.

However, the underlying TCC API uses **camelCase** for field names:
- `daily_schedules` → `dailySchedules`
- `day_of_week` → `dayOfWeek`
- `heat_setpoint` → `heatSetpoint`
- `time_of_day` → `timeOfDay`
- `zone_id` → `zoneId`
- `dhw_id` → `dhwId`

The library automatically converts between these formats when communicating with the API, so you only need to work with the snake_case format shown in this documentation.

## Validation

When using `set_schedules`, the library performs basic validation:
- Ensures the JSON is valid and parseable
- Validates the structure matches the expected schema
- Checks that required fields are present

If validation fails, an error will be raised with details about what was wrong.

## Best Practices

1. **Backup First**: Always backup your current schedules before making changes:
   ```bash
   evo-client -u username -p password get_schedules -o backup.json
   ```

2. **Complete Schedules**: Include all seven days of the week in your schedules to avoid unexpected behavior.

3. **Ordered Switchpoints**: Ensure switchpoints within each day are in chronological order.

4. **Valid IDs**: Use the exact `zone_id` or `dhw_id` values from your system. You can get these from the `dump` command or by examining a `get_schedules` output.

5. **Test Changes**: Test schedule changes on a single zone first before applying to all zones.

