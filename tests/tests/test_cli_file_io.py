"""Test the CLI's file I/O (the token cache, and the --input-file/--output-file)."""

from __future__ import annotations

import io
import json
import stat
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os
import asyncclick as click
import pytest

from evohome_cli.auth import TokenCacheManager
from evohome_cli.client import _read_input, _write_output

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import CacheDataT


_DATA: dict[str, object] = {"key": "value", "list": [1, 2]}


async def test_cache_file_is_private(
    client_session: aiohttp.ClientSession, tmp_path: Path
) -> None:
    """Check the cache's folder is created, and that only its owner can access it."""

    cache_path = tmp_path / "evohome" / ".evo-cache.tst~"  # the folder doesn't exist
    manager = TokenCacheManager(
        "username", "password", client_session, cache_path=cache_path
    )

    cache: CacheDataT = {}
    await manager._write_cache_to_file(cache)

    assert (
        stat.S_IMODE((await aiofiles.os.stat(cache_path.parent)).st_mode)
        == stat.S_IRWXU
    )
    assert stat.S_IMODE((await aiofiles.os.stat(cache_path)).st_mode) == (
        stat.S_IRUSR | stat.S_IWUSR
    )

    assert await manager._read_cache_from_file() == cache

    await manager._write_cache_to_file(cache)  # the folder now exists, the file too
    assert await manager._read_cache_from_file() == cache


async def test_write_output_to_file(tmp_path: Path) -> None:
    """Check the output is written to a file, as JSON."""

    output_file = tmp_path / "output.json"
    await _write_output(str(output_file), _DATA)

    async with aiofiles.open(output_file) as fp:
        assert json.loads(await fp.read()) == _DATA


async def test_write_output_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Check the output is written to stdout, as JSON, if the file is '-'."""

    await _write_output("-", _DATA)

    assert json.loads(capsys.readouterr().out) == _DATA


async def test_write_output_fails(tmp_path: Path) -> None:
    """Check a file that can't be written raises a click.FileError."""

    with pytest.raises(click.FileError):
        await _write_output(str(tmp_path / "no_such_dir" / "output.json"), _DATA)


async def test_read_input_from_file(tmp_path: Path) -> None:
    """Check the input is read from a file."""

    input_file = tmp_path / "input.json"
    async with aiofiles.open(input_file, "w") as fp:
        await fp.write(json.dumps(_DATA))

    assert json.loads(await _read_input(str(input_file))) == _DATA


async def test_read_input_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check the input is read from stdin, if the file is '-'."""

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_DATA)))

    assert json.loads(await _read_input("-")) == _DATA


async def test_read_input_fails(tmp_path: Path) -> None:
    """Check a file that can't be read raises a click.FileError."""

    with pytest.raises(click.FileError):
        await _read_input(str(tmp_path / "no_such_file.json"))
