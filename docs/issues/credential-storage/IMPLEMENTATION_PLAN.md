# feat/credential-storage Branch — Implementation Plan

## Goal

Create a clean `feat/credential-storage` branch from `upstream/main` that adds **only** the secure credential storage feature. This addresses GitHub issues [#1](https://github.com/divyavanmahajan/evohome-async/issues/1), [#2](https://github.com/divyavanmahajan/evohome-async/issues/2), [#3](https://github.com/divyavanmahajan/evohome-async/issues/3), [#4](https://github.com/divyavanmahajan/evohome-async/issues/4), and [#5](https://github.com/divyavanmahajan/evohome-async/issues/5).

## Approach

Rather than cherry-picking from the combined `master` branch (which mixes all three features), we will:
1. Create a new branch from `upstream/main`
2. Write clean new files that implement **only** the credential storage feature
3. Address **all** reviewer feedback (no broad excepts, keyring as a class, no linting suppressions)

---

## Proposed Changes

### Auth Module

#### [MODIFY] [auth.py](file:///Users/divya/Documents/projects/homeautomation/evohome-async/src/evohome_cli/auth.py)

Add a new `KeyringCredentialManager` class following the `AbstractTokenManager` pattern, replacing the standalone functions.

**Key changes:**
- Add `import keyring` with graceful fallback (keep existing `try/except ImportError`)
- Add constants: `CREDENTIAL_SERVICE_NAME`, `CREDENTIAL_USERNAME_KEY`, `CREDENTIAL_PASSWORD_KEY`
- Add `KeyringCredentialManager` class with methods:
  - `get_credentials() -> tuple[str, str] | None`
  - `store_credentials(username, password) -> None`
  - `delete_credentials() -> None`
  - `storage_location` property
- **No broad excepts**: catch `keyring.errors.KeyringError` specifically
- **No `RuntimeError`**: raise `EvohomeError` subclass instead
- Keep existing `CredentialsManager` class untouched (it handles token caching, not keyring)

---

### CLI Module

#### [MODIFY] [client.py](file:///Users/divya/Documents/projects/homeautomation/evohome-async/src/evohome_cli/client.py)

Add the `login` command and credential resolution to the existing CLI. **Do not** include schedule conversion or temperature polling.

**Key changes:**
- Import `KeyringCredentialManager` from `.auth` (not the standalone functions)
- Modify `cli()` group: change `--username`/`--password` from `required=True` to `default=None`, add credential resolution from keyring
- Add `login` click command (standalone, not under `cli` group)
- Modify `main()` to handle `login` as a standalone command
- **No imports** from `.poll_evohome` or `.schedule_parser`
- **No `--format` option** on `get_schedules`/`set_schedules` (that's the schedule feature)
- **No broad excepts** in login command: catch `EvohomeError` specifically

---

### Configuration

#### [MODIFY] [pyproject.toml](file:///Users/divya/Documents/projects/homeautomation/evohome-async/pyproject.toml)

- **Do not add** the broad mypy overrides block for CLI modules
- **Do not add** broad per-file-ignores for `auth.py`, `poll_evohome.py`, `schedule_parser.py`
- Keep only the upstream-original per-file-ignores for `client.py` (`EXE001`, `T201`)
- May need to add `BLE001` (blind except) for `client.py` if the login command legitimately needs it — but prefer fixing the code instead

---

### Dependencies

#### [MODIFY] [requirements_dev.txt](file:///Users/divya/Documents/projects/homeautomation/evohome-async/requirements_dev.txt)

- **Do not add** `aiozoneinfo` (it's for schedule parsing, not credential storage)

---

### Cleanup

#### [DELETE] [.env.example](file:///Users/divya/Documents/projects/homeautomation/evohome-async/.env.example)

- Not needed for credential storage feature

#### [MODIFY] [.gitignore](file:///Users/divya/Documents/projects/homeautomation/evohome-async/.gitignore)

- Keep `.env` in `.gitignore` (good practice) but remove `*.csv` (that's for polling)

---

### Documentation

#### [MODIFY] [AGENTS.md](file:///Users/divya/Documents/projects/homeautomation/evohome-async/AGENTS.md)

- Update to reflect current repo state (fix outdated content per issue #2)
- Only describe credential storage feature additions

---

### Tests

#### [NEW] [test_cli_auth.py](file:///Users/divya/Documents/projects/homeautomation/evohome-async/tests/tests/test_cli_auth.py)

Adapt the existing test file to test the new `KeyringCredentialManager` class instead of standalone functions:

- Test `get_credentials()` — with keyring, without, with errors
- Test `store_credentials()` — with keyring, without, with errors
- Test `delete_credentials()` — with keyring, without, with errors
- Test `storage_location` property — various backends
- Test credential resolution in CLI (no integration with actual API)
- **No broad mocking**: mock `keyring.errors.KeyringError` specifically

---

## Files NOT Included (for later PRs)

| File | Feature | PR |
|---|---|---|
| `src/evohome_cli/schedule_parser.py` | Text schedule format | PR 2 |
| `src/evohome_cli/poll_evohome.py` | Temperature polling | PR 3 |
| `tests/tests/test_cli_schedules.py` | Schedule tests | PR 2 |
| `tests/tests/test_cli_poll_evohome.py` | Polling tests | PR 3 |
| `docs/TextSchedule.md`, `docs/ScheduleJSON.md` | Schedule docs | PR 2 |
| `docs/LogTemperatureCSV.md` | Polling docs | PR 3 |

---

## Verification Plan

### Automated Tests

```bash
# Run credential storage tests only
pytest tests/tests/test_cli_auth.py -v

# Run full test suite to ensure no regressions
pytest tests/ -v

# Lint check — zero new warnings
ruff check src/evohome_cli/auth.py src/evohome_cli/client.py tests/tests/test_cli_auth.py

# Type check — zero errors
mypy src/evohome_cli/auth.py src/evohome_cli/client.py
```

### Manual Verification

1. **Verify branch is clean**: `git diff upstream/main --name-only` should show only credential-storage files
2. **Verify no schedule/polling imports**: `grep -r "schedule_parser\|poll_evohome" src/evohome_cli/client.py` should return empty
3. **Verify no broad excepts**: `grep -n "except Exception" src/evohome_cli/` should return empty
4. **Verify pyproject.toml is clean**: `git diff upstream/main -- pyproject.toml` should show minimal or no changes
