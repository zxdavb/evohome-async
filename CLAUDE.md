# Instructions for Claude Code

Follow **CONTRIBUTING.md** in full. Key rules most likely to be violated:

1. **No lint/type suppressions** — no `# noqa`, `# type: ignore`, `cast()`, new `per-file-ignores`, or mypy overrides. Fix the underlying type issue instead. `cast()` is not an acceptable substitute for `# type: ignore` — both paper over type errors without fixing them. Pre-existing suppressions must not be copied to new code. **mypy is the authoritative type checker** (see verify commands below); Pylance/pyright is informational only, not gated. When the two disagree — most commonly on untyped third-party libraries (e.g. voluptuous, whose unannotated `Schema.__call__` pyright infers as `Unknown | Any | object`) — prefer a plain `# type: ignore[code]` targeted at mypy's specific error over restructuring working code to satisfy pyright, and don't add `# pyright: ignore` comments to chase it.
2. **Async I/O only** — `aiofiles` not `open()`, `aiohttp` not `requests`, `asyncio.sleep()` not `time.sleep()`.
3. **Timezone-aware datetimes** — always `dt.now(tz=UTC)`; import as `from datetime import UTC, datetime as dt`.
4. **Project exceptions** — raise from the hierarchy in `src/_evohome/exceptions.py`, never bare `Exception`; do not raise generic exceptions (e.g. TypeError)
5. **No `sys.exit()`** outside `src/evohome_cli/client.py:main()`.
6. **Do not modify `pyproject.toml`** lint/type/test config.
7. **All new dependencies need justification** — `[project.dependencies]` requires explicit agreement; CLI-only deps go in `pyproject.toml` optional extras (e.g. `[project.optional-dependencies]`).
8. **Never delete unreferenced `Tcc*` TypedDicts/StrEnums from the schema modules** — `src/evohomeasync2/schemas/*.py` (v2) and `src/evohomeasync/schemas.py` (v1). The vendor's API is undocumented, so these **are** the documentation: they are the best known description of the vendor's JSON shape and the source of truth for static typing. Being unreferenced by library code is their normal state, not a sign of dead code — each module's docstring says so explicitly ("serve as documentation of the vendor's API, even if they are unused by this library"). Ruff does not flag unused module-level classes, so nothing will contradict you; do not "clean them up". The same applies to the `factory_*` functions that build the matching `vol.Schema` validators. Two live consequences: keep a `Tcc*T` and its `factory_*` in agreement when you touch either (a divergence is a real bug — the schema is what runs), and remember the vendor casing convention they record — camelCase JSON keys, PascalCase enum values.

After any code change, verify:

```bash
ruff check .
ruff format --check .
mypy
```
