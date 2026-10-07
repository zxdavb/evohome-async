"""Tests for evohome-async - validate the exceptions raised by the v2 client."""

from __future__ import annotations

import copy
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync2 import ControlSystem, EvohomeClient, Zone, exceptions as exc
from evohomeasync2.const import (
    SZ_GATEWAYS,
    SZ_MODEL_TYPE,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_ZONE_ID,
    SZ_ZONES,
    ZoneModelType,
)

from .conftest import FIXTURES_V2 as FIXTURES, auth_get
from .const import PUT_RESPONSE_V2

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


async def test_status_not_fetched(
    credentials_manager: TokenCacheManager, fixture_folder: Path
) -> None:
    """Test the status attrs raise NotFetchedError until the status is fetched."""

    evo = EvohomeClient(credentials_manager)

    with patch("evohomeasync2.auth.Auth.get", auth_get(fixture_folder)):
        await evo.update(dont_update_status=True)  # i.e. the config only

    tcs = evo.locations[0].gateways[0].systems[0]

    with pytest.raises(exc.NotFetchedError):
        _ = tcs.status
    with pytest.raises(exc.NotFetchedError):
        _ = tcs.zones[0].status
    if tcs.hotwater:
        with pytest.raises(exc.NotFetchedError):
            _ = tcs.hotwater.status


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


async def test_invalid_schedule_not_stored(evohome_v2: EvohomeClient) -> None:
    """Test a schedule whose switchpoints can't be found is not stored.

    A zone keeps its earlier schedule & switchpoints (if any), else it still has none.
    """

    zones = evohome_v2.locations[0].gateways[0].systems[0].zones

    fetched = zones[0]
    schedule = await fetched.get_schedule()
    switchpoints = (fetched.this_switchpoint, fetched.next_switchpoint)

    unfetched = zones[1]  # its schedule has not been fetched

    with (
        patch(
            "evohomeasync2.auth.Auth.get",
            AsyncMock(return_value={"daily_schedules": schedule}),
        ),
        patch.object(
            Zone,
            "_find_switchpoints",
            side_effect=exc.InvalidScheduleError("No switchpoints for next day"),
        ),
    ):
        for zone in (fetched, unfetched):
            with pytest.raises(exc.InvalidScheduleError):
                await zone.get_schedule()

    assert fetched.schedule == schedule
    assert (fetched.this_switchpoint, fetched.next_switchpoint) == switchpoints

    with pytest.raises(exc.NotFetchedError):
        _ = unfetched.schedule
    with pytest.raises(exc.NotFetchedError):
        _ = unfetched.this_switchpoint
    with pytest.raises(exc.NotFetchedError):
        _ = unfetched.next_switchpoint


async def test_set_schedule_before_get(evohome_v2: EvohomeClient) -> None:
    """Test the switchpoints are available after set_schedule(), without a get."""

    zones = evohome_v2.locations[0].gateways[0].systems[0].zones
    schedule = await zones[0].get_schedule()

    zone = zones[1]  # its schedule has not been fetched

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ):
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


async def test_ghost_zone_skipped(evohome_v2: EvohomeClient) -> None:
    """Test a TCS skips a ghost zone, and only that zone."""

    assert evohome_v2._user_locs is not None  # mypy
    tcs = evohome_v2.locations[0].gateways[0].systems[0]

    config = copy.deepcopy(
        evohome_v2._user_locs[0][SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0]
    )
    ghost = config[SZ_ZONES][1]
    ghost[SZ_MODEL_TYPE] = ZoneModelType.UNKNOWN

    new_tcs = ControlSystem(tcs.gateway, config)

    assert [z.id for z in new_tcs.zones] == [
        z.id for z in tcs.zones if z.id != ghost[SZ_ZONE_ID]
    ]
    assert len(new_tcs.zones) == len(tcs.zones) - 1


async def test_ghost_zone_other_errors(evohome_v2: EvohomeClient) -> None:
    """Test a TCS skips only a GhostZoneError: any other InvalidConfigError is raised."""

    assert evohome_v2._user_locs is not None  # mypy
    tcs = evohome_v2.locations[0].gateways[0].systems[0]

    config = evohome_v2._user_locs[0][SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0]
    error = exc.InvalidConfigError("Not a ghost zone")

    with (
        patch("evohomeasync2.control_system.Zone", side_effect=error),
        pytest.raises(exc.InvalidConfigError) as err,
    ):
        ControlSystem(tcs.gateway, config)

    assert err.value is error
