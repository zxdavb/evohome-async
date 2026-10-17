"""Tests for evohome-async - the locations must be consistent with the config JSON.

Every location known from the config should be in the status, and vice versa. If not, a
warning is logged (the known locations are still updated).
"""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync.const import SZ_LOCATION_ID
from evohomeasync.schemas import _LocationIdT

from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [Path(FIXTURES) / "default"]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_location_unknown(
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A location that is not in the config should be ignored, with a warning."""

    assert ec1._user_locs is not None  # mypy

    user_locs = deepcopy(ec1._user_locs)
    user_locs.append(deepcopy(user_locs[0]))
    user_locs[-1][SZ_LOCATION_ID] = _LocationIdT(9999999)

    with (
        caplog.at_level(logging.WARNING),
        patch("evohomeasync.auth.Auth.get", AsyncMock(return_value=user_locs)),
    ):
        await ec1.get_status()
        await ec1.get_status()  # the same as update()

    msg = (
        f"{ec1}: status has location_id='9999999' not known"
        ", (has the account configuration changed?)"
    )
    assert [r.message for r in caplog.records] == [msg]  # i.e. is logged only once


async def test_location_absent(
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A location of the config that is not in the status should log a warning."""

    loc = ec1.locations[0]

    with (
        caplog.at_level(logging.WARNING),
        patch("evohomeasync.auth.Auth.get", AsyncMock(return_value=[])),
    ):
        await ec1.get_status()
        await ec1.get_status()  # the same as update()

    msg = (
        f"{ec1}: status has no entry for location_id='{loc.id}'"
        ", (has the account configuration changed?)"
    )
    assert [r.message for r in caplog.records] == [msg]  # i.e. is logged only once
