# AI Agent Guidance for evohome-async

This document provides guidance for AI coding agents working on the **evohome-async** project. It complements the existing documentation and helps agents understand the project structure, conventions, and best practices.

## Project Overview

**evohome-async** is a Python async client library for Honeywell's Total Connect Comfort (TCC) RESTful API, supporting Evohome, Round Thermostat, VisionPro, and other EU/EMEA-based heating control systems.

- **Version**: 1.0.5
- **License**: Apache-2.0
- **Python**: ≥3.12
- **Primary Use**: Home automation integration (especially Home Assistant)

## Quick Reference

### Key Documentation
- **Architecture.md**: Detailed system architecture and CLI design
- **ProjectAnalysis.md**: Comprehensive project analysis
- **CLI.md**: CLI usage guide
- **ScheduleJSON.md** / **TextSchedule.md**: Schedule format specifications

### Entry Points
- **Library**: `src/evohomeasync2/` (v2 API, primary)
- **CLI**: `cli/client.py` (entry point: `evo-client`)
- **Tests**: `tests/tests/` (pytest-based)

## Project Structure

```
evohome-async/
├── src/
│   ├── evohome/           # Shared utilities, version, auth
│   ├── evohomeasync/      # Legacy v0 API (backward compatibility)
│   └── evohomeasync2/     # Current v2 API (PRIMARY)
├── cli/                   # CLI utilities (not part of core library)
│   ├── auth.py           # Token management, credential storage
│   ├── client.py         # Main CLI commands
│   ├── poll_evohome.py   # Temperature polling
│   └── schedule_parser.py # Format conversion (JSON ↔ Text)
├── tests/                 # Test suite
│   ├── tests/            # Main tests
│   └── tests_rf/         # Request/response fixtures
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

## Code Quality Standards

### Type Checking (mypy)
- **Strict mode enabled** - All functions must have type annotations
- **No implicit Any** - Explicit types required
- **TZ-aware datetimes** - All datetime objects must be timezone-aware
- Run: `mypy cli src tests`

### Linting (ruff)
- **40+ rule categories** enabled (see `pyproject.toml`)
- **Target**: Python 3.13 (for future compatibility)
- **Key checks**: PEP 8, security (bandit), performance, async best practices
- Run: `ruff check cli src tests`

### Testing (pytest)
- **Async mode**: Auto-detection
- **Coverage**: Comprehensive unit + integration tests
- **Fixtures**: Function-scoped event loops
- Run: `pytest tests/`

### Pre-commit Hooks
- Configured in `.pre-commit-config.yaml`
- Runs type checking, linting, and tests before commit

## Coding Conventions

### Naming
- **Attributes**: `snake_case` (e.g., `.zone_id`, not `.zoneId`)
- **Entity IDs**: Use `.id` (not `.zoneId`, `.dhwId`, etc.)
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: Prefix with `_` (e.g., `_internal_function()`)

### Async/Await
- **All I/O operations** must be async
- Use `aiohttp` for HTTP requests
- Use `aiofiles` for file operations
- Use `asyncclick` for CLI commands

### Error Handling
- **Parochial exceptions** (e.g., `AuthenticationFailedError`, not generic `TypeError`)
- **Proper logging** with context
- **Graceful degradation** where possible

### Documentation
- **Docstrings**: Required for all public functions/classes
- **Type hints**: Required for all function signatures
- **Comments**: Explain "why", not "what"

## Common Tasks

### Adding a New CLI Command

**Option 1: Simple command in `client.py`**
```python
@cli.command("mycommand")
@click.option("--option", help="Description")
@click.pass_context
async def mycommand(ctx: click.Context, option: str) -> None:
    """Command description."""
    # Implementation
```

**Option 2: Complex command in separate module** (like `poll_evohome.py`)
1. Create `cli/mycommand.py`
2. Define helper functions at module level (for testability)
3. Create `register_command(cli_group)` function
4. Import dependencies inside `register_command()` (avoid circular imports)
5. In `client.py`: `from cli.mycommand import register_command as register_mycommand`
6. Call `register_mycommand(cli)` after CLI group definition

### Working with Schedules

**Two formats supported:**
1. **JSON**: API-compatible, structured (see `ScheduleJSON.md`)
2. **Text**: Human-readable, editable (see `TextSchedule.md`)

**Conversion:**
- `parse_text_schedule(text)` → JSON
- `json_to_text_schedule(schedules)` → Text

**Key functions in `schedule_parser.py`:**
- `parse_temperature_time()`: Extract temp/time pairs
- `parse_day_spec()`: Parse day specifications
- `_format_day_spec()`: Optimize day grouping
- `_group_days_by_schedule()`: Group identical schedules

### Authentication Flow

**Credential Priority:**
1. Command-line options (`--username`, `--password`)
2. Stored credentials (from system keyring)
3. Error if neither available

**Credential Storage:**
- **macOS**: Keychain Access
- **Windows**: Credential Manager
- **Linux**: Secret Service (GNOME Keyring, KWallet)

**Functions in `cli/auth.py`:**
- `get_stored_credentials()`: Retrieve from keyring
- `store_credentials()`: Save to keyring
- `delete_stored_credentials()`: Remove from keyring
- `get_credential_storage_location()`: Get platform-specific location

### Token Management

**Token caching:**
- Cached to `.evo-cache.tmp` (configurable)
- Automatic refresh when expired
- Reduces API calls

**Classes:**
- `TokenManager` (evohomeasync2): v2 API tokens
- `SessionManager` (evohomeasync): v0 API sessions
- `CredentialsManager` (cli): Unified token + credential management

## Testing Guidelines

### Test Organization
- **Unit tests**: Test individual functions
- **Integration tests**: Test CLI commands with mocked API
- **Format conversion tests**: Round-trip validation (text → JSON → text)

### Test Files
- `test_cli_schedules.py`: Schedule conversion and CLI
- `test_cli_auth.py`: Credential storage and login
- `test_cli_poll_evohome.py`: Temperature polling
- `test_v2_auth.py`: Core authentication
- `test_v2_apis.py`: API interactions

### Writing Tests
```python
import pytest
from cli.schedule_parser import parse_text_schedule, json_to_text_schedule

@pytest.mark.asyncio
async def test_schedule_conversion():
    """Test round-trip schedule conversion."""
    text = "1. Zone (123)\nWeekdays: 16C @ 06:00 to 17.5C @ 21:50"
    json_data = parse_text_schedule(text)
    result = json_to_text_schedule(json_data)
    assert "Weekdays" in result
    assert "16C @ 06:00" in result
```

## Security Considerations

### Credentials
- **Never log** credentials or tokens
- **Never expose** in error messages
- **Use keyring** for storage (not plain text)
- **Hidden input** for interactive password prompts

### Token Storage
- Cached tokens in restricted-permission files
- Automatic token refresh
- Secure transmission via HTTPS

### Input Validation
- All user inputs validated
- Schema validation with `voluptuous`
- Type checking with `mypy`

## Common Pitfalls

### 1. Circular Imports
**Problem**: Importing `client.py` from other CLI modules causes circular imports.
**Solution**: Import inside `register_command()` function (see `poll_evohome.py`).

### 2. Timezone Handling
**Problem**: Naive datetime objects cause issues.
**Solution**: Always use TZ-aware datetimes (see `evohome/time_zone.py`).

### 3. Async Context
**Problem**: Calling sync functions in async context.
**Solution**: Use `aiofiles`, `aiohttp`, and `asyncclick` for all I/O.

### 4. Type Annotations
**Problem**: Missing or incomplete type hints fail mypy.
**Solution**: Add complete type annotations, use `TypedDict` for complex structures.

### 5. Schedule Format Confusion
**Problem**: Mixing JSON and text formats.
**Solution**: Use `--format` option to specify format explicitly.

## API Interaction

### Main Classes
- **EvohomeClient** (`evohomeasync2.main`): Main client class
- **Location** (`evohomeasync2.location`): Location entity
- **ControlSystem** (`evohomeasync2.control_system`): TCS entity
- **Zone** (`evohomeasync2.zone`): Zone entity
- **HotWater** (`evohomeasync2.hotwater`): DHW entity

### Typical Usage
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
    for tcs in location.control_systems:
        for zone in tcs.zones:
            print(f"{zone.name}: {zone.temperature}°C")

await token_manager.save_access_token()
await websession.close()
```

## Build and Distribution

### Build System
- **Backend**: Hatchling (PEP 517/518)
- **Version**: Dynamic from `src/evohome/__init__.py`
- **Packages**: `evohomeasync`, `evohomeasync2`, `evohome`

### Installation
```bash
# Development
pip install -e .

# Production
pip install evohome-async
```

### Entry Point
```toml
[project.scripts]
evo-client = "cli.client:main"
```

## Dependencies

### Runtime (Required)
- `aiohttp>=3.11.12`: Async HTTP client
- `aiozoneinfo>=0.2.3`: Async timezone support
- `voluptuous>=0.15.2`: Schema validation

### CLI (Optional)
- `asyncclick`: Async CLI framework
- `aiofiles`: Async file operations
- `keyring`: Secure credential storage

### Development
- `pytest`: Testing framework
- `mypy`: Static type checking
- `ruff`: Linting and formatting
- `hatchling`: Build backend

## Version Management

- **Version file**: `src/evohome/__init__.py`
- **Format**: `__version__ = "1.0.5"`
- **Semantic versioning**: MAJOR.MINOR.PATCH
- **Hatchling**: Reads version dynamically during build

## Monitoring Components

**Note**: Energy meter polling, weather data collection, and InfluxDB utilities have been moved to a separate `../monitor/` folder. See `monitor/README.md` for details.

## Future Enhancements

Potential improvements:
- DHW (Domestic Hot Water) schedule support in text format
- Schedule validation before upload
- Schedule comparison/diff functionality
- Template-based schedule generation
- Batch operations for multiple locations
- Python 3.13+ specific optimizations

## Getting Help

### Documentation
- **README.md**: Quick start and overview
- **Architecture.md**: Detailed architecture
- **CLI.md**: CLI usage guide
- **ProjectAnalysis.md**: Comprehensive analysis

### External Resources
- **TCC API**: [Total Connect Comfort](https://international.mytotalconnectcomfort.com/)
- **Home Assistant**: [Evohome Integration](https://www.home-assistant.io/integrations/evohome)
- **Legacy Client**: [evohome-client](https://github.com/watchforstock/evohome-client)

## Summary

When working on this project:
1. ✅ **Use strict type checking** - mypy must pass
2. ✅ **Follow async patterns** - All I/O must be async
3. ✅ **Test thoroughly** - Unit + integration tests
4. ✅ **Document changes** - Docstrings + comments
5. ✅ **Secure credentials** - Use keyring, never plain text
6. ✅ **Validate inputs** - Schema validation + type checking
7. ✅ **Handle errors gracefully** - Parochial exceptions + logging
8. ✅ **Maintain compatibility** - Support both v0 and v2 APIs

This is a well-architected, production-ready library with high code quality standards. Maintain these standards in all contributions.
