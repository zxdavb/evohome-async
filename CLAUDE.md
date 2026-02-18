# Instructions for Claude Code

Follow **CONTRIBUTING.md** in full. Key rules most likely to be violated:

1. **No lint/type suppressions** — no `# noqa`, `# type: ignore`, new `per-file-ignores`, or mypy overrides. Fix the code.
2. **Async I/O only** — `aiofiles` not `open()`, `aiohttp` not `requests`, `asyncio.sleep()` not `time.sleep()`.
3. **Timezone-aware datetimes** — always `dt.now(tz=UTC)`; import as `from datetime import UTC, datetime as dt`.
4. **Project exceptions** — raise from the hierarchy in `src/_evohome/exceptions.py`, never bare `Exception`.
5. **No `sys.exit()`** outside `cli/evohome_cli/client.py:main()`.
6. **Do not modify `pyproject.toml`** lint/type/test config.
7. **All new dependencies need justification** — `[project.dependencies]` requires explicit agreement; CLI-only deps go in `requirements_cli.txt`.

After any code change, verify:
```bash
ruff check .
ruff format --check .
mypy
```
