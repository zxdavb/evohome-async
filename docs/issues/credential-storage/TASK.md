# Task: Implement feat/credential-storage Branch

## Objective
Create a clean credential-storage branch from upstream/main addressing all PR #43 feedback (issues #1-#5).

## Checklist

### Branch Setup
- [x] Create `feat/credential-storage` branch from `upstream/main`
- [x] Verify clean starting point

### Core Implementation
- [x] Add custom exceptions to `_evohome/exceptions.py`
- [x] Implement `KeyringCredentialManager` class in `auth.py`
- [x] Update `client.py` with credential resolution and login command
- [x] Update `main()` to handle login as standalone command

### Configuration & Cleanup
- [x] Update `AGENTS.md` (issue #2) — N/A, doesn't exist in upstream
- [x] Remove `.env.example` (issue #3)
- [x] Clean up `.gitignore` — N/A, no changes needed
- [x] Verify `pyproject.toml` has no broad suppressions (issue #1)

### Testing
- [x] Create `test_cli_auth.py` for KeyringCredentialManager
- [x] Run pytest — all tests pass (16/16)
- [x] Run ruff — zero critical warnings
- [x] Run mypy — zero errors

### Verification
- [x] Verify no schedule/polling imports
- [x] Verify no broad except clauses (only 1 intentional with noqa)
- [x] Git diff shows only credential-storage files
