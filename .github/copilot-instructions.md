# Copilot Instructions for evohome-async

**Read `CONTRIBUTING.md` at the repo root — it is the single source of truth.**
Everything below is a summary for quick context; the full rules, examples, and
exception hierarchy are in that file.

## Critical rules (summary)

1. **All checks must pass as-is.** Run `ruff check .`, `ruff format --check .`,
   `mypy`, and `pytest`. Do NOT add `noqa`, `type: ignore`, `per-file-ignores`,
   or mypy `disable_error_code` to work around failures.

2. **Do not modify `pyproject.toml`** lint/type/test config. Changes will be
   rejected without significant justification.

3. **All datetimes must be timezone-aware:** `datetime.now(tz=UTC)`, never
   bare `datetime.now()`.

4. **All I/O must be async:** `aiohttp` for HTTP, `aiofiles` for files,
   `asyncclick` for CLI. No `open()`, `requests`, or `time.sleep()`.

5. **No bare `except Exception`.** When raising, use the project's exception
   hierarchy (`src/_evohome/exceptions.py`). Never swallow errors with `pass`.

6. **No `sys.exit()` in library code.** Only `cli/client.py:main()`.

## Key conventions

- `snake_case` names, `UPPER_SNAKE_CASE` constants, `_prefixed` privates.
- `from datetime import datetime as dt, timedelta as td`
- `import voluptuous as vol`
- Type annotations required everywhere (near-strict mypy).
- `TypedDict` for structured dicts, not `dict[str, Any]`.
- Logging via `_LOGGER`, never `print()` (except CLI `client.py`).

See `CONTRIBUTING.md` for the full project structure, exception tree, and
detailed guidance for AI agents.
