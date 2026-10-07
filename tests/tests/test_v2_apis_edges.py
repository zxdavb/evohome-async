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
from freezegun.api import FakeDatetime

import evohomeasync2 as evo2
from evohomeasync2 import CommTask, HotWater, Zone
from evohomeasync2.const import DhwState, SystemMode, ZoneMode

from .conftest import FIXTURES_V2 as FIXTURES
from .const import PUT_RESPONSE_V2

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import ControlSystem
    from evohomeasync2.auth import Auth


# Fixtures with old/new system modes to test fallback and error handling logic
_FIXTURES = ("default", "hass_118169")
# ...of which, those with a DHW (for the DHW tests, as hass_118169 has no DHW)
_FIXTURES_WITH_DHW = ("default",)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    names = (
        _FIXTURES_WITH_DHW
        if metafunc.function.__name__.startswith("test_dhw_")
        else _FIXTURES
    )
    folders = [Path(FIXTURES) / name for name in names]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_ctl_reset_emulates_auto_with_reset(
    auth: Auth,
    tcs: ControlSystem,
) -> None:
    """ControlSystem.reset() should emulate `AutoWithReset` if it is unavailable."""

    # each emulated PUT returns its own comm task, to check their order
    tcs_task = CommTask(auth, "1000000001")
    zon_tasks = [CommTask(auth, str(2000000001 + i)) for i in range(len(tcs.zones))]
    dhw_task = CommTask(auth, "3000000001")

    with (
        patch.object(
            Zone, "reset", new_callable=AsyncMock, side_effect=zon_tasks
        ) as mock_zone_reset,
        patch.object(
            HotWater, "reset", new_callable=AsyncMock, return_value=dhw_task
        ) as mock_dhw_reset,
        patch.object(
            tcs, "set_auto", new_callable=AsyncMock, return_value=tcs_task
        ) as mock_set_auto,
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
    ):
        tasks = await tcs.reset()

    if SystemMode.AUTO_WITH_RESET in tcs.allowed_modes:
        url = f"temperatureControlSystem/{tcs.id}/mode"
        mode = {
            "system_mode": SystemMode.AUTO_WITH_RESET,
            "permanent": True,
        }

        mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)
        mock_set_auto.assert_not_awaited()
        mock_zone_reset.assert_not_awaited()

        if tcs.hotwater is not None:
            mock_dhw_reset.assert_not_awaited()

        assert [t.id for t in tasks] == [PUT_RESPONSE_V2["id"]]

    else:
        mock_set_auto.assert_awaited_once()
        mock_put.assert_not_awaited()
        assert mock_zone_reset.await_count == len(tcs.zones)

        if tcs.hotwater is not None:
            mock_dhw_reset.assert_awaited_once()

        # the TCS's task, then each zone's, then the DHW's (if any)
        expected = [tcs_task, *zon_tasks] + ([dhw_task] if tcs.hotwater else [])
        assert tasks == expected


async def test_ctl_set_auto_falls_back_to_heat(
    tcs: ControlSystem,
) -> None:
    """ControlSystem.set_auto() should use `Heat` if `Auto` is unavailable."""

    expected_mode = (
        SystemMode.AUTO if SystemMode.AUTO in tcs.allowed_modes else SystemMode.HEAT
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "system_mode": expected_mode,
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_auto()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_heatingoff_falls_back_to_off(
    tcs: ControlSystem,
) -> None:
    """ControlSystem.set_heatingoff() should use `Off` if `HeatingOff` is unavailable."""

    expected_mode = (
        SystemMode.OFF
        if SystemMode.OFF in tcs.allowed_modes
        else SystemMode.HEATING_OFF
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "system_mode": expected_mode,
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_heatingoff()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_mode_rejects_unsupported_mode(
    tcs: ControlSystem,
) -> None:
    """ControlSystem.set_mode() should reject modes not supported by the current TCS."""

    for system_mode in SystemMode:
        if system_mode not in tcs.allowed_modes:
            break
    else:
        pytest.skip("TCS supports all system modes!")

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidSystemModeError),
    ):
        await tcs.set_mode(system_mode)

    mock_put.assert_not_awaited()


async def test_ctl_set_mode_rejects_until_for_non_temporary_mode(
    tcs: ControlSystem,
    freezer: FrozenDateTimeFactory,
) -> None:
    """ControlSystem.set_mode() should reject an until kwarg for non-temporary modes."""

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
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidSystemModeError),
    ):
        await tcs.set_mode(non_temporary, until=dt.now(tz=UTC) + td(days=1))

    mock_put.assert_not_awaited()


# Zone set_mode tests...


async def test_zon_set_mode_follow_schedule(
    zone: Zone,
) -> None:
    """Zone.set_mode(FollowSchedule) should PUT the correct payload."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode(ZoneMode.FOLLOW_SCHEDULE)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.FOLLOW_SCHEDULE,
        },
    )


async def test_zon_set_mode_permanent_override(
    zone: Zone,
) -> None:
    """Zone.set_mode(PermanentOverride) should PUT the correct payload."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode(ZoneMode.PERMANENT_OVERRIDE, temperature=20.0)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.PERMANENT_OVERRIDE,
            "heat_setpoint_value": 20.0,
        },
    )


async def test_zon_set_mode_temporary_override(
    zone: Zone,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zone.set_mode(TemporaryOverride) should PUT the correct payload."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE,
            temperature=21.5,
            until=dt.now(tz=UTC) + td(hours=3),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.TEMPORARY_OVERRIDE,
            "heat_setpoint_value": 21.5,
            "time_until": FakeDatetime(2025, 7, 10, 15, 0, tzinfo=UTC),
        },
    )


async def test_zon_set_mode_rejects_vacation_hold(
    zone: Zone,
) -> None:
    """Zone.set_mode(VacationHold) should raise when VacationHold is not supported."""

    if ZoneMode.VACATION_HOLD in zone.allowed_modes:
        pytest.skip("Zone supports VacationHold mode")

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(ZoneMode.VACATION_HOLD, temperature=20.0)

    mock_put.assert_not_awaited()


async def test_zon_set_mode_vacation_hold(
    zone: Zone,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zone.set_mode(VacationHold) should PUT the correct payload when supported."""

    if ZoneMode.VACATION_HOLD not in zone.allowed_modes:
        pytest.skip("Zone does not support VacationHold mode")

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode(
            ZoneMode.VACATION_HOLD,
            temperature=15.0,
            until=dt.now(tz=UTC) + td(days=7),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.VACATION_HOLD,
            "heat_setpoint_value": 15.0,
            "time_until": FakeDatetime(2025, 7, 17, 12, 0, tzinfo=UTC),
        },
    )


async def test_zon_set_mode_follow_schedule_rejects_extra_args(
    zone: Zone,
) -> None:
    """Zone.set_mode(FollowSchedule) should reject temperature or until arguments."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(ZoneMode.FOLLOW_SCHEDULE, temperature=20.0)

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(
            ZoneMode.FOLLOW_SCHEDULE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()


async def test_zon_set_mode_permanent_override_rejects_bad_args(
    zone: Zone,
) -> None:
    """Zone.set_mode(PermanentOverride) should reject missing temperature or extra until."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(ZoneMode.PERMANENT_OVERRIDE)

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(
            ZoneMode.PERMANENT_OVERRIDE,
            temperature=20.0,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


async def test_zon_set_mode_temporary_override_rejects_bad_args(
    zone: Zone,
) -> None:
    """Zone.set_mode(TemporaryOverride) should reject missing temperature or until."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(ZoneMode.TEMPORARY_OVERRIDE, temperature=20.0)

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await zone.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE,
            temperature=zone.max_heat_setpoint + 1.0,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


# HotWater set_mode tests...


async def test_dhw_set_mode_follow_schedule(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode(FollowSchedule) should PUT the correct payload."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_mode(ZoneMode.FOLLOW_SCHEDULE)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={
            "mode": ZoneMode.FOLLOW_SCHEDULE,
        },
    )


async def test_dhw_set_mode_permanent_override(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode(PermanentOverride) should PUT the correct payload."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_mode(ZoneMode.PERMANENT_OVERRIDE, state=DhwState.ON)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={
            "mode": ZoneMode.PERMANENT_OVERRIDE,
            "state": DhwState.ON,
        },
    )


async def test_dhw_set_mode_temporary_override(
    dhw: HotWater,
    freezer: FrozenDateTimeFactory,
) -> None:
    """HotWater.set_mode(TemporaryOverride) should PUT the correct payload."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE,
            state=DhwState.OFF,
            until=dt.now(tz=UTC) + td(hours=3),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={
            "mode": ZoneMode.TEMPORARY_OVERRIDE,
            "state": DhwState.OFF,
            "until_time": FakeDatetime(2025, 7, 10, 15, 0, tzinfo=UTC),
        },
    )


async def test_dhw_set_mode_rejects_unsupported_mode(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode() should reject modes not supported by this DHW."""

    for mode in ZoneMode:
        if mode not in dhw.allowed_modes:
            break
    else:
        pytest.skip("DHW supports all zone modes!")

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(mode)

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_follow_schedule_rejects_extra_args(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode(FollowSchedule) should reject state or until arguments."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(ZoneMode.FOLLOW_SCHEDULE, state=DhwState.ON)

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(ZoneMode.FOLLOW_SCHEDULE, until=dt.now(tz=UTC) + td(hours=1))

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_permanent_override_rejects_bad_args(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode(PermanentOverride) should reject missing state or extra until."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(ZoneMode.PERMANENT_OVERRIDE)

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(
            ZoneMode.PERMANENT_OVERRIDE,
            state=DhwState.ON,
            until=dt.now(tz=UTC) + td(hours=1),
        )

    mock_put.assert_not_awaited()


async def test_dhw_set_mode_temporary_override_rejects_bad_args(
    dhw: HotWater,
) -> None:
    """HotWater.set_mode(TemporaryOverride) should reject missing state or until."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE, until=dt.now(tz=UTC) + td(hours=1)
        )

    mock_put.assert_not_awaited()

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(evo2.InvalidModeRequestError),
    ):
        await dhw.set_mode(ZoneMode.TEMPORARY_OVERRIDE, state=DhwState.OFF)

    mock_put.assert_not_awaited()
