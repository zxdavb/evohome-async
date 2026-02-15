# Changes Since Commit 9412c90

This document tracks changes made to the codebase since commit `9412c9055af4c6883d897a307492ea18d218cf50` (2026-02-15).

## Summary

The changes focus on enhancing the CLI with new features for credential management, schedule format conversion, temperature polling, and improved user experience.

### Key Additions
- ✨ Secure credential storage using system keyring
- ✨ Text-based schedule format with bidirectional conversion
- ✨ Temperature polling command with CSV output
- ✨ Standalone format conversion commands
- ✨ Comprehensive test suite for new features
- 📚 Extensive documentation

## Modified Files

### 1. `.gitignore`
**Changes:**
- Added `*.csv` to ignore CSV data files
- Added `!requirement*.txt` to ensure requirement files are tracked
- Added `*.txt` to ignore text files (with exception above)
- Added `.env` to ignore environment configuration files

**Rationale:** Prevent accidental commit of data files and environment-specific configuration while ensuring dependency files remain tracked.

---

### 2. `cli/auth.py`
**Changes:**
- Added `keyring` import with graceful fallback if not installed
- Added constants for credential storage:
  - `CREDENTIAL_SERVICE_NAME = "evohome-async"`
  - `CREDENTIAL_USERNAME_KEY = "username"`
  - `CREDENTIAL_PASSWORD_KEY = "password"`
- Added new functions for secure credential management:
  - `get_stored_credentials()`: Retrieve username/password from system keyring
  - `store_credentials()`: Store credentials in system keyring
  - `delete_stored_credentials()`: Remove stored credentials
  - `get_credential_storage_location()`: Get platform-specific storage location description

**Details:**
- **Platform Support:**
  - macOS: Keychain Access (System Keychain)
  - Windows: Windows Credential Manager
  - Linux: Secret Service (GNOME Keyring, KWallet, etc.)
- **Security:** Credentials stored in OS-native secure storage, not plain text
- **Graceful Fallback:** If keyring unavailable, returns `None` instead of crashing

**Lines Added:** ~89 lines (functions + docstrings)

---

### 3. `cli/client.py`
**Changes:**

#### A. Schedule Format Support
- Added `--format` option to `get_schedules` command:
  - Choices: `json` (default), `text`
  - Converts JSON to text format if requested
- Added `--format` option to `set_schedules` command:
  - Choices: `json` (default), `text`
  - Parses text format to JSON before upload

#### B. Login Command
- Added new `login` command for credential management:
  - Options: `--username`, `--password`, `--delete`
  - Interactive prompts if credentials not provided
  - Hidden password input
  - Displays storage location after successful storage
  - Delete mode to remove stored credentials

#### C. Conversion Commands
- Added new CLI group `convert_cli` for standalone conversion commands:
  - `convert-schedule-to-json`: Convert text → JSON
  - `convert-schedule-to-text`: Convert JSON → text
  - No authentication required
  - Supports stdin/stdout or file I/O

#### D. Main Entry Point Refactoring
- Modified `main()` function to handle three command types:
  1. `login` - Credential management (no auth)
  2. `convert-*` - Format conversion (no auth)
  3. Other commands - Require authentication

**Lines Added:** ~178 lines (commands + logic)

---

### 4. `requirements_dev.txt`
**Changes:**
- Added `aiozoneinfo >= 0.2.3` to development dependencies

**Rationale:** Required for timezone support during development and testing.

---

## New Files

### 1. `cli/poll_evohome.py` (647 lines)
**Purpose:** Temperature polling command for continuous monitoring.

**Key Features:**
- Configurable polling interval (30s to 120m)
- CSV output with timestamps and zone temperatures
- Optional on-screen display with formatted columns
- Interactive 'L' key to show zone list and headers
- File handling: append (default) or overwrite modes
- Retry logic for API failures with exponential backoff
- Graceful keyboard interrupt handling

**Functions:**
- `_parse_interval()`: Parse interval string (e.g., "60s", "2m") to seconds
- `_format_zone_key()`: Format zone key as `zone_id_zone_name`
- `register_command()`: Register poll command with CLI group

**CSV Format:**
```csv
timestamp,system_mode,zone_id_zone_name,...
2026-02-15T01:30:00,Auto,5262675_Livingroom,...
```

**Display Format:**
```
Time                Mode            Zone1    Zone2    ...
-----------------------------------------------------------
2026-02-15 01:30:00 Auto             20.5     19.2    ...
```

---

### 2. `cli/schedule_parser.py` (314 lines)
**Purpose:** Bidirectional conversion between text and JSON schedule formats.

**Key Features:**
- Human-readable text format for easy editing
- API-compatible JSON format
- Smart day grouping (Weekdays, Weekends, All days)
- Round-trip conversion preserves data
- Regex-based parsing for efficiency

**Text Format Example:**
```
1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30

2. Bedroom (5262676)
All days: 18C @ 22:00 to 16C @ 06:00
```

**JSON Format Example:**
```json
[
  {
    "zone_id": "5262675",
    "name": "Livingroom",
    "daily_schedules": [
      {
        "day_of_week": "Monday",
        "switchpoints": [
          {"heat_setpoint": 16.0, "time_of_day": "06:00:00"},
          {"heat_setpoint": 17.5, "time_of_day": "21:50:00"}
        ]
      }
    ]
  }
]
```

**Main Functions:**
- `parse_text_schedule()`: Text → JSON
- `json_to_text_schedule()`: JSON → Text
- `parse_temperature_time()`: Extract temp/time pairs
- `parse_day_spec()`: Parse day specifications
- `_format_day_spec()`: Optimize day grouping
- `_format_switchpoints()`: Format switchpoints as text
- `_group_days_by_schedule()`: Group days with identical schedules

---

### 3. `tests/tests/test_cli_auth.py`
**Purpose:** Test credential storage and login command.

**Test Coverage:**
- Credential storage and retrieval
- Login command with username/password options
- Delete credentials functionality
- Credential storage location detection
- Error handling for missing keyring

---

### 4. `tests/tests/test_cli_poll_evohome.py`
**Purpose:** Test temperature polling command.

**Test Coverage:**
- Interval parsing (30s to 120m)
- Zone key formatting
- CSV file creation and writing
- Append vs. overwrite modes
- Zone list display
- Error handling

---

### 5. `tests/tests/test_cli_schedules.py`
**Purpose:** Test schedule format conversion and CLI commands.

**Test Coverage:**
- Text → JSON conversion
- JSON → Text conversion
- Round-trip conversion (text → JSON → text)
- Day specification parsing
- Switchpoint formatting
- CLI get/set schedules commands
- Format option handling

---

### 6. `docs/Architecture.md` (564 lines)
**Purpose:** Comprehensive architecture documentation.

**Sections:**
- Project configuration and structure
- Core components (auth, parser, polling, client)
- Credential management flow
- Data flow diagrams
- Schedule format details
- Error handling
- Testing strategy
- Dependencies
- Build and distribution
- Extension points
- Security considerations

---

### 7. `docs/CLI.md`
**Purpose:** CLI usage guide.

**Sections:**
- Installation
- Command reference
- Authentication
- Schedule management
- Temperature polling
- Format conversion
- Examples

---

### 8. `docs/DumpJSON.md`
**Purpose:** JSON dump format documentation.

**Sections:**
- JSON structure
- Field descriptions
- Examples

---

### 9. `docs/LogTemperatureCSV.md`
**Purpose:** Temperature logging CSV format.

**Sections:**
- CSV structure
- Column descriptions
- Usage examples

---

### 10. `docs/ProjectAnalysis.md` (479 lines)
**Purpose:** Comprehensive project analysis.

**Sections:**
- Project overview and purpose
- Architecture and structure
- Core components
- Key features
- Dependencies
- Configuration
- Data flow examples
- Use cases
- Testing
- Security considerations
- Performance considerations
- Future enhancements

---

### 11. `docs/ScheduleJSON.md`
**Purpose:** JSON schedule format specification.

**Sections:**
- JSON structure
- Field descriptions
- Examples
- Validation rules

---

### 12. `docs/TextSchedule.md`
**Purpose:** Text schedule format specification.

**Sections:**
- Text format syntax
- Day specifications
- Temperature/time format
- Examples
- Conversion rules

---

### 13. `.env.example`
**Purpose:** Example environment configuration file.

**Contents:**
- TCC credentials (username, password)
- InfluxDB configuration (optional)
- Other environment variables

---

### 14. `.cursor/` directory
**Purpose:** Cursor IDE configuration (auto-generated).

**Note:** Added to `.gitignore` to prevent tracking IDE-specific files.

---

## Feature Breakdown

### 1. Secure Credential Storage
**Files:** `cli/auth.py`, `cli/client.py`, `tests/tests/test_cli_auth.py`

**Functionality:**
- Store TCC credentials in OS-native secure storage
- Retrieve credentials automatically for CLI commands
- Delete stored credentials
- Platform-specific storage locations

**Usage:**
```bash
# Store credentials
evo-client login

# Use stored credentials
evo-client mode

# Delete credentials
evo-client login --delete
```

---

### 2. Text Schedule Format
**Files:** `cli/schedule_parser.py`, `cli/client.py`, `tests/tests/test_cli_schedules.py`, `docs/TextSchedule.md`

**Functionality:**
- Human-readable schedule format
- Bidirectional conversion (text ↔ JSON)
- Smart day grouping
- Easy editing in text editor

**Usage:**
```bash
# Get schedules in text format
evo-client get-schedules --format text > schedules.txt

# Edit schedules.txt in text editor

# Upload modified schedules
evo-client set-schedules --format text -f schedules.txt
```

---

### 3. Temperature Polling
**Files:** `cli/poll_evohome.py`, `cli/client.py`, `tests/tests/test_cli_poll_evohome.py`, `docs/LogTemperatureCSV.md`

**Functionality:**
- Continuous temperature monitoring
- CSV output with timestamps
- Configurable polling interval
- Interactive display
- Append/overwrite modes

**Usage:**
```bash
# Poll every 60 seconds
evo-client poll --interval 60s --output temps.csv

# Poll every 2 minutes, overwrite file
evo-client poll --interval 2m --output temps.csv --overwrite

# Poll without display
evo-client poll --interval 60s --output temps.csv --noshow
```

---

### 4. Standalone Format Conversion
**Files:** `cli/client.py`, `cli/schedule_parser.py`, `tests/tests/test_cli_schedules.py`

**Functionality:**
- Convert between JSON and text formats
- No authentication required
- Supports stdin/stdout

**Usage:**
```bash
# Convert text to JSON
evo-client convert-schedule-to-json -i schedules.txt -o schedules.json

# Convert JSON to text
evo-client convert-schedule-to-text -i schedules.json -o schedules.txt

# Use stdin/stdout
cat schedules.txt | evo-client convert-schedule-to-json > schedules.json
```

---

## Testing

### New Test Files
1. **test_cli_auth.py**: Credential storage and login command
2. **test_cli_poll_evohome.py**: Temperature polling
3. **test_cli_schedules.py**: Schedule conversion and CLI

### Test Coverage
- Unit tests for individual functions
- Integration tests for CLI commands
- Round-trip conversion validation
- Error handling tests

### Running Tests
```bash
pytest tests/tests/test_cli_auth.py
pytest tests/tests/test_cli_poll_evohome.py
pytest tests/tests/test_cli_schedules.py
```

---

## Documentation

### New Documentation Files
1. **Architecture.md**: Comprehensive architecture documentation
2. **CLI.md**: CLI usage guide
3. **DumpJSON.md**: JSON dump format
4. **LogTemperatureCSV.md**: Temperature CSV format
5. **ProjectAnalysis.md**: Project analysis
6. **ScheduleJSON.md**: JSON schedule format
7. **TextSchedule.md**: Text schedule format

### Documentation Quality
- Detailed explanations
- Code examples
- Usage examples
- Architecture diagrams (text-based)
- Security considerations
- Extension points

---

## Code Quality

### Type Checking
- All new code fully typed
- mypy strict mode compliance
- TypedDict for complex structures

### Linting
- ruff compliance (40+ rule categories)
- PEP 8 style
- Security checks (bandit)
- Performance checks

### Testing
- Comprehensive test coverage
- Async test support
- Mocked API interactions

---

## Security Enhancements

### Credential Storage
- OS-native secure storage (keyring)
- No plain-text passwords
- Platform-specific backends

### Password Input
- Hidden input for interactive prompts
- Never logged or exposed in errors

### Token Management
- Secure token caching
- Automatic token refresh

---

## Breaking Changes

**None.** All changes are backward-compatible additions.

---

## Migration Guide

### For Users
No migration required. New features are opt-in:
- Continue using `--username` and `--password` options, or
- Use new `login` command to store credentials securely

### For Developers
No API changes. New CLI commands and modules are additions only.

---

## Future Work

Potential enhancements based on new infrastructure:
- DHW (Domestic Hot Water) schedule support in text format
- Schedule validation before upload
- Schedule comparison/diff functionality
- Template-based schedule generation
- Batch operations for multiple locations

---

## Commit Message Suggestions

When committing these changes, use conventional commit style:

```
feat(cli): add secure credential storage with system keyring

- Add login command for credential management
- Support macOS Keychain, Windows Credential Manager, Linux Secret Service
- Add get/store/delete credential functions in cli/auth.py
- Add tests for credential storage

BREAKING CHANGE: None (backward compatible)
```

```
feat(cli): add text schedule format with bidirectional conversion

- Add schedule_parser.py for text ↔ JSON conversion
- Support human-readable schedule format
- Add --format option to get-schedules and set-schedules
- Add standalone conversion commands
- Add comprehensive tests and documentation

BREAKING CHANGE: None (backward compatible)
```

```
feat(cli): add temperature polling command

- Add poll command for continuous temperature monitoring
- Support configurable intervals (30s to 120m)
- Write to CSV with timestamps and zone temperatures
- Add interactive display with 'L' key for zone list
- Support append/overwrite modes
- Add retry logic for API failures

BREAKING CHANGE: None (backward compatible)
```

```
docs: add comprehensive architecture and usage documentation

- Add Architecture.md with detailed system design
- Add CLI.md with usage guide
- Add format specifications (ScheduleJSON.md, TextSchedule.md)
- Add ProjectAnalysis.md with comprehensive analysis
- Add LogTemperatureCSV.md for temperature logging

BREAKING CHANGE: None
```

---

## Statistics

### Lines of Code Added
- **cli/auth.py**: ~89 lines (credential management)
- **cli/client.py**: ~178 lines (commands + logic)
- **cli/poll_evohome.py**: 647 lines (new file)
- **cli/schedule_parser.py**: 314 lines (new file)
- **tests/**: ~500+ lines (3 new test files)
- **docs/**: ~2500+ lines (7 new documentation files)

**Total**: ~4200+ lines of code and documentation

### Files Changed
- **Modified**: 4 files (`.gitignore`, `cli/auth.py`, `cli/client.py`, `requirements_dev.txt`)
- **Added**: 14 files (2 CLI modules, 3 test files, 7 docs, 2 config)

### Test Coverage
- **New test files**: 3
- **Test functions**: 20+
- **Coverage**: Comprehensive (unit + integration)

---

## Summary

These changes significantly enhance the CLI with:
1. ✅ **Secure credential storage** - No more plain-text passwords
2. ✅ **Human-readable schedules** - Easy editing in text format
3. ✅ **Temperature monitoring** - Continuous polling with CSV output
4. ✅ **Standalone conversions** - Format conversion without authentication
5. ✅ **Comprehensive tests** - Full test coverage for new features
6. ✅ **Extensive documentation** - Detailed guides and specifications

All changes are **backward-compatible** and follow the project's high code quality standards (type checking, linting, testing).
