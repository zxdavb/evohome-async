"""Tests for evohome-async - ControlSystem/Zone/HotWater mode edge cases.

Older systems do not support all system modes, and some modes have been renamed in
newer systems. These tests check that the client handles these cases correctly, falling
back to appropriate alternatives where possible and raising errors where not.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

import evohomeasync2 as evo2
from evohomeasync2 import HotWater, Zone
from evohomeasync2.schemas import DhwStateEnum, ZoneModeEnum
from evohomeasync2.schemas.const import SystemModeEnum

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import EvohomeClient


# Fixtures with old/new system modes to test fallback and error handling logic
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [Path(FIXTURES) / name for name in ("default", "hass_118169")]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_ctl_reset_emulates_auto_with_reset(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.reset() should emulate `AutoWithReset` if it is unavailable."""

    tcs = evohome_v2.tcs

    with (
        patch.object(Zone, "reset", new_callable=AsyncMock) as mock_zone_reset,
        patch.object(HotWater, "reset", new_callable=AsyncMock) as mock_dhw_reset,
        patch.object(tcs, "set_auto", new_callable=AsyncMock) as mock_set_auto,
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
    ):
        await tcs.reset()

    if SystemModeEnum.AUTO_WITH_RESET in tcs.allowed_modes:
        url = f"temperatureControlSystem/{tcs.id}/mode"
        mode = {
            "systemMode": str(SystemModeEnum.AUTO_WITH_RESET),
            "permanent": True,
        }

        mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)
        mock_set_auto.assert_not_awaited()
        mock_zone_reset.assert_not_awaited()

        if tcs.hotwater is not None:
            mock_dhw_reset.assert_not_awaited()

    else:
        mock_set_auto.assert_awaited_once()
        mock_put.assert_not_awaited()
        assert mock_zone_reset.await_count == len(tcs.zones)

        if tcs.hotwater is not None:
            mock_dhw_reset.assert_awaited_once()


async def test_ctl_set_auto_falls_back_to_heat(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_auto() should use `Heat` if `Auto` is unavailable."""

    tcs = evohome_v2.tcs

    expected_mode = (
        SystemModeEnum.AUTO
        if SystemModeEnum.AUTO in tcs.allowed_modes
        else SystemModeEnum.HEAT
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": str(expected_mode),
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await tcs.set_auto()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_heatingoff_falls_back_to_off(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_heatingoff() should use `Off` if `HeatingOff` is unavailable."""

    tcs = evohome_v2.tcs

    expected_mode = (
        SystemModeEnum.OFF
        if SystemModeEnum.OFF in tcs.allowed_modes
        else SystemModeEnum.HEATING_OFF
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": str(expected_mode),
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await tcs.set_heatingoff()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_mode_rejects_unsupported_mode(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_mode() should reject modes not supported by the current TCS."""

    tcs = evohome_v2.tcs

    for system_mode in SystemModeEnum:
        if system_mode not in tcs.allowed_modes:
            break
    else:
        pytest.skip("TCS supports all system modes!")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidSystemModeError),
    ):
        await tcs.set_mode(system_mode)

    mock_put.assert_not_awaited()


async def test_ctl_set_mode_rejects_until_for_non_temporary_mode(
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """ControlSystem.set_mode() should reject an until kwarg for non-temporary modes."""

    tcs = evohome_v2.tcs

    non_temporary = next(
        (
            d["system_mode"]
            for d in tcs.allowed_system_modes
            if not d["can_be_temporary"]
        ),
        None,
    )
    if non_temporary is None:
        pytest.skip("All TCS modes support temporary duration")

    freezer.move_to("2025-07-10T12:00:00Z")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidSystemModeError),
    ):
        await tcs.set_mode(non_temporary, until=dt.now(tz=UTC) + td(days=1))

    mock_put.assert_not_awaited()


# Zone set_mode tests...


async def test_zon_set_mode_follow_schedule(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(FollowSchedule) should PUT the correct payload."""

    zone = evohome_v2.tcs.zones[0]

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await zone.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={"setpointMode": "FollowSchedule"},
    )


async def test_zon_set_mode_permanent_override(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(PermanentOverride) should PUT the correct payload."""

    zone = evohome_v2.tcs.zones[0]

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await zone.set_mode(ZoneModeEnum.PERMANENT_OVERRIDE, temperature=20.0)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={"setpointMode": "PermanentOverride", "heatSetpointValue": 20.0},
    )


async def test_zon_set_mode_temporary_override(
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zone.set_mode(TemporaryOverride) should PUT the correct payload."""

    zone = evohome_v2.tcs.zones[0]

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await zone.set_mode(
            ZoneModeEnum.TEMPORARY_OVERRIDE,
            temperature=21.5,
            until=dt.now(tz=UTC) + td(hours=3),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpointMode": "TemporaryOverride",
            "heatSetpointValue": 21.5,
            "timeUntil": "2025-07-10T15:00:00Z",
        },
    )


async def test_zon_set_mode_rejects_vacation_hold(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(VacationHold) should raise when VacationHold is not supported."""

    zone = evohome_v2.tcs.zones[0]

    if ZoneModeEnum.VACATION_HOLD in zone.allowed_modes:
        pytest.skip("Zone supports VacationHold mode")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(ZoneModeEnum.VACATION_HOLD, temperature=20.0)

    mock_put.assert_not_awaited()


async def test_zon_set_mode_vacation_hold(
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zone.set_mode(VacationHold) should PUT the correct payload when supported."""

    zone = evohome_v2.tcs.zones[0]

    if ZoneModeEnum.VACATION_HOLD not in zone.allowed_modes:
        pytest.skip("Zone does not support VacationHold mode")

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await zone.set_mode(
            ZoneModeEnum.VACATION_HOLD,
            temperature=15.0,
            until=dt.now(tz=UTC) + td(days=7),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpointMode": "VacationHold",
            "heatSetpointValue": 15.0,
            "timeUntil": "2025-07-17T12:00:00Z",
        },
    )


async def test_zon_set_mode_follow_schedule_rejects_extra_args(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(FollowSchedule) should reject temperature or until arguments."""

    zone = evohome_v2.tcs.zones[0]

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE, temperature=20.0)

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(
            ZoneModeEnum.FOLLOW_SCHEDULE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()


async def test_zon_set_mode_permanent_override_rejects_bad_args(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(PermanentOverride) should reject missing temperature or extra until."""

    zone = evohome_v2.tcs.zones[0]

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(ZoneModeEnum.PERMANENT_OVERRIDE)

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(
            ZoneModeEnum.PERMANENT_OVERRIDE,
            temperature=20.0,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


async def test_zon_set_mode_temporary_override_rejects_bad_args(
    evohome_v2: EvohomeClient,
) -> None:
    """Zone.set_mode(TemporaryOverride) should reject missing temperature or until."""

    zone = evohome_v2.tcs.zones[0]

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(
            ZoneModeEnum.TEMPORARY_OVERRIDE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(ZoneModeEnum.TEMPORARY_OVERRIDE, temperature=20.0)

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidZoneModeError),
    ):
        await zone.set_mode(
            ZoneModeEnum.TEMPORARY_OVERRIDE,
            temperature=zone.max_heat_setpoint + 1.0,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


# HotWater set_mode tests...


async def test_dhw_set_mode_follow_schedule(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode(FollowSchedule) should PUT the correct payload."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await dhw.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={"mode": "FollowSchedule"},
    )


async def test_dhw_set_mode_permanent_override(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode(PermanentOverride) should PUT the correct payload."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await dhw.set_mode(ZoneModeEnum.PERMANENT_OVERRIDE, state=DhwStateEnum.ON)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={"mode": "PermanentOverride", "state": "On"},
    )


async def test_dhw_set_mode_temporary_override(
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """HotWater.set_mode(TemporaryOverride) should PUT the correct payload."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await dhw.set_mode(
            ZoneModeEnum.TEMPORARY_OVERRIDE,
            state=DhwStateEnum.OFF,
            until=dt.now(tz=UTC) + td(hours=3),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={
            "mode": "TemporaryOverride",
            "state": "Off",
            "untilTime": "2025-07-10T15:00:00Z",
        },
    )


async def test_dhw_set_mode_rejects_unsupported_mode(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode() should reject modes not supported by this DHW."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    for mode in ZoneModeEnum:
        if mode not in dhw.allowed_modes:
            break
    else:
        pytest.skip("DHW supports all zone modes!")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(mode)

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_follow_schedule_rejects_extra_args(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode(FollowSchedule) should reject state or until arguments."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE, state=DhwStateEnum.ON)

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(
            ZoneModeEnum.FOLLOW_SCHEDULE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_permanent_override_rejects_bad_args(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode(PermanentOverride) should reject missing state or extra until."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(ZoneModeEnum.PERMANENT_OVERRIDE)

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(
            ZoneModeEnum.PERMANENT_OVERRIDE,
            state=DhwStateEnum.ON,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_temporary_override_rejects_bad_args(
    evohome_v2: EvohomeClient,
) -> None:
    """HotWater.set_mode(TemporaryOverride) should reject missing state or until."""

    dhw = evohome_v2.tcs.hotwater
    if dhw is None:
        pytest.skip("No DHW in this fixture")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(
            ZoneModeEnum.TEMPORARY_OVERRIDE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidDhwModeError),
    ):
        await dhw.set_mode(ZoneModeEnum.TEMPORARY_OVERRIDE, state=DhwStateEnum.OFF)

    mock_put.assert_not_awaited()
