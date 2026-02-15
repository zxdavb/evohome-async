# Text Schedule Format Documentation

This document describes the human-readable text format for heating schedules used as an alternative to the JSON format. This format is easier to read and edit manually, and can be converted to the JSON format described in [ScheduleJSON.md](ScheduleJSON.md) for use with the CLI commands.

## Overview

The text schedule format provides a simple, readable way to define heating schedules for multiple zones. Each zone is defined with its name and ID, followed by schedule lines that specify temperature changes throughout the week.

## Structure

### Zone Header

Each zone starts with a header line in the format:

```
<number>. <zone_name> (<zone_id>)
```

**Components:**
- `<number>`: Sequential number (1, 2, 3, etc.) - used for organization only
- `<zone_name>`: Human-readable name of the zone (e.g., "Livingroom", "Kitchen")
- `<zone_id>`: Unique identifier for the zone (numeric string, e.g., "5262675")

**Example:**
```
1. Livingroom (5262675)
```

### Schedule Lines

After the zone header, one or more schedule lines define when temperature changes occur. Each schedule line follows this format:

```
<day_spec>: <temperature>C @ <time> to <temperature>C @ <time> [to ...]
```

**Components:**
- `<day_spec>`: Specifies which days this schedule applies to (see Day Specifications below)
- `<temperature>`: Target temperature in degrees Celsius (can be decimal, e.g., `16.0`, `21.5`)
- `<time>`: Time in 24-hour format as `HH:MM` (e.g., `06:00`, `21:50`)
- Multiple temperature/time pairs can be chained with `to` to create multiple switchpoints

**Examples:**
```
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30
All days: 18C @ 07:00 to 15C @ 08:30
```

### Day Specifications

The `<day_spec>` field can be one of the following:

| Specification | Description | Days Included |
|--------------|-------------|---------------|
| `Weekdays` | Monday through Friday | Monday, Tuesday, Wednesday, Thursday, Friday |
| `Weekends` | Saturday and Sunday | Saturday, Sunday |
| `All days` | All seven days of the week | Monday through Sunday |
| `Monday` | Single day (full name) | Monday only |
| `Tuesday` | Single day (full name) | Tuesday only |
| `Wednesday` | Single day (full name) | Wednesday only |
| `Thursday` | Single day (full name) | Thursday only |
| `Friday` | Single day (full name) | Friday only |
| `Saturday` | Single day (full name) | Saturday only |
| `Sunday` | Single day (full name) | Sunday only |
| `Mon/Tue/Thu/Fri` | Multiple specific days (abbreviated) | Monday, Tuesday, Thursday, Friday |

**Day Abbreviations:**
- `Mon` = Monday
- `Tue` = Tuesday
- `Wed` = Wednesday
- `Thu` = Thursday
- `Fri` = Friday
- `Sat` = Saturday
- `Sun` = Sunday

**Note:** When multiple day specifications apply to the same day, the last one encountered takes precedence.

## Complete Example

Here is a complete example showing multiple zones with different schedule patterns:

```
1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30

2. Hall upstairs (5262676)
Weekdays: 15C @ 07:00 to 19C @ 14:30
Weekends: 21.5C @ 07:00 to 21.5C @ 22:30

3. Room 1 (5262677)
All days: 15C @ 07:00 to 15C @ 22:30

4. Kitchen (5262678)
Weekdays: 20C @ 07:00 to 15C @ 19:30
Weekends: 20C @ 07:00 to 15C @ 20:30

5. Dining (5262680)
Weekdays: 21C @ 06:30 to 18C @ 08:00 to 21C @ 18:00 to 16C @ 22:30
Weekends: 21C @ 08:00 to 21C @ 10:00 to 21C @ 18:00 to 16C @ 23:00

6. Room 4 (5262682)
Mon/Tue/Thu/Fri: 15C @ 07:00 to 15C @ 22:30
Wednesday: 15C @ 07:00 to 15C @ 12:00 to 15C @ 22:30
Weekends: 15C @ 07:00 to 15C @ 22:30
```

## Format Rules

### Temperature Format
- Temperature values are specified in degrees Celsius
- Can be integers (e.g., `15`, `21`) or decimals (e.g., `16.5`, `21.5`)
- Must include the `C` unit indicator
- Typical range: 5C to 35C (exact range depends on system capabilities)

### Time Format
- Time is specified in 24-hour format
- Format: `HH:MM` (e.g., `06:00`, `21:50`, `23:00`)
- Hours: `00` to `23`
- Minutes: `00` to `59`
- No seconds are specified (they default to `00` when converted to JSON)

### Switchpoint Chains
- Multiple switchpoints can be chained using `to`
- Each switchpoint consists of a temperature and time pair
- Switchpoints should be in chronological order within each schedule line
- There is no limit on the number of switchpoints per day

**Example with multiple switchpoints:**
```
Weekdays: 21C @ 06:30 to 18C @ 08:00 to 21C @ 18:00 to 16C @ 22:30
```

This creates four switchpoints:
1. 21C at 06:30
2. 18C at 08:00
3. 21C at 18:00
4. 16C at 22:30

### Whitespace
- Leading and trailing whitespace on lines is ignored
- Spaces around colons, `@` symbols, and `to` keywords are optional but recommended for readability
- Blank lines between zones are allowed and ignored

### Zone Ordering
- Zones can be listed in any order
- The sequential number at the start of each zone header is for human readability only and doesn't affect parsing

## Conversion to JSON Format

The text schedule format can be converted to the JSON format described in [ScheduleJSON.md](ScheduleJSON.md) using a parser script. The conversion process:

1. **Zone Headers** → JSON `zone_id` and `name` fields
2. **Schedule Lines** → JSON `daily_schedules` array with `day_of_week` and `switchpoints`
3. **Temperature/Time Pairs** → JSON `heat_setpoint` and `time_of_day` (converted to `HH:MM:SS` format)
4. **Day Specifications** → Expanded to individual `day_of_week` entries for each applicable day

### Conversion Example

**Text Format:**
```
1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30
```

**JSON Format (equivalent):**
```json
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
    }
    // ... (Wednesday, Thursday, Friday with same schedule)
    // ... (Saturday, Sunday with weekend schedule)
  ]
}
```

## Common Patterns

### Simple Two-Switchpoint Schedule
Most zones use a simple pattern with two switchpoints per day:
```
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
```
This sets the temperature at 6 AM and changes it again at 9:50 PM.

### Constant Temperature
To maintain the same temperature all day, use the same temperature for both switchpoints:
```
All days: 15C @ 07:00 to 15C @ 22:30
```

### Multiple Temperature Changes
For zones that need multiple temperature adjustments throughout the day:
```
Weekdays: 21C @ 06:30 to 18C @ 08:00 to 21C @ 18:00 to 16C @ 22:30
```

### Different Weekday/Weekend Schedules
Use separate lines for weekdays and weekends:
```
Weekdays: 20C @ 07:00 to 15C @ 19:30
Weekends: 20C @ 07:00 to 15C @ 20:30
```

### Special Day Handling
Override specific days with different schedules:
```
Mon/Tue/Thu/Fri: 15C @ 07:00 to 15C @ 22:30
Wednesday: 15C @ 07:00 to 15C @ 12:00 to 15C @ 22:30
Weekends: 15C @ 07:00 to 15C @ 22:30
```

## Best Practices

1. **Consistency**: Use consistent formatting throughout the file for easier reading and maintenance.

2. **Complete Schedules**: Ensure all seven days of the week have schedules defined. If a day isn't explicitly mentioned, it may use a default or the last applicable schedule.

3. **Chronological Order**: List switchpoints in chronological order within each schedule line.

4. **Clear Zone Names**: Use descriptive zone names that make it easy to identify the location.

5. **Comments**: While the format doesn't officially support comments, you can add blank lines between zones for visual separation.

6. **Validation**: After editing, convert to JSON format and validate that all schedules are correct before using with the CLI.

## Limitations

- The text format does not support domestic hot water (DHW) schedules - only zone schedules
- No support for comments or annotations
- Day specifications must match exactly (case-sensitive for full day names)
- Time format is limited to HH:MM (seconds are always assumed to be 00)

## Related Documentation

- [ScheduleJSON.md](ScheduleJSON.md) - JSON format documentation
- [CLI.md](CLI.md) - Command-line interface documentation

