"""Tests for evohome-async - validate the exceptions raised by the v2 client."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync2 import EvohomeClient, Zone, exceptions as exc
from evohomeasync2.const import SZ_MODEL_TYPE, ZoneModelType

from .conftest import FIXTURES_V2 as FIXTURES

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


def _first_zone(evo: EvohomeClient) -> Zone:
    return evo.locations[0].gateways[0].systems[0].zones[0]


async def test_config_not_fetched(credentials_manager: TokenCacheManager) -> None:
    """Test the config attrs raise NotFetchedError until update() is called."""

    evo = EvohomeClient(credentials_manager)

    with pytest.raises(exc.NotFetchedError):
        _ = evo.tzinfo
    with pytest.raises(exc.NotFetchedError):
        _ = evo.user_account
    with pytest.raises(exc.NotFetchedError):
        _ = evo.locations
    with pytest.raises(exc.NotFetchedError):
        _ = evo.location_by_id


async def test_schedule_not_fetched(evohome_v2: EvohomeClient) -> None:
    """Test the schedule attrs raise NotFetchedError until get_schedule() is called."""

    zone = _first_zone(evohome_v2)

    with pytest.raises(exc.NotFetchedError):
        _ = zone.schedule
    with pytest.raises(exc.NotFetchedError):
        _ = zone.this_switchpoint
    with pytest.raises(exc.NotFetchedError):
        _ = zone.next_switchpoint


async def test_invalid_config(credentials_manager: TokenCacheManager) -> None:
    """Test update() raises InvalidConfigError if the config fails validation."""

    evo = EvohomeClient(credentials_manager)
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidConfigError) as err,
    ):
        await evo.update()

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error


async def test_invalid_status(evohome_v2: EvohomeClient) -> None:
    """Test update() raises InvalidStatusError if the status fails validation."""

    loc = evohome_v2.locations[0]
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidStatusError) as err,
    ):
        await loc.update()

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        # the schedule failed validation, or there is no schedule
        (exc.BadApiResponseError(_ERR_MSG), exc.InvalidScheduleError),
        (
            exc.ApiCallFailedError(_ERR_MSG, status=HTTPStatus.BAD_REQUEST),
            exc.InvalidScheduleError,
        ),
        # all other failures are not about the schedule, and so are left as they are
        (
            exc.ApiCallFailedError(_ERR_MSG, status=HTTPStatus.INTERNAL_SERVER_ERROR),
            exc.ApiCallFailedError,
        ),
        (
            exc.BadUserCredentialsError(_ERR_MSG, status=HTTPStatus.BAD_REQUEST),
            exc.BadUserCredentialsError,
        ),
        (exc.AuthRateLimitExceededError(_ERR_MSG), exc.AuthRateLimitExceededError),
    ],
    ids=lambda v: v.__name__ if isinstance(v, type) else type(v).__name__,
)
async def test_get_schedule_failures(
    evohome_v2: EvohomeClient,
    error: exc.EvohomeError,
    expected: type[exc.EvohomeError],
) -> None:
    """Test get_schedule() raises InvalidScheduleError only for a bad schedule."""

    zone = _first_zone(evohome_v2)

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(expected) as err,
    ):
        await zone.get_schedule()

    assert type(err.value) is expected


async def test_empty_schedule(evohome_v2: EvohomeClient) -> None:
    """Test an empty schedule is valid, and has no switchpoints."""

    zone = _first_zone(evohome_v2)

    with patch(
        "evohomeasync2.auth.Auth.get", AsyncMock(return_value={"daily_schedules": []})
    ):
        assert await zone.get_schedule() == []

    assert zone.schedule == []
    assert zone.this_switchpoint is None
    assert zone.next_switchpoint is None


async def test_set_schedule_before_get(evohome_v2: EvohomeClient) -> None:
    """Test the switchpoints are available after set_schedule(), without a get."""

    zones = evohome_v2.locations[0].gateways[0].systems[0].zones
    schedule = await zones[0].get_schedule()

    zone = zones[1]  # its schedule has not been fetched

    with patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock):
        await zone.set_schedule(schedule)

    assert zone.schedule == schedule
    assert zone.this_switchpoint is not None
    assert zone.next_switchpoint is not None
    assert zone.this_switchpoint[0] < zone.next_switchpoint[0]


async def test_ghost_zone(evohome_v2: EvohomeClient) -> None:
    """Test a zone without a (known) model type raises GhostZoneError."""

    zone = _first_zone(evohome_v2)

    config = zone._config.copy()
    config[SZ_MODEL_TYPE] = ZoneModelType.UNKNOWN

    with pytest.raises(exc.GhostZoneError):
        Zone(zone.tcs, config)
