# Evohome Async CLI Architecture

This document describes the architecture of the evohome-async CLI utility, including the schedule format conversion functionality.

## Overview

The CLI utility (`evo-client`) provides a command-line interface for interacting with the Honeywell TCC (Total Connect Comfort) API. It supports two schedule formats:
- **JSON format**: Structured format used by the TCC API
- **Text format**: Human-readable format for easier editing

## Project Configuration

The project is configured using `pyproject.toml` following PEP 518/621 standards.

### Project Metadata
- **Name**: `evohome-async`
- **Version**: Dynamic (read from `src/evohome/__init__.py`)
- **Python Requirement**: `>=3.12`
- **License**: Apache-2.0
- **Build System**: Hatchling

### Entry Point
The CLI is installed as `evo-client` via the entry point:
```toml
[project.scripts]
evo-client = "cli.client:main"
```

### Package Structure
The project uses a `src` layout with packages organized as:
- `src/evohomeasync`: Legacy v0 API client
- `src/evohomeasync2`: Current v2 API client (primary)
- `src/evohome`: Shared utilities and version information
- `cli/`: CLI utilities (not part of core library)

Packages are built into wheels via Hatchling, with sources configured in `src/`.

## Directory Structure

```
evohome-async/
├── cli/
│   ├── __init__.py
│   ├── auth.py              # Authentication and token management
│   ├── client.py            # Main CLI commands
│   ├── poll_evohome.py      # Temperature polling command
│   ├── schedule_parser.py   # Schedule format conversion
│   └── py.typed
├── src/
│   └── evohomeasync2/       # Core library
├── scripts/                 # Remaining utility scripts
├── tests/                   # Test suite
└── docs/                    # Documentation
```

> **Note**: Energy meter polling, weather data collection, and InfluxDB utilities have been moved to the `../monitor/` folder. See the [monitor documentation](../../monitor/README.md) for details.


## Core Components

### 1. Authentication Module (`cli/auth.py`)

**Purpose**: Manages authentication tokens, session IDs, and user credentials for the TCC API.

**Key Components**:
- `CredentialsManager`: Handles access tokens, refresh tokens, and session IDs
- Token caching to disk to avoid unnecessary re-authentication
- Automatic token refresh when expired
- Secure credential storage using system keyring

**Responsibilities**:
- Authenticate with TCC API
- Cache tokens to file system
- Refresh expired tokens automatically
- Manage session lifecycle
- Store and retrieve user credentials securely

**Credential Storage Functions**:
- `get_stored_credentials()`: Retrieves username and password from secure storage
- `store_credentials()`: Stores credentials in system keyring
- `delete_stored_credentials()`: Removes stored credentials
- `get_credential_storage_location()`: Returns platform-specific storage location description

**Storage Backend**:
Uses the `keyring` library for cross-platform secure storage:
- **macOS**: Keychain Access (System Keychain)
- **Windows**: Windows Credential Manager
- **Linux**: Secret Service (GNOME Keyring, KWallet, etc.)

**Security**:
- Credentials are stored in the operating system's native secure credential store
- No credentials are stored in plain text files
- Graceful fallback if keyring is not available (requires command-line credentials)

### 2. Schedule Parser Module (`cli/schedule_parser.py`)

**Purpose**: Converts between text and JSON schedule formats.

**Key Functions**:

#### `parse_text_schedule(text: str) -> list[dict]`
Converts human-readable text format to JSON structure.

**Input Format**:
```
1. Zone Name (zone_id)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30
```

**Output Format**: JSON array of schedule objects with `zone_id`, `name`, and `daily_schedules`.

**Processing Steps**:
1. Parse zone headers (number, name, ID)
2. Parse schedule lines (day specifications and switchpoints)
3. Expand day specifications (Weekdays → Monday-Friday, etc.)
4. Convert temperature/time pairs to switchpoint objects
5. Sort daily schedules by day of week

#### `json_to_text_schedule(schedules: list[dict]) -> str`
Converts JSON structure to human-readable text format.

**Processing Steps**:
1. Group daily schedules by switchpoint patterns
2. Determine optimal day specification format:
   - "All days" if all 7 days have same schedule
   - "Weekdays" if all weekdays have same schedule
   - "Weekends" if all weekends have same schedule
   - "Mon/Tue/Thu/Fri" for specific day combinations
   - Individual day names when needed
3. Format switchpoints as "temperatureC @ HH:MM" pairs
4. Generate zone headers with sequential numbering

**Helper Functions**:
- `parse_temperature_time()`: Extracts temperature and time pairs from text
- `parse_day_spec()`: Converts day specifications to list of day names
- `_format_day_spec()`: Optimizes day specification format
- `_format_switchpoints()`: Formats switchpoints as text
- `_group_days_by_schedule()`: Groups days with identical schedules

### 3. Temperature Polling Module (`cli/poll_evohome.py`)

**Purpose**: Provides the `poll` command for continuously polling zone temperatures.

**Key Features**:
- Runs dump command repeatedly at configurable intervals (30s to 120m)
- Writes temperature data to CSV file with timestamps
- Optional on-screen display with fixed-width columns
- Interactive 'L' key to show zone list and headers
- File existence handling: defaults to append, can override with `--overwrite`

**Processing Steps**:
1. Parse interval string (e.g., "60s", "2m") to seconds
2. Get zone list from TCS
3. Check if CSV file exists:
   - If exists: Default behavior is to append (skip header writing)
   - If `--overwrite` specified: Overwrite file (write header)
   - If `--append` specified: Explicitly append (same as default)
4. Create CSV file with headers: `timestamp`, `system_mode`, `{zone_id}_{zone_name}` (only if new file or overwriting)
5. Start keyboard input thread for 'L' key handling
6. Loop:
   - Update location status (calls dump internally)
   - Get system mode from TCS
   - Extract temperatures from zones
   - Write row to CSV file (includes timestamp, system_mode, and zone temperatures)
   - Display on screen (if not `--noshow`) with time, mode, and temperatures
   - Check for 'L' key press every 100ms (show zone list and header immediately)
   - Wait for interval duration (broken into 100ms chunks for responsiveness)
7. Handle KeyboardInterrupt gracefully

**Helper Functions**:
- `_parse_interval()`: Parses interval string (30s-120m) to seconds
- `_format_zone_key()`: Formats zone key as `zone_id_zone_name` (spaces to underscores)
- `register_command()`: Registers the command with the CLI group (avoids circular imports)

**Module Structure**:
- Functions are defined at module level for testability
- Command registration happens via `register_command()` function
- Imports from `client.py` are done inside `register_command()` to avoid circular dependencies

### 4. CLI Client Module (`cli/client.py`)

**Purpose**: Main entry point for CLI commands.

**Command Registration**:
- Commands are defined in this module or registered from separate modules
- The `poll` command is registered from `cli/poll_evohome.py` via `register_poll(cli)`
- This modular approach improves code organization and maintainability

**Command Groups**:

#### Main CLI Group (Requires Authentication)
Commands in this group require credentials, which can be provided via:
- Command-line options: `--username` / `-u` and `--password` / `-p`
- Stored credentials: Automatically loaded from secure storage if available

**Commands**:
- `mode`: Retrieve system mode
- `dump`: Download config and status
- `poll`: Continuously poll zone temperatures at regular intervals (registered from `cli/poll_evohome.py`)
- `get_schedule`: Download single zone schedule
- `get_schedules`: Download all schedules (supports `--format json|text`)
- `set_schedules`: Upload schedules (supports `--format json|text`)

**Credential Resolution**:
1. Check command-line options (`--username`, `--password`)
2. If missing, attempt to load from secure storage
3. If still missing, raise error with helpful message directing user to `login` command

#### Login Command (No Authentication Required)
Standalone command for credential management.

**Commands**:
- `login`: Store credentials securely
  - Options:
    - `--username` / `-u`: TCC account username (prompts if not provided)
    - `--password` / `-p`: TCC account password (prompts if not provided, hidden input)
    - `--delete` / `-d`: Delete stored credentials (flag)
  - Usage examples:
    - `evo-client login` - Interactive mode (prompts for credentials)
    - `evo-client login -u username -p password` - Non-interactive mode
    - `evo-client login --delete` - Remove stored credentials

#### Conversion CLI Group (No Authentication Required)
Standalone file format conversion commands.

**Commands**:
- `convert-schedule-to-json`: Convert text format to JSON
- `convert-schedule-to-text`: Convert JSON format to text

**Command Flow**:

```
main()
├── Check if standalone command (login, convert-*)
│   ├── login → login() (no auth, stores credentials)
│   │   ├── Parse -u/-p options via click
│   │   ├── Prompt for missing credentials
│   │   └── Store in secure keyring
│   ├── convert-* → convert_cli() (no auth)
│   └── Other → cli() (requires auth)
│       ├── Resolve credentials
│       │   ├── From command line (-u/-p)?
│       │   ├── From secure storage?
│       │   └── Error if neither available
│       ├── Authenticate
│       ├── Execute command
│       │   ├── mode, dump, get_schedule, get_schedules, set_schedules
│       │   └── poll → Continuous loop
│       │       ├── Parse interval (30s-120m)
│       │       ├── Get zones from TCS
│       │       ├── Create CSV file with headers
│       │       ├── Start keyboard thread (for 'L' key)
│       │       └── Loop: update → extract temps → write CSV → display → wait
│       └── Cleanup
```

## Credential Management Flow

### Storing Credentials
```
User runs: evo-client login [-u username] [-p password]
├── Check for command-line options (-u, -p)
├── If username missing → Prompt for username
├── If password missing → Prompt for password (hidden input)
├── Store in system keyring
│   ├── macOS: Keychain Access
│   ├── Windows: Credential Manager
│   └── Linux: Secret Service
└── Display storage location to user
```

### Using Stored Credentials
```
User runs: evo-client <command>
├── Check for --username/--password options
├── If missing, load from keyring
├── If still missing, show error with login instructions
└── Use credentials for authentication
```

### Credential Priority
1. **Command-line options** (`--username`, `--password`) - highest priority
2. **Stored credentials** (from keyring) - fallback
3. **Error** - if neither available

## Data Flow

### Getting Schedules (JSON Format)
```
TCC API → get_schedules() → JSON → Output File
```

### Getting Schedules (Text Format)
```
TCC API → get_schedules() → JSON → json_to_text_schedule() → Text → Output File
```

### Setting Schedules (JSON Format)
```
Input File → JSON → set_schedules() → TCC API
```

### Setting Schedules (Text Format)
```
Input File → Text → parse_text_schedule() → JSON → set_schedules() → TCC API
```

### Conversion Commands
```
Text File → parse_text_schedule() → JSON → Output File
JSON File → json_to_text_schedule() → Text → Output File
```

## Schedule Format Details

### JSON Format Structure

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
      }
    ]
  }
]
```

### Text Format Structure

```
1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30
```

**Day Specifications**:
- `Weekdays`: Monday through Friday
- `Weekends`: Saturday and Sunday
- `All days`: All seven days
- `Mon/Tue/Thu/Fri`: Specific day combinations
- `Wednesday`: Individual days

## Error Handling

### Parser Errors
- Invalid zone header format
- Malformed schedule lines
- Invalid temperature or time formats
- Missing required fields

### CLI Errors
- Authentication failures
- Network errors
- File I/O errors
- Invalid command arguments

## Testing Strategy

Tests are organized in the `tests/` directory:

- **Unit Tests**: Test individual parser functions and credential storage
- **Integration Tests**: Test CLI commands with mocked API
- **Format Conversion Tests**: Verify round-trip conversion (text → JSON → text)
- **Credential Storage Tests**: Test secure credential storage and retrieval

**Test Files**:
- `tests/tests/test_cli_schedules.py`: Schedule format conversion and CLI schedule commands
- `tests/tests/test_cli_auth.py`: Credential storage, login command (including -u/-p options), and authentication flow
- `tests/tests/test_cli_poll_evohome.py`: Temperature polling command (interval parsing, CSV writing, zone formatting)
- `tests/tests/test_v2_auth.py`: Core authentication token management
- `tests/tests/test_v2_apis.py`: API interaction tests

### Test Configuration (pytest)

Configured in `pyproject.toml`:
- **Async Mode**: `auto` (automatic async test detection)
- **Fixture Loop Scope**: `function` (new event loop per test)
- **Excluded Directories**: `tests.out/*`, `tests.wip/*`

### Type Checking (mypy)

The project uses strict type checking with mypy:
- **Python Version**: 3.12
- **Strict Options Enabled**:
  - `no_implicit_optional`: Require explicit Optional types
  - `check_untyped_defs`: Check untyped function definitions
  - `disallow_untyped_calls`: Require type annotations for all calls
  - `disallow_incomplete_defs`: Require complete type annotations
  - `strict_equality`: Strict type checking for equality comparisons
  - `warn_return_any`: Warn about returning Any types
- **Excluded**: `docs/`, `tests/tests_cc/`

### Code Quality (ruff)

Comprehensive linting with ruff:
- **Target Version**: Python 3.13 (for future compatibility)
- **Enabled Checks**: 40+ rule categories including:
  - Style (E, W): PEP 8 compliance
  - Bug detection (B, BLE): Common errors and blind excepts
  - Complexity (C90): McCabe complexity
  - Security (S): Bandit security checks
  - Performance (PERF): Performance anti-patterns
  - Type checking (TC): Type checking imports
  - Async (ASYNC): Async/await best practices
- **Per-file Ignores**: CLI files allow prints, test files allow assertions

### Code Coverage

Coverage configuration:
- **Omitted**: `cli/*`, `tests*/*` (CLI and tests excluded from coverage)
- **Show Missing**: Enabled (shows lines not covered)

## Dependencies

### Runtime Dependencies
Defined in `pyproject.toml`:
- `aiohttp>=3.11.12`: Async HTTP client for API communication
- `aiozoneinfo>=0.2.3`: Async timezone support
- `voluptuous>=0.15.2`: Schema validation

### Optional Runtime Dependencies
- `keyring`: Secure credential storage (required for `login` command)
  - Automatically uses system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
  - If not installed, `login` command will fail with helpful error message
  - Other commands can still use `--username` and `--password` options

### Development Dependencies
- `asyncclick`: Async CLI framework (for CLI commands)
- `aiofiles`: Async file operations (for CLI file handling)
- `pytest`: Testing framework
- `mypy`: Static type checking
- `ruff`: Fast Python linter and formatter
- `hatchling`: Build backend

### Internal Modules
- `evohomeasync2`: Core library for TCC API interaction (v2 API)
- `evohomeasync`: Legacy v0 API client
- `evohome`: Shared utilities and version information
- `cli.auth`: Authentication management
- `cli.schedule_parser`: Schedule format conversion

## Build and Distribution

### Build System
The project uses **Hatchling** as the build backend:
- **Sources**: Located in `src/` directory
- **Packages**: `src/evohomeasync`, `src/evohomeasync2`, `src/evohome`
- **Version**: Read dynamically from `src/evohome/__init__.py`

### Installation
```bash
# Development installation
pip install -e .

# Production installation
pip install evohome-async
```

### Distribution
The package can be distributed as:
- **Wheel** (`.whl`): Built via Hatchling
- **Source Distribution** (`.tar.gz`): For compatibility

## Extension Points

### Adding New Schedule Formats
1. Add parser function to `schedule_parser.py`
2. Add conversion function (bidirectional)
3. Add format option to CLI commands
4. Add tests in `tests/tests/test_cli_schedules.py`
5. Update documentation (`docs/ScheduleJSON.md`, `docs/TextSchedule.md`)

### Adding New CLI Commands

Commands can be added in two ways:

**Option 1: Add to `client.py`** (for simple commands)
1. Add command function to `client.py`
2. Decorate with `@cli.command()`, `@convert_cli.command()`, or `@click.command()` for standalone commands
3. Add tests in `tests/tests/`
4. Update `docs/CLI.md`
5. Ensure type annotations for mypy compliance
6. Run ruff linter to ensure code quality
7. If command requires auth, ensure it works with both stored and command-line credentials

**Option 2: Create separate module** (for complex commands, like `poll`)
1. Create new file in `cli/` directory (e.g., `cli/newcommand.py`)
2. Define helper functions at module level (for testability)
3. Create `register_command(cli_group)` function that:
   - Imports dependencies from `client.py` inside the function (to avoid circular imports)
   - Defines and decorates the command with `@cli_group.command()`
4. In `client.py`, import and call the register function: `register_newcommand(cli)`
5. Add tests in `tests/tests/` (import functions from the new module)
6. Update `docs/CLI.md` and `docs/Architecture.md`
7. Ensure type annotations for mypy compliance
8. Run ruff linter to ensure code quality
9. If command requires auth, ensure it works with both stored and command-line credentials

## Performance Considerations

- **Token Caching**: Reduces authentication overhead
- **Async Operations**: Non-blocking I/O for API calls
- **Parser Efficiency**: Regex-based parsing for text format
- **Memory Usage**: Stream processing for large schedule files

## Security Considerations

- **Credentials**: Never logged or exposed in error messages
- **Credential Storage**: User credentials stored in OS secure credential store (keyring)
  - Not stored in plain text files
  - Protected by OS-level security (Keychain, Credential Manager, etc.)
  - Requires user authentication to access (OS-level)
- **Token Storage**: Cached tokens stored securely on disk
- **Input Validation**: All user inputs validated before processing
- **File Permissions**: Cache file permissions restricted
- **Password Input**: Passwords are never echoed when entered interactively

## Development Workflow

### Code Quality Checks
Before committing, ensure:
1. **Type Checking**: `mypy cli src tests`
2. **Linting**: `ruff check cli src tests`
3. **Tests**: `pytest tests/`
4. **Coverage**: `pytest --cov=src --cov-report=html`

### Project Standards
- **Python Version**: 3.12+ required
- **Type Annotations**: Required for all functions (mypy strict mode)
- **Code Style**: PEP 8 compliant (enforced by ruff)
- **Async/Await**: Use async/await for all I/O operations
- **Error Handling**: Proper exception handling with typed exceptions

### Version Management
- Version is stored in `src/evohome/__init__.py`
- Hatchling reads version dynamically during build
- Follow semantic versioning (MAJOR.MINOR.PATCH)

## Future Enhancements

Potential improvements:
- Support for DHW (Domestic Hot Water) schedules in text format
- Schedule validation before upload
- Schedule comparison/diff functionality
- Template-based schedule generation
- Batch operations for multiple locations
- Python 3.13+ specific optimizations (target version already set)

