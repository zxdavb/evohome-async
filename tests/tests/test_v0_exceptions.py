"""Tests for evohome-async - validate the exceptions raised by the v0 client."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync import EvohomeClient, exceptions as exc
from tests.common import get_loc

from .conftest import FIXTURES_V0 as FIXTURES

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager

_ERR_MSG = "GET url: response failed validation: ..."


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "fixture_folder" not in metafunc.fixturenames:
        return

    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and p.name == "default"
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_config_not_fetched(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test the config attrs raise NotFetchedError until update() is called."""

    evo = EvohomeClient(credentials_manager)

    with pytest.raises(exc.NotFetchedError):
        _ = evo.user_account
    with pytest.raises(exc.NotFetchedError):
        _ = evo.locations
    with pytest.raises(exc.NotFetchedError):
        _ = evo.location_by_id


async def test_invalid_config(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update() raises InvalidConfigError if the config fails validation."""

    evo = EvohomeClient(credentials_manager)
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidConfigError) as err,
    ):
        await evo.update()

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error


async def test_invalid_status(
    evohome_v0: EvohomeClient,
) -> None:
    """Test update() raises InvalidStatusError if the status fails validation."""

    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidStatusError) as err,
    ):
        await evohome_v0.update()  # the entities exist, so this is a status update

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error


async def test_unknown_zone(
    evohome_v0: EvohomeClient,
) -> None:
    """Test asking for a zone that does not exist raises BadApiRequestError."""

    loc = get_loc(evohome_v0)

    with pytest.raises(exc.BadApiRequestError):
        loc._get_zone("no such zone")
