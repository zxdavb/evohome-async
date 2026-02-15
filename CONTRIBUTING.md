# Contributing to evohome-async

Thank you for your interest in contributing. This library is consumed by
[Home Assistant](https://www.home-assistant.io/integrations/evohome), so
contributions must meet production-quality standards.

**Please read this file in full before starting work.** AI-assisted PRs that
ignore these guidelines will be closed.

---

## Quick-start checklist

Before opening a PR, **every one** of these commands must pass cleanly:

```bash
ruff check .               # linting — zero warnings
ruff format --check .      # formatting
mypy                       # strict type checking
pytest                     # full test suite
```

If your change introduces a new warning or error, fix your code — do **not** add
suppression comments, per-file ignores, or mypy overrides. If you find a
pre-existing issue in the codebase, please raise it separately (or better yet,
submit a focused PR to fix it).

---

## Golden rules

### 1. The linting / typing config is not negotiable

`pyproject.toml` defines strict ruff and near-strict mypy settings on purpose.
PRs that weaken the configuration to make new code pass **will be rejected**.
Specifically:

- Do **not** add `# noqa`, `# type: ignore`, `per-file-ignores`, or new
  `[[tool.mypy.overrides]]` sections.
- Do **not** add new entries to `[tool.ruff.lint.ignore]`.
- The single existing mypy override is for vendored third-party code and is not
  a precedent for application code.

If you believe a rule is genuinely wrong for a specific case, raise it in the PR
description for discussion — do not silently suppress it.

### 2. All datetimes must be timezone-aware

This is enforced by both ruff (`DTZ` rules) and mypy.

```python
# ✅ Correct
from datetime import UTC, datetime as dt
now = dt.now(tz=UTC)

# ❌ Wrong — will be caught by DTZ005
from datetime import datetime
now = datetime.now()
```

The project convention is to alias: `from datetime import datetime as dt`.

### 3. All I/O must be async

| Need          | Use                | Not                    |
|---------------|--------------------|------------------------|
| HTTP requests | `aiohttp`          | `requests`, `urllib`   |
| File I/O      | `aiofiles`         | `open()`, `pathlib.read_text()` |
| CLI framework | `asyncclick`       | `click` (sync)         |
| Sleep         | `asyncio.sleep()`  | `time.sleep()`         |

Never call blocking I/O in an async code path. The `ASYNC` ruff rules enforce
this.

### 4. Use the project's exception hierarchy

See `src/_evohome/exceptions.py`. Key types:

```
EvohomeError
├── ApiRequestFailedError        # API call failed
│   ├── ApiRateLimitExceededError
│   └── AuthenticationFailedError
│       └── BadUserCredentialsError
├── BadApiSchemaError            # API returned unexpected data
├── ConfigError                  # Bad config JSON
└── StatusError                  # Bad status/schedule JSON
```

- Do **not** raise bare `Exception`, `RuntimeError`, or `ValueError` in library
  code.
- Do **not** use bare `except Exception:` — catch the specific type you expect.
- Never silently swallow errors with `pass`. At minimum, log a warning.

### 5. No `sys.exit()` in library code

Only the CLI entry-point (`main()` in `client.py`) may call `sys.exit()`.
Library code must raise exceptions and let callers decide.

### 6. Dependencies require discussion

Do not add, remove, or change entries in `[project.dependencies]` without prior
agreement. This library is a transitive dependency of Home Assistant — every new
dependency has significant downstream impact.

Optional dev/CLI dependencies in `requirements_*.txt` are less sensitive but
still warrant justification.

---

## Code conventions

| Topic              | Convention |
|--------------------|------------|
| Attribute names    | `snake_case` (not `camelCase`) |
| Entity IDs         | `.id` (not `.zoneId`, `.dhwId`) |
| Constants          | `UPPER_SNAKE_CASE` |
| Private members    | `_prefixed` |
| Datetime import    | `from datetime import datetime as dt` |
| UTC import         | `from datetime import UTC` |
| Logging            | `_LOGGER = logging.getLogger(__name__)` |
| Type annotations   | Required on every function/method |
| Structured dicts   | `TypedDict`, not `dict[str, Any]` |
| Schema validation  | `voluptuous` (not pydantic, not dataclasses) |
| Build backend      | Hatchling — version lives in `src/_evohome/__init__.py` |

### Logging vs printing

- **Library code** (`_evohome`, `evohomeasync`, `evohomeasync2`): use `_LOGGER`,
  never `print()`. The `T201` ruff rule enforces this.
- **CLI code** (`evohome_cli/client.py`): `print()` is permitted (suppressed via
  `per-file-ignores`). Do not extend this suppression to other files without
  good reason.

---

## Project structure

```
src/
  _evohome/           # Shared internals (auth, exceptions, helpers, timezone)
  evohomeasync/       # Legacy v0 API client (backward compat)
  evohomeasync2/      # Primary v2 API client — most work happens here
  evohome_cli/        # CLI tool (excluded from coverage)
tests/
  tests/              # Main test suite
  tests_rf/           # Request/response fixture tests
```

The **library** (`_evohome`, `evohomeasync`, `evohomeasync2`) is the published
deliverable. The CLI is a developer convenience and is explicitly excluded from
code coverage.

---

## Commit and PR hygiene

- Keep PRs focused — one logical change per PR.
- Use [conventional commits](https://www.conventionalcommits.org/) if possible.
- Include or update tests for any behavioural change.
- Do not commit generated files, IDE configuration, or `__pycache__/`.
- Do not add top-level documentation dumps (e.g., 500-line `AGENTS.md`,
  `Architecture.md`). Keep docs proportional to the change.

---

## For AI coding agents

If you are an AI tool generating code for this project, pay particular attention
to the following — these are the most common mistakes:

1. **Do not disable lint/type rules.** Fix the code instead.
2. **Use `dt.now(tz=UTC)`**, never bare `datetime.now()`.
3. **Use `aiofiles.open()`** in async functions, not `open()`.
4. **Catch specific exceptions**, not `Exception`.
5. **Do not add `sys.exit()`** outside of `cli/client.py:main()`.
6. **Do not create sprawling documentation files.** A clear docstring and a
   concise PR description are preferred.
7. **Run the full check suite** (`ruff check .`, `mypy`, `pytest`) and verify
   it passes with zero new warnings before declaring the work complete.
8. **Do not modify `pyproject.toml`** unless the change is to project metadata
   (description, URLs, classifiers). Lint/type/test config changes require
   explicit maintainer approval.
