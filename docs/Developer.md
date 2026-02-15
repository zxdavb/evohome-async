# evohome-async Project Analysis

## Overview

**evohome-async** is a Python async client library for accessing Honeywell's Total Connect Comfort (TCC) RESTful API. It provides support for Resideo TCC-based systems including Evohome, Round Thermostat, VisionPro, and other EU/EMEA-based heating control systems.

**Current Version**: 1.0.5  
**License**: Apache-2.0  
**Python Requirement**: ≥3.12

## Project Purpose

The library enables:
- Asynchronous communication with Honeywell TCC API
- Home automation integration (notably Home Assistant)
- Schedule backup/restore functionality
- Temperature and energy monitoring
- Integration with time-series databases (InfluxDB)

> **Note**: The TCC API does not currently support cooling systems. For US-based systems, use alternatives like [somecomfort](https://github.com/mkmer/AIOSomecomfort).

## Architecture

### Package Structure

The project uses a `src` layout with three main packages:

```
evohome-async/
├── src/
│   ├── evohome/           # Shared utilities and version info
│   ├── evohomeasync/      # Legacy v0 API client
│   └── evohomeasync2/     # Current v2 API client (primary)
├── cli/                   # CLI utilities (not part of core library)
├── scripts/               # Remaining utility scripts
├── docs/                  # Documentation
└── tests/                 # Test suite

../monitor/                # Monitoring suite (separate folder)
├── scripts/               # Monitoring and data collection scripts
├── data/                  # Data storage (CSV files)
├── docs/                  # Monitoring documentation
└── setup/                 # InfluxDB setup scripts
```

> **Note**: Monitoring components (energy meter polling, weather data collection, InfluxDB utilities) have been reorganized into a separate `monitor` folder at the workspace root. See [monitor/README.md](../../monitor/README.md) for details.


### Core Components

#### 1. **evohome** (Shared Utilities)
Located in `src/evohome/`, provides:
- **Version management** (`__init__.py`)
- **Authentication** (`auth.py`) - Token management and credentials
- **Constants** (`const.py`) - API endpoints and configuration
- **Credentials management** (`credentials.py`)
- **Exception handling** (`exceptions.py`)
- **Helper utilities** (`helpers.py`)
- **Timezone handling** (`time_zone.py`, `windows_zones.py`)

#### 2. **evohomeasync2** (Primary v2 API Client)
Located in `src/evohomeasync2/`, the main library:
- **EvohomeClient** (`main.py`) - Main client class for API interaction
- **Authentication** (`auth.py`) - Token manager for v2 API
- **Entity models** (`control_system.py`, `gateway.py`, `hotwater.py`, `location.py`, `zone.py`)
- **Schema validation** (`schemas/`) - TypedDicts and validation schemas
- **Constants** (`const.py`)

Key class: `EvohomeClient`
- Manages user account and location information
- Provides async methods for updating system state
- Handles timezone initialization
- Exposes locations, control systems, and zones

#### 3. **evohomeasync** (Legacy v0 API)
Located in `src/evohomeasync/`, maintained for backward compatibility:
- Legacy authentication and entity models
- Simpler schema structure
- Deprecated in favor of evohomeasync2

### CLI Architecture

The CLI (`cli/`) provides a command-line interface with several components:

#### **client.py** - Main CLI Entry Point
Provides commands:
- `mode` - Retrieve system mode
- `dump` - Download config and status
- `poll` - Continuously poll zone temperatures
- `get-schedule` / `get-schedules` - Download schedules
- `set-schedules` - Upload schedules
- `login` - Store credentials securely
- `convert-schedule-to-json` / `convert-schedule-to-text` - Format conversion

Entry point: `evo-client` (installed via `pyproject.toml`)

#### **auth.py** - Credential Management
- `CredentialsManager` - Handles tokens and session IDs
- Secure credential storage using system keyring:
  - **macOS**: Keychain Access
  - **Windows**: Credential Manager
  - **Linux**: Secret Service (GNOME Keyring, KWallet)
- Token caching to avoid re-authentication
- Automatic token refresh

#### **schedule_parser.py** - Schedule Format Conversion
Converts between two formats:

**Text Format** (human-readable):
```
1. Livingroom (5262675)
Weekdays: 16C @ 06:00 to 17.5C @ 21:50
Weekends: 15C @ 07:00 to 15C @ 22:30
```

**JSON Format** (API-compatible):
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

Key functions:
- `parse_text_schedule()` - Text → JSON
- `json_to_text_schedule()` - JSON → Text
- Smart day grouping (Weekdays, Weekends, All days)

#### **poll_evohome.py** - Temperature Polling
- Continuous temperature monitoring at configurable intervals (30s to 120m)
- CSV output with timestamps and zone temperatures
- Interactive display with 'L' key for zone list
- Append/overwrite modes for CSV files

### Monitoring Components

> **Note**: The following monitoring components have been moved to the `../monitor/` folder. See [monitor documentation](../../monitor/README.md) for complete details.

**Energy Monitoring** (`monitor/scripts/poll_energymeter.py`):
- Polls P1 Energy Meter API for energy data
- Writes to CSV and optionally to InfluxDB
- Supports data import from CSV to InfluxDB
- Configurable polling intervals (10s to 120m)
- Interactive table display with keyboard controls

**Weather Data Collection** (`monitor/scripts/poll_openweathermap.py`):
- Fetches weather data from OpenWeatherMap API
- Logs to CSV and InfluxDB
- Correlates weather with heating data

**Data Import** (`monitor/scripts/import_temperature_csv.py`):
- Imports historical temperature data from CSV to InfluxDB
- Handles timezone conversion
- Validates data before import

**InfluxDB Utilities** (`monitor/scripts/`):
- `test_influxdb_connection.py` - Connection testing
- `test_line_protocol.py` - Line protocol validation
- `check_influxdb_schema.py` - Schema verification


## Key Features

### 1. **Asynchronous Design**
- Built on `aiohttp` for non-blocking I/O
- Async/await throughout the codebase
- Efficient for multiple concurrent API calls

### 2. **Authentication & Security**
- Token-based authentication with automatic refresh
- Secure credential storage via OS keyring
- Token caching to minimize API calls
- No plain-text credential storage

### 3. **Schedule Management**
- Backup/restore zone schedules
- Human-readable text format for easy editing
- JSON format for API compatibility
- Bidirectional conversion with validation

### 4. **Data Monitoring & Logging**
- Temperature polling with CSV output
- Energy meter integration
- Weather data correlation
- InfluxDB integration for time-series data

### 5. **Type Safety**
- Fully typed with TypedDicts
- `py.typed` marker for type checkers
- Strict mypy configuration
- Type annotations for all functions

### 6. **Code Quality**
- Comprehensive linting with ruff (40+ rule categories)
- Strict type checking with mypy
- Extensive test suite with pytest
- Pre-commit hooks for quality checks

## Dependencies

### Runtime Dependencies
- `aiohttp>=3.11.12` - Async HTTP client
- `aiozoneinfo>=0.2.3` - Async timezone support
- `voluptuous>=0.15.2` - Schema validation

### CLI Dependencies (Optional)
- `asyncclick` - Async CLI framework
- `aiofiles` - Async file operations
- `keyring` - Secure credential storage

### Development Dependencies
- `pytest` - Testing framework
- `mypy` - Static type checking
- `ruff` - Fast Python linter
- `hatchling` - Build backend

### Optional Integrations
- `influxdb3-python` - InfluxDB v3 client
- `python-dotenv` - Environment variable management

## Configuration

### Build System (pyproject.toml)
- **Build Backend**: Hatchling
- **Version**: Dynamic from `src/evohome/__init__.py`
- **Entry Point**: `evo-client = cli.client:main`
- **Packages**: `evohomeasync`, `evohomeasync2`, `evohome`

### Testing (pytest)
- **Async Mode**: Auto-detection
- **Fixture Scope**: Function-level event loops
- **Excluded**: `tests.out/*`, `tests.wip/*`

### Type Checking (mypy)
Strict configuration with:
- `check_untyped_defs` - Check all function definitions
- `disallow_untyped_calls` - Require type annotations
- `disallow_any_generics` - No bare generics
- `warn_return_any` - Warn on Any returns
- `strict_equality` - Strict type equality checks

### Linting (ruff)
Enabled checks include:
- **Style**: E, W (PEP 8)
- **Bugs**: B, BLE (bugbear, blind-except)
- **Security**: S (bandit)
- **Performance**: PERF (performance anti-patterns)
- **Async**: ASYNC (async/await best practices)
- **Type Checking**: TC (type checking imports)
- **Complexity**: C90 (McCabe complexity)

## Data Flow Examples

### Getting Schedules
```
User → CLI → EvohomeClient → TCC API
                ↓
         JSON Response
                ↓
    (Optional) Text Conversion
                ↓
          Output File
```

### Temperature Polling
```
User → CLI → EvohomeClient → TCC API (periodic)
                ↓
         Zone Temperatures
                ↓
         CSV File + Display
```

### Energy Monitoring
```
P1 Meter API → poll_energymeter.py → CSV File
                        ↓
                   InfluxDB (optional)
```

## Use Cases

### 1. **Home Automation Integration**
Primary use case for Home Assistant and similar platforms:
- Real-time temperature monitoring
- Schedule management
- System mode control
- Zone-level control

### 2. **Data Analysis**
Historical data collection and analysis:
- Temperature trends over time
- Energy consumption patterns
- Weather correlation
- InfluxDB integration for visualization (Grafana)

### 3. **Schedule Management**
Backup and restore heating schedules:
- Seasonal schedule changes
- Bulk zone configuration
- Human-readable editing
- Version control for schedules

### 4. **System Monitoring**
Continuous monitoring and alerting:
- Temperature anomalies
- System faults
- Energy usage tracking
- Multi-location support

## Differences from Non-Async Version

Key improvements over [evohome-client](https://github.com/watchforstock/evohome-client):

1. **Async/Await** - Non-blocking I/O throughout
2. **Simplified Namespace** - `snake_case` attrs, `.id` instead of `.zoneId`
3. **TZ-Aware Datetimes** - All datetimes are timezone-aware
4. **Modern Authentication** - `TokenManager` and `Auth` classes
5. **Better Error Handling** - Parochial exceptions (e.g., `AuthenticationFailedError`)
6. **Enhanced Logging** - Better error messages and fault warnings
7. **Full Typing** - TypedDicts and `py.typed` marker
8. **Modern Tooling** - ruff/mypy instead of older tools
9. **Extensive Testing** - Comprehensive pytest suite
10. **Extended Compatibility** - Beyond pure Evohome (VisionPro, etc.)

## Documentation

Located in `docs/`:
- **Architecture.md** - Detailed architecture documentation
- **CLI.md** - CLI usage guide
- **DumpJSON.md** - JSON dump format
- **ScheduleJSON.md** - Schedule JSON format
- **TextSchedule.md** - Text schedule format
- **LogTemperatureCSV.md** - Temperature logging
- **ProjectAnalysis.md** - Comprehensive project analysis

Monitoring documentation (in `../monitor/docs/`):
- **Architecture.md** - Monitoring system architecture
- **UserGuide.md** - Complete monitoring user guide
- **PollEnergyMeter.md** - Energy meter polling details
- **PollWeather.md** - Weather data collection guide
- **OpenWeatherMapJSON.md** - Weather API format reference
- **ImportTemperatureCSV.md** - CSV import guide


## Testing

Comprehensive test suite in `tests/`:
- **Unit Tests** - Individual function testing
- **Integration Tests** - CLI commands with mocked API
- **Format Conversion Tests** - Round-trip conversion validation
- **Credential Storage Tests** - Secure storage verification
- **API Tests** - v2 API interaction tests

Test files:
- `test_cli_schedules.py` - Schedule conversion and CLI
- `test_cli_auth.py` - Credential storage and login
- `test_cli_poll_evohome.py` - Temperature polling
- `test_v2_auth.py` - Core authentication
- `test_v2_apis.py` - API interactions

## Security Considerations

1. **Credential Storage**
   - OS-native secure storage (keyring)
   - No plain-text passwords
   - OS-level authentication required

2. **Token Management**
   - Cached tokens with restricted permissions
   - Automatic token refresh
   - Secure token storage

3. **Input Validation**
   - All user inputs validated
   - Schema validation with voluptuous
   - Type checking with mypy

4. **Password Handling**
   - Hidden input for interactive prompts
   - Never logged or exposed in errors
   - Secure transmission via HTTPS

## Performance Considerations

- **Token Caching** - Reduces authentication overhead
- **Async Operations** - Non-blocking I/O for API calls
- **Efficient Parsing** - Regex-based schedule parsing
- **Stream Processing** - Memory-efficient for large files
- **Connection Pooling** - aiohttp session reuse

## Future Enhancements

Potential improvements mentioned in documentation:
- DHW (Domestic Hot Water) schedule support in text format
- Schedule validation before upload
- Schedule comparison/diff functionality
- Template-based schedule generation
- Batch operations for multiple locations
- Python 3.13+ optimizations

## Summary

**evohome-async** is a well-architected, production-ready Python library for Honeywell TCC API integration. It demonstrates:

✅ **Modern Python Practices** - Async/await, type hints, strict linting  
✅ **Security** - Secure credential storage, token management  
✅ **Usability** - CLI tools, format conversion, human-readable schedules  
✅ **Extensibility** - Modular design, clear extension points  
✅ **Quality** - Comprehensive testing, type checking, documentation  
✅ **Integration** - InfluxDB support, Home Assistant compatibility  

The project is actively maintained with recent updates (v1.0.5) and follows best practices for open-source Python projects. It's suitable for both library integration and standalone CLI usage.

## Quick Start

### Installation
```bash
pip install evohome-async
```

### Basic Usage (Library)
```python
import aiohttp
from evohomeasync2 import EvohomeClient
from evohome.auth import TokenManager

websession = aiohttp.ClientSession()
token_manager = TokenManager(username, password, websession)
await token_manager.load_access_token()

evo = EvohomeClient(token_manager)
await evo.update()

# Access locations, zones, etc.
for location in evo.locations:
    print(location.name)

await token_manager.save_access_token()
await websession.close()
```

### CLI Usage
```bash
# Store credentials
evo-client login

# Get system mode
evo-client mode

# Download schedules
evo-client get-schedules --format text > schedules.txt

# Poll temperatures
evo-client poll --interval 60s --output temps.csv
```

## Project Statistics

- **Total Packages**: 3 (evohome, evohomeasync, evohomeasync2)
- **CLI Commands**: 10+ commands
- **Scripts**: 7 standalone utilities
- **Documentation Files**: 10 markdown files
- **Test Coverage**: Comprehensive (unit + integration)
- **Python Version**: 3.12+
- **License**: Apache-2.0
- **Build System**: Hatchling (PEP 517/518)
