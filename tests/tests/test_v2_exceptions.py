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
from tests.common import get_dhw, get_loc, get_tcs, get_zon
from tests.const import TEST_LOC_IDX

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


async def test_config_not_fetched(
    credentials_manager: TokenCacheManager,
) -> None:
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


async def test_schedule_not_fetched(
    zone: Zone,
) -> None:
    """Test the schedule attrs raise NotFetchedError until get_schedule() is called."""

    with pytest.raises(exc.NotFetchedError):
        _ = zone.schedule
    with pytest.raises(exc.NotFetchedError):
        _ = zone.this_switchpoint
    with pytest.raises(exc.NotFetchedError):
        _ = zone.next_switchpoint


async def test_status_not_fetched(
    credentials_manager: TokenCacheManager,
    fixture_folder: Path,
) -> None:
    """Test the status attrs raise NotFetchedError until the status is fetched."""

    evo = EvohomeClient(credentials_manager)

    with patch("evohomeasync2.auth.Auth.get", auth_get(fixture_folder)):
        await evo.setup()  # i.e. the config only

    # not the tcs/zone/dhw fixtures: they come from evohome_v2, which has fetched the
    # status (so nothing would raise), whereas this client has fetched only the config
    tcs = get_tcs(evo)

    with pytest.raises(exc.NotFetchedError):
        _ = tcs.status
    zone = get_zon(evo)
    assert zone is not None  # the default/ fixture has zones
    with pytest.raises(exc.NotFetchedError):
        _ = zone.status
    if dhw := get_dhw(evo):  # not the dhw fixture (see above)
        with pytest.raises(exc.NotFetchedError):
            _ = dhw.status


async def test_invalid_config(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update() raises InvalidConfigError if the config fails validation."""

    evo = EvohomeClient(credentials_manager)
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidConfigError) as err,
    ):
        await evo.setup()

    assert err.value.message == _ERR_MSG
    assert err.value.__cause__ is error


async def test_invalid_status(
    evohome_v2: EvohomeClient,
) -> None:
    """Test update() raises InvalidStatusError if the status fails validation."""

    loc = get_loc(evohome_v2)
    error = exc.BadApiResponseError(_ERR_MSG)

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(exc.InvalidStatusError) as err,
    ):
        await loc.get_status()

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
    zone: Zone,
    error: exc.EvohomeError,
    expected: type[exc.EvohomeError],
) -> None:
    """Test get_schedule() raises InvalidScheduleError only for a bad schedule."""

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=error)),
        pytest.raises(expected) as err,
    ):
        await zone.get_schedule()

    assert type(err.value) is expected


async def test_empty_schedule(
    zone: Zone,
) -> None:
    """Test an empty schedule is valid, and has no switchpoints."""

    with patch(
        "evohomeasync2.auth.Auth.get", AsyncMock(return_value={"daily_schedules": []})
    ):
        assert await zone.get_schedule() == []

    assert zone.schedule == []
    assert zone.this_switchpoint is None
    assert zone.next_switchpoint is None


async def test_invalid_schedule_not_stored(
    evohome_v2: EvohomeClient,
) -> None:
    """Test a schedule whose switchpoints can't be found is not stored.

    A zone keeps its earlier schedule & switchpoints (if any), else it still has none.
    """

    fetched = get_zon(evohome_v2)
    unfetched = get_zon(evohome_v2, 1)  # its schedule will not have been fetched
    assert fetched is not None  # the default/ fixture has 2+ zones
    assert unfetched is not None

    schedule = await fetched.get_schedule()
    switchpoints = (fetched.this_switchpoint, fetched.next_switchpoint)

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


async def test_set_schedule_before_get(
    evohome_v2: EvohomeClient,
) -> None:
    """Test the switchpoints are available after set_schedule(), without a get."""

    fetched = get_zon(evohome_v2)
    zone = get_zon(evohome_v2, 1)  # its schedule will not have been fetched
    assert fetched is not None  # the default/ fixture has 2+ zones
    assert zone is not None

    schedule = await fetched.get_schedule()

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


async def test_ghost_zone(
    zone: Zone,
) -> None:
    """Test a zone without a (known) model type raises GhostZoneError."""

    config = zone._config.copy()
    config[SZ_MODEL_TYPE] = ZoneModelType.UNKNOWN

    with pytest.raises(exc.GhostZoneError):
        Zone(zone.tcs, config)


async def test_ghost_zone_skipped(
    evohome_v2: EvohomeClient,
    tcs: ControlSystem,
) -> None:
    """Test a TCS skips a ghost zone, and only that zone."""

    assert evohome_v2._user_locs is not None  # mypy

    config = copy.deepcopy(
        evohome_v2._user_locs[TEST_LOC_IDX][SZ_GATEWAYS][0][
            SZ_TEMPERATURE_CONTROL_SYSTEMS
        ][0]
    )
    ghost = config[SZ_ZONES][1]
    ghost[SZ_MODEL_TYPE] = ZoneModelType.UNKNOWN

    new_tcs = ControlSystem(tcs.gateway, config)

    assert [z.id for z in new_tcs.zones] == [
        z.id for z in tcs.zones if z.id != ghost[SZ_ZONE_ID]
    ]
    assert len(new_tcs.zones) == len(tcs.zones) - 1


async def test_ghost_zone_other_errors(
    evohome_v2: EvohomeClient,
    tcs: ControlSystem,
) -> None:
    """Test a TCS skips only a GhostZoneError: any other InvalidConfigError is raised."""

    assert evohome_v2._user_locs is not None  # mypy

    config = evohome_v2._user_locs[TEST_LOC_IDX][SZ_GATEWAYS][0][
        SZ_TEMPERATURE_CONTROL_SYSTEMS
    ][0]
    error = exc.InvalidConfigError("Not a ghost zone")

    with (
        patch("evohomeasync2.control_system.Zone", side_effect=error),
        pytest.raises(exc.InvalidConfigError) as err,
    ):
        ControlSystem(tcs.gateway, config)

    assert err.value is error
