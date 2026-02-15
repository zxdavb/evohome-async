# LogTemperature Command CSV Format

The `poll` command outputs temperature data to a CSV file. This document describes the structure and format of this CSV output.

## Overview

The CSV file contains time-series data with timestamps, system mode status, and zone temperatures. Each row represents a single reading taken at the specified interval.

## File Structure

The CSV file uses standard CSV format with:
- Comma-separated values
- First row contains column headers
- Subsequent rows contain data values
- UTF-8 encoding

## Column Structure

### Column Order

1. **`timestamp`** (required): ISO 8601 formatted timestamp
2. **`system_mode`** (required): System mode status
3. **Zone columns** (variable): One column per zone, named as `{zone_id}_{zone_name}`

### Column Details

#### `timestamp`

- **Format**: ISO 8601 (e.g., `2025-01-15T10:30:00.123456`)
- **Description**: The exact time when the temperature reading was taken
- **Example**: `2025-01-15T10:30:00.123456`

#### `system_mode`

- **Format**: String (enum value)
- **Description**: The current system mode status from the TCS (Temperature Control System)
- **Possible Values**:
  - `Auto`: Normal automatic mode following schedules
  - `AutoWithEco`: Automatic mode with energy-saving adjustments
  - `Away`: Away mode (reduced heating)
  - `DayOff`: Day off mode
  - `Custom`: Custom mode
  - `HeatingOff`: Heating disabled
- **Example**: `AutoWithEco`

#### Zone Columns: `{zone_id}_{zone_name}`

- **Format**: String (zone ID) + underscore + zone name (spaces replaced with underscores)
- **Description**: Temperature reading for a specific zone
- **Naming Convention**:
  - Zone ID (numeric string, e.g., `5262675`)
  - Underscore separator (`_`)
  - Zone name with spaces replaced by underscores
- **Value Format**: 
  - Numeric temperature with 1 decimal place (e.g., `16.5`) when available
  - `N/A` when temperature is unavailable
- **Examples**:
  - Column name: `5262675_Livingroom`
  - Column name: `5262676_Hall_upstairs` (note the underscore replacing the space)
  - Column name: `5262677_Room_1`
  - Value: `16.5` or `N/A`

## Example CSV File

```csv
timestamp,system_mode,5262675_Livingroom,5262676_Kitchen,5262677_Room_1
2025-01-15T10:30:00.123456,AutoWithEco,16.5,20.0,14.5
2025-01-15T10:31:00.234567,AutoWithEco,16.6,20.1,14.6
2025-01-15T10:32:00.345678,Auto,16.7,20.2,14.7
2025-01-15T10:33:00.456789,Auto,16.8,N/A,14.8
```

## Data Characteristics

### Timestamp Precision

- Timestamps include microsecond precision when available
- Format: `YYYY-MM-DDTHH:MM:SS.ffffff`
- Timezone: Local system time (not UTC)

### Temperature Values

- **Available**: Displayed as decimal number with 1 decimal place (e.g., `16.5`, `20.0`)
- **Unavailable**: Displayed as `N/A` (string literal)
- **Units**: Degrees Celsius (no unit symbol in CSV)

### System Mode Values

- System mode values are string representations of the SystemMode enum
- Values are case-sensitive
- Mode can change between readings if the system mode is changed

### Zone Column Names

- Zone column names are determined at the start of logging
- Column order is based on the order zones are discovered in the TCS
- If zones are added or removed during logging, the CSV structure remains consistent (new zones won't appear, removed zones will show `N/A`)

## File Handling

### New Files

When creating a new CSV file:
- Header row is written immediately
- First data row is written after the first temperature reading

### Appending to Existing Files

When appending to an existing file (default behavior):
- Header row is **not** written again
- New data rows are appended to the end of the file
- The existing file structure is preserved

### Overwriting Existing Files

When overwriting an existing file (using `--overwrite`):
- Header row is written
- All previous data is replaced
- New data rows are written starting from the beginning

## Usage Examples

### Reading the CSV File

**Python:**
```python
import csv

with open('temperatures.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        timestamp = row['timestamp']
        mode = row['system_mode']
        livingroom_temp = row.get('5262675_Livingroom', 'N/A')
        print(f"{timestamp}: Mode={mode}, Livingroom={livingroom_temp}")
```

**Pandas:**
```python
import pandas as pd

df = pd.read_csv('temperatures.csv', parse_dates=['timestamp'])
print(df.head())
print(df['system_mode'].value_counts())
```

**Excel/Spreadsheet:**
- Open the CSV file directly in Excel, Google Sheets, or similar
- The comma-separated format is automatically recognized
- Timestamps can be formatted as dates/times
- Temperature columns can be used for charts and analysis

### Analyzing the Data

**Filter by System Mode:**
```python
import pandas as pd

df = pd.read_csv('temperatures.csv', parse_dates=['timestamp'])
away_mode = df[df['system_mode'] == 'Away']
print(away_mode.describe())
```

**Temperature Trends:**
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('temperatures.csv', parse_dates=['timestamp'])
df['5262675_Livingroom'] = pd.to_numeric(df['5262675_Livingroom'], errors='coerce')
df.plot(x='timestamp', y='5262675_Livingroom', kind='line')
plt.show()
```

## Notes

- The CSV file grows continuously as data is logged
- File size depends on:
  - Number of zones
  - Logging interval
  - Duration of logging session
- Zone column names are fixed at the start of logging
- If a zone's temperature becomes unavailable during logging, subsequent rows will show `N/A` for that zone
- System mode changes are captured in real-time
- The file can be safely opened and analyzed while logging is in progress (new rows are appended)

## Related Documentation

- See `docs/CLI.md` for command usage and options
- See `docs/DumpJSON.md` for the structure of the underlying data source
- See `docs/Architecture.md` for implementation details

