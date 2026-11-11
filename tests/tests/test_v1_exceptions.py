"""Test the exceptions raised by the v1 client."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync import EvohomeClient, exceptions as exc
from tests.common import get_tcs

from .conftest import FIXTURES_V1 as FIXTURES

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

    ec1 = EvohomeClient(credentials_manager)

    with pytest.raises(exc.NotFetchedError) as exc_info:
        _ = ec1.user_account
    assert exc_info.value.reason is exc.ClientStateErrorReason.CONFIG_NOT_FETCHED
    with pytest.raises(exc.NotFetchedError) as exc_info:
        _ = ec1.user_id
    assert exc_info.value.reason is exc.ClientStateErrorReason.CONFIG_NOT_FETCHED
    with pytest.raises(exc.NotFetchedError) as exc_info:
        _ = ec1.locations
    assert exc_info.value.reason is exc.ClientStateErrorReason.CONFIG_NOT_FETCHED
    with pytest.raises(exc.NotFetchedError) as exc_info:
        _ = ec1.location_by_id
    assert exc_info.value.reason is exc.ClientStateErrorReason.CONFIG_NOT_FETCHED


async def test_invalid_config(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update() raises InvalidGetConfigError if the config fails validation."""

    ec1 = EvohomeClient(credentials_manager)
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidGetConfigError) as err,
    ):
        await ec1.get_status()

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error
    assert err.value.reason is exc.ResponseErrorReason.CONFIG_INVALID


async def test_invalid_account(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test get_status() raises InvalidGetConfigError if the account has no user_id."""

    ec1 = EvohomeClient(credentials_manager)

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(return_value={})),
        pytest.raises(exc.InvalidGetConfigError) as err,
    ):
        await ec1.get_status()

    assert err.value.reason is exc.ResponseErrorReason.ACCOUNT_INVALID


async def test_invalid_status(
    ec1: EvohomeClient,
) -> None:
    """Test update() raises InvalidGetStatusError if the status fails validation."""

    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidGetStatusError) as err,
    ):
        await ec1.get_status()  # the entities exist, so this is a status update

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error
    assert err.value.reason is exc.ResponseErrorReason.STATUS_INVALID


async def test_unknown_zone(
    ec1: EvohomeClient,
) -> None:
    """Test asking for a zone that does not exist raises BadApiRequestError."""

    tcs = get_tcs(ec1)

    with pytest.raises(exc.BadApiRequestError) as exc_info:
        tcs._get_zone("no such zone")

    assert exc_info.value.reason is exc.RequestErrorReason.ZONE_UNKNOWN
