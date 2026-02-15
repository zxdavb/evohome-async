# Evohome Async CLI Documentation

The `evo-client` CLI utility provides a command-line interface for interacting with the Honeywell TCC (Total Connect Comfort) API.

## Installation

The CLI is available as part of the `evohome-async` package. Install it using:

```bash
pip install evohome-async
```

## Main CLI Options

Most commands require authentication. You can provide credentials in two ways:

1. **Command-line options** (recommended for scripts):
   - `--username` / `-u`: TCC account username
   - `--password` / `-p`: TCC account password

2. **Stored credentials** (recommended for interactive use):
   - Use the `login` command to store credentials securely
   - Credentials are stored in the system's secure credential store
   - Once stored, you can omit `--username` and `--password` from commands

**Other global options:**
- `--no-tokens` / `-c` (flag): Don't load the token cache
- `--debug` / `-d` (flag): Enable debug logging and wait for debugger attachment

**Note**: If neither command-line credentials nor stored credentials are available, commands will fail with an error message.

## Available Commands

### 1. `login`

Stores TCC account credentials securely for future use. This command does not require authentication.

**Options:**
- `--username` / `-u`: TCC account username (prompted if not provided)
- `--password` / `-p`: TCC account password (prompted if not provided, hidden input)
- `--delete` / `-d` (flag): Delete stored credentials

**Credential Storage:**
Credentials are stored in your system's secure credential store:
- **macOS**: Keychain Access (System Keychain)
- **Windows**: Windows Credential Manager
- **Linux**: Secret Service (GNOME Keyring, KWallet, etc.)

**Requirements:**
- The `keyring` package must be installed: `pip install keyring`
- On Linux, you may need a Secret Service implementation (usually pre-installed)

**Examples:**
```bash
# Interactive login (will prompt for username and password)
evo-client login

# Login with command-line credentials
evo-client login -u myuser@example.com -p mypassword

# Delete stored credentials
evo-client login --delete
```

**After logging in:**
Once credentials are stored, you can use other commands without `--username` and `--password`:
```bash
# These commands will use stored credentials automatically
evo-client get_schedules -o schedules.json
evo-client set_schedules -i schedules.json
```

---

### 2. `mode`

Retrieves the system mode.

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index

**Example:**
```bash
# With stored credentials
evo-client mode --loc-idx 0

# With command-line credentials
evo-client -u username -p password mode --loc-idx 0
```

**Output:**
Displays the current system mode (e.g., Auto, Away, DayOff, etc.)

---

### 3. `dump`

Downloads all the global config and the location status.

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index
- `--output-file` / `-o` (default: stdout): The output file path

**Example:**
```bash
# With stored credentials
evo-client dump --loc-idx 0 -o config.json

# With command-line credentials
evo-client -u username -p password dump --loc-idx 0 -o config.json
```

**Output:**
A JSON file containing:
- `config`: The location configuration
- `status`: The current location status

For detailed information about the JSON structure, see [DumpJSON.md](DumpJSON.md).

---

### 4. `poll`

Continuously polls zone temperatures at regular intervals. Temperatures are written to a CSV file and optionally displayed on screen in a table format. Optionally sends data to InfluxDB.

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index
- `--interval` / `-i` (default: "60s"): Interval between temperature readings (30s to 120m)
  - Format: number followed by 's' (seconds) or 'm' (minutes)
  - Examples: `30s`, `1m`, `120m`
- `--output-file` / `-o` (required): Output CSV file for temperature timeseries data
- `--append` / `-a` (flag): Append to existing file if it exists (skips header)
- `--overwrite` (flag): Overwrite existing file if it exists
- `--noshow` (flag): Do not display temperatures on screen (only write to file)
- `--influx` (flag): Send data to InfluxDB
- `--importcsv` (flag): Import existing CSV file to InfluxDB before starting

**File Handling:**
- If the output file already exists:
  - **Default behavior**: Automatically append to the file (header will not be duplicated)
  - If `--overwrite` is specified: Overwrite the file (header will be written)
  - If `--append` / `-a` is specified: Explicitly append (same as default, but makes intent clear)
- Note: `--append` and `--overwrite` are mutually exclusive (cannot be used together)

**Interactive Features:**
- Press `L` (or `l`) to show the zone list (zone ID -> zone name mapping) and column headers, then continue logging
- Press `Ctrl+C` to stop logging

**Output Format:**

**CSV File:**
- First column: `timestamp` (ISO 8601 format)
- Second column: `system_mode` (system mode status, e.g., "AutoWithEco", "Auto", "Away")
- Subsequent columns: `{zone_id}_{zone_name}` (spaces in zone names replaced with underscores)
- Example column names: `timestamp`, `system_mode`, `5262675_Livingroom`, `5262676_Hall_upstairs`, `5262677_Room_1`
- For detailed CSV format documentation, see `docs/LogTemperatureCSV.md`

**Screen Display:**
- Fixed-width columns showing time, system mode, and zone temperatures
- Zone IDs are used as column headers
- System mode is displayed (e.g., "AutoWithEco", "Auto", "Away")
- Temperature values are displayed with 1 decimal place, or "N/A" if unavailable
- Example:
  ```
  Time                 Mode           5262675  5262676  5262677
  -------------------------------------------------------------
  2025-01-15 10:30:00 AutoWithEco      16.5    17.5    14.5
  2025-01-15 10:31:00 AutoWithEco      16.6    17.6    14.6
  ```

**Examples:**
```bash
# Poll temperatures every 60 seconds, display on screen
evo-client poll -i 60s -o temperatures.csv

# Poll temperatures every 2 minutes, no screen display
evo-client poll -i 2m -o temperatures.csv --noshow

# Poll temperatures every 30 seconds for a specific location
evo-client poll -l 1 -i 30s -o location1_temps.csv

# Poll temperatures and send to InfluxDB
evo-client poll -i 60s -o temperatures.csv --influx

# Import existing CSV to InfluxDB and continue polling
evo-client poll -i 60s -o temperatures.csv --influx --importcsv
```

**Notes:**
- The command runs continuously until interrupted with `Ctrl+C`
- Temperature readings are taken by calling the dump command at the specified interval
- If a zone's temperature is unavailable, it will be recorded as "N/A" in the CSV and displayed as "N/A" on screen
- Zone names with spaces are converted to underscores in CSV column names (e.g., "Hall upstairs" becomes "Hall_upstairs")
- Keyboard input for the 'L' key may not work on Windows systems

---

### 6. `get_schedule`

Downloads the schedule of a specific zone or hot water (Work In Progress).

**Arguments:**
- `zone-id` (required): The zone ID (e.g., "00" to "11", or "HW" for hot water)

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index
- `--output-file` / `-o` (default: stdout): The output file path

**Example:**
```bash
# With stored credentials
evo-client get_schedule 00 --loc-idx 0 -o schedule.json

# With command-line credentials
evo-client -u username -p password get_schedule 00 --loc-idx 0 -o schedule.json
```

**Output:**
A JSON file containing the schedule for the specified zone:
```json
{
  "zone_id": {
    "name": "Zone Name",
    "schedule": { ... }
  }
}
```

---

### 7. `get_schedules`

Downloads all schedules from a Temperature Control System (TCS).

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index
- `--output-file` / `-o` (default: stdout): The output file path

**Example:**
```bash
# With stored credentials
evo-client get_schedules --loc-idx 0 -o all_schedules.json

# With command-line credentials
evo-client -u username -p password get_schedules --loc-idx 0 -o all_schedules.json
```

**Output:**
A JSON file containing all schedules for all zones and hot water in the TCS.

**Note:** This command will abort with an error message if no TCS is found at the specified location index.

---

### 8. `set_schedules`

Uploads schedules to a Temperature Control System (TCS).

**Options:**
- `--loc-idx` / `-l` (default: 0): The location index
- `--input-file` / `-i` (required): The input file containing schedules in JSON format

**Example:**
```bash
# With stored credentials
evo-client set_schedules --loc-idx 0 -i schedules.json

# With command-line credentials
evo-client -u username -p password set_schedules --loc-idx 0 -i schedules.json
```

**Input Format:**
The input file should contain a JSON object with schedules in the same format as returned by `get_schedules`.

**Output:**
- Success message if all schedules were uploaded successfully
- Error message if any errors occurred during upload

**Note:** This command will abort with an error message if no TCS is found at the specified location index.

---

## Common Options

### Location Index (`--loc-idx` / `-l`)

Most commands support the `--loc-idx` option to specify which location to operate on. If you have multiple locations in your account, use this to select a specific one. The default is `0` (the first location).

### Output File (`--output-file` / `-o`)

Commands that retrieve data support the `--output-file` option to save results to a file. If not specified, output is written to stdout. Use `-` to explicitly specify stdout.

### Input File (`--input-file` / `-i`)

Commands that upload data require the `--input-file` option to specify the source file containing the data to upload.

---

## Authentication and Token Caching

By default, the CLI caches authentication tokens to avoid repeated logins. The token cache is stored locally and reused across CLI invocations.

- To disable token caching, use the `--no-tokens` / `-c` flag
- Tokens are automatically saved after each successful command execution
- If authentication fails, the session is closed and an error is displayed

---

## Debugging

The `--debug` / `-d` flag enables:

1. **Debug logging**: All log messages at DEBUG level and above are displayed
2. **Debugger attachment**: The CLI will pause execution and wait for a debugger to attach on `0.0.0.0:5679`

**Example:**
```bash
evo-client -u username -p password --debug mode
```

This is useful for troubleshooting issues or developing new features.

---

## Error Handling

The CLI handles various error conditions:

- **Authentication failures**: If login fails, the session is closed and an error message is displayed
- **Missing TCS**: Commands that require a TCS will abort with a clear error message if none is found
- **Invalid parameters**: Click validation ensures parameters are within valid ranges
- **Network errors**: Errors are displayed with appropriate context

---

## Usage Examples

### Get the current system mode
```bash
evo-client -u myuser@example.com -p mypassword mode
```

### Backup all schedules to a file
```bash
evo-client -u myuser@example.com -p mypassword get_schedules -o backup_schedules.json
```

### Restore schedules from a backup
```bash
evo-client -u myuser@example.com -p mypassword set_schedules -i backup_schedules.json
```

### Get configuration and status for a specific location
```bash
evo-client -u myuser@example.com -p mypassword dump --loc-idx 1 -o location1.json
```

### Get a specific zone's schedule
```bash
evo-client -u myuser@example.com -p mypassword get_schedule 00 -o zone00_schedule.json
```

---

## Notes

- The CLI uses asyncclick and requires Python 3.12+
- All commands authenticate and update the client before executing
- The `--debug` flag enables debug logging and can pause execution for debugger attachment
- Token caching is enabled by default (use `--no-tokens` to disable)
- The entry point is defined as `evo-client` in the package configuration

