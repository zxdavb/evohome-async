"""Test the v2 methods that set the mode of a TCS, DHW or zone."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from freezegun.api import FakeDatetime

from evohomeasync2 import BadApiRequestError, InvalidModeRequestError
from evohomeasync2.const import DhwState, SystemMode, TimingMode, ZoneMode

from .conftest import FIXTURES_V2 as FIXTURES
from .const import PUT_RESPONSE_V2

if TYPE_CHECKING:
    from typing import Any, TypedDict

    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import ControlSystem, HotWater, Zone
    from evohomeasync2.typedefs import EvoAllowedSystemModesT

    class _SetZoneTimeT(TypedDict, total=False):  # the set time of a set_mode()
        duration: td


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and p.name == "default"
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


# Test the ControlSystem APIs (incomplete)...
# NOTE: not all systems support all modes, below we only test evohome modes


async def test_ctl_reset(
    tcs: ControlSystem,
) -> None:
    """Test ControlSystem.reset() method."""

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "system_mode": SystemMode.AUTO_WITH_RESET,
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.reset()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


CTL_APIS_SANS_UNTIL = {  # system mode APIs that can not take an until kwarg
    "set_auto": SystemMode.AUTO,
    "set_heatingoff": SystemMode.HEATING_OFF,
}


@pytest.mark.parametrize("api_name", CTL_APIS_SANS_UNTIL)
async def test_ctl_set_mode_sans_until(
    tcs: ControlSystem,
    api_name: str,
) -> None:
    """Test ControlSystem.set_auto() method."""

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "system_mode": CTL_APIS_SANS_UNTIL[api_name],
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await getattr(tcs, api_name)()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.raises(TypeError),  # got an unexpected keyword argument 'until'
    ):
        await getattr(tcs, api_name)(until=dt.now(tz=UTC) + td(days=3))


CTL_APIS_WITH_UNTIL = {  # system mode APIs that can take an until kwarg
    "set_away": SystemMode.AWAY,
    "set_custom": SystemMode.CUSTOM,
    "set_dayoff": SystemMode.DAY_OFF,
    "set_eco": SystemMode.AUTO_WITH_ECO,
}


@pytest.mark.parametrize("api_name", CTL_APIS_WITH_UNTIL)
async def test_ctl_set_mode_with_until(
    tcs: ControlSystem,
    api_name: str,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test ControlSystem.set_*() methods (that can take an until kwarg)."""

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "system_mode": CTL_APIS_WITH_UNTIL[api_name],
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await getattr(tcs, api_name)()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)

    freezer.move_to("2025-07-10T12:00:00Z")

    mode = {
        "system_mode": CTL_APIS_WITH_UNTIL[api_name],
        "permanent": False,
        "time_until": FakeDatetime(2025, 7, 13, 12, 0, tzinfo=UTC),
    }

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await getattr(tcs, api_name)(until=dt.now(tz=UTC) + td(days=3))

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


# Test the HotWater APIs...


async def test_dhw_set_off(
    dhw: HotWater,
) -> None:
    """Test HotWater.set_off() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_off()

    EXPECTED_JSON = {
        "mode": ZoneMode.PERMANENT_OVERRIDE,
        "state": DhwState.OFF,
    }

    mock_put.assert_awaited_once()

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_dhw_set_on(
    dhw: HotWater,
) -> None:
    """Test HotWater.set_on() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_on()

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "mode": ZoneMode.PERMANENT_OVERRIDE,
        "state": DhwState.ON,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_dhw_reset(
    dhw: HotWater,
) -> None:
    """Test HotWater.reset() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.reset()

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "mode": ZoneMode.FOLLOW_SCHEDULE,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_dhw_set_state(
    dhw: HotWater,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test HotWater.set_state() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_state(DhwState.OFF)

    mock_put.assert_awaited_once()

    EXPECTED_JSON: dict[str, dt | str] = {
        "mode": ZoneMode.PERMANENT_OVERRIDE,
        "state": DhwState.OFF,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_state(DhwState.ON, until=dt.now(tz=UTC) + td(hours=3))

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "mode": ZoneMode.TEMPORARY_OVERRIDE,
        "state": DhwState.ON,
        "until_time": FakeDatetime(2025, 7, 10, 15, 0, tzinfo=UTC),
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


# Test the Zone APIs...


async def test_zon_reset(
    zone: Zone,
) -> None:
    """Test Zone.reset() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.reset()

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "setpoint_mode": ZoneMode.FOLLOW_SCHEDULE,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_zon_set_temperature(
    zone: Zone,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test Zone.set_temperature() method."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_temperature(19.5)

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "setpoint_mode": ZoneMode.PERMANENT_OVERRIDE,
        "heat_setpoint_value": 19.5,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_temperature(20.5, until=dt.now(tz=UTC) + td(hours=1))

    mock_put.assert_awaited_once()

    EXPECTED_JSON = {
        "setpoint_mode": ZoneMode.TEMPORARY_OVERRIDE,
        "heat_setpoint_value": 20.5,
        "time_until": FakeDatetime(2025, 7, 10, 13, 0, tzinfo=UTC),
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


# Test input flexibility (accept str/StrEnum mode/state, dt|str until, reject naive)...


async def test_ctl_set_mode_accepts_str_mode(
    tcs: ControlSystem,
) -> None:
    """A snake_case string mode is accepted (and coerced to the StrEnum)."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_mode("away")  # instead of SystemMode.AWAY

    EXPECTED_JSON = {"system_mode": SystemMode.AWAY, "permanent": True}

    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_dhw_set_state_accepts_str_inputs(
    dhw: HotWater,
) -> None:
    """A string state and an ISO-string until are accepted and normalised."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_state(
            "on", until="2025-07-13T12:00:00Z"
        )  # instead of DhwState.ON

    EXPECTED_JSON = {
        "mode": ZoneMode.TEMPORARY_OVERRIDE,
        "state": DhwState.ON,
        "until_time": dt(2025, 7, 13, 12, 0, tzinfo=UTC),
    }

    assert mock_put.call_args[1] == {"json": EXPECTED_JSON}


async def test_set_mode_rejects_naive_until(
    tcs: ControlSystem,
) -> None:
    """A naive (TZ-unaware) until is rejected before any request is made."""

    naive = dt.fromisoformat("2025-07-13T12:00:00")  # no offset

    with pytest.raises(BadApiRequestError):
        await tcs.set_away(until=naive)


# Test ControlSystem.set_mode() (with a duration/period, rather than an until)...


@pytest.mark.parametrize(
    ("system_mode", "kwargs", "now_until"),
    [
        pytest.param(
            SystemMode.AUTO_WITH_ECO,
            {"duration": td(hours=2)},
            ("2025-07-10T12:00:00Z", dt(2025, 7, 10, 14, 0, tzinfo=UTC)),
            id="duration",
        ),
        pytest.param(  # midnight BST (UTC+1) is 23:00 UTC
            SystemMode.AWAY,
            {"period": td(days=3)},
            ("2025-07-10T12:00:00Z", dt(2025, 7, 12, 23, 0, tzinfo=UTC)),
            id="period",
        ),
        pytest.param(  # the clocks go back (BST -> GMT) on 2025-10-26
            SystemMode.DAY_OFF,
            {"period": td(days=2)},
            ("2025-10-25T12:00:00Z", dt(2025, 10, 27, 0, 0, tzinfo=UTC)),
            id="period_over_dst",
        ),
        pytest.param(  # 01:30 BST + 1h is 01:30 GMT (the clocks go back at 02:00 BST)
            SystemMode.AUTO_WITH_ECO,
            {"duration": td(hours=1)},
            ("2025-10-26T00:30:00Z", dt(2025, 10, 26, 1, 30, tzinfo=UTC)),
            id="duration_over_dst_end",
        ),
        pytest.param(  # 00:30 GMT + 2h is 03:30 BST (the clocks go forward at 01:00 GMT)
            SystemMode.AUTO_WITH_ECO,
            {"duration": td(hours=2)},
            ("2025-03-30T00:30:00Z", dt(2025, 3, 30, 2, 30, tzinfo=UTC)),
            id="duration_over_dst_start",
        ),
        pytest.param(  # the maximum duration is allowed
            SystemMode.AUTO_WITH_ECO,
            {"duration": td(days=1)},
            ("2025-07-10T12:00:00Z", dt(2025, 7, 11, 12, 0, tzinfo=UTC)),
            id="duration_max",
        ),
        pytest.param(  # the maximum period is allowed (midnight BST is 23:00 UTC)
            SystemMode.AWAY,
            {"period": td(days=99)},
            ("2025-07-10T12:00:00Z", dt(2025, 10, 16, 23, 0, tzinfo=UTC)),
            id="period_max",
        ),
    ],
)
async def test_ctl_set_mode_temporary(
    tcs: ControlSystem,
    freezer: FrozenDateTimeFactory,
    system_mode: SystemMode,
    kwargs: dict[str, Any],  # some of these are rejected by the overloads
    now_until: tuple[str, dt],
) -> None:
    """Test set_mode() ends a duration from now, and a period from midnight."""

    now, expected = now_until
    freezer.move_to(now)

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_mode(system_mode, **kwargs)

    json = mock_put.call_args[1]["json"]

    assert json["system_mode"] == system_mode
    assert json["permanent"] is False
    assert json["time_until"] == expected  # the same instant, whatever its TZ


async def test_ctl_set_mode_permanent(
    tcs: ControlSystem,
) -> None:
    """Test set_mode() without a duration/period sets the mode indefinitely."""

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {"system_mode": SystemMode.AWAY, "permanent": True}

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_mode("away")

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_mode_not_permanent(
    tcs: ControlSystem,
) -> None:
    """Test set_mode() rejects a mode that can't be permanent, sans duration/period."""

    # no known system has such a mode, so this one is made up
    mode_entry: EvoAllowedSystemModesT = {
        "system_mode": SystemMode.AUTO_WITH_ECO,
        "can_be_permanent": False,
        "can_be_temporary": True,
        "max_duration": "1.00:00:00",
        "timing_resolution": "01:00:00",
        "timing_mode": TimingMode.DURATION,
    }

    with (
        patch.object(
            type(tcs),
            "allowed_system_modes",
            new_callable=PropertyMock,
            return_value=(mode_entry,),
        ),
        pytest.raises(InvalidModeRequestError, match="duration must not be None"),
    ):
        await tcs.set_mode(SystemMode.AUTO_WITH_ECO)


@pytest.mark.parametrize(
    ("system_mode", "kwargs"),
    [
        pytest.param("no_such_mode", {}, id="unknown_mode"),
        pytest.param(SystemMode.HEAT, {}, id="unsupported_mode"),
        pytest.param(
            SystemMode.AWAY,
            {"duration": td(hours=1), "period": td(days=1)},
            id="duration_and_period",
        ),
        pytest.param(SystemMode.AUTO, {"duration": td(hours=1)}, id="not_temporary"),
        pytest.param(SystemMode.AWAY, {"duration": td(hours=1)}, id="period_only"),
        pytest.param(SystemMode.AUTO_WITH_ECO, {"period": td(days=1)}, id="dur_only"),
        pytest.param(SystemMode.AUTO_WITH_ECO, {"duration": td(0)}, id="dur_zero"),
        pytest.param(
            SystemMode.AUTO_WITH_ECO, {"duration": td(hours=-1)}, id="dur_negative"
        ),
        pytest.param(  # max_duration is "1.00:00:00"
            SystemMode.AUTO_WITH_ECO, {"duration": td(hours=25)}, id="dur_too_long"
        ),
        pytest.param(SystemMode.AWAY, {"period": td(0)}, id="period_zero"),
        pytest.param(SystemMode.AWAY, {"period": td(hours=12)}, id="period_too_short"),
        pytest.param(  # max_duration is "99.00:00:00"
            SystemMode.AWAY, {"period": td(days=100)}, id="period_too_long"
        ),
        pytest.param(  # timing_resolution is "01:00:00"
            SystemMode.AUTO_WITH_ECO, {"duration": td(minutes=90)}, id="dur_resolution"
        ),
        pytest.param(  # timing_resolution is "1.00:00:00"
            SystemMode.AWAY, {"period": td(days=1, hours=6)}, id="period_resolution"
        ),
    ],
)
async def test_ctl_set_mode_rejects(
    tcs: ControlSystem,
    system_mode: SystemMode | str,
    kwargs: dict[str, Any],  # some of these are rejected by the overloads
) -> None:
    """Test set_mode() rejects an invalid request before any PUT is made."""

    with pytest.raises(InvalidModeRequestError):
        await tcs.set_mode(system_mode, **kwargs)


async def test_ctl_set_system_mode_is_deprecated(
    tcs: ControlSystem,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test set_system_mode() warns, and still sets the mode."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=PUT_RESPONSE_V2,
        ) as mock_put,
        pytest.warns(DeprecationWarning, match=r"use \.set_mode\(\)"),
    ):
        await tcs.set_system_mode(SystemMode.AUTO_WITH_ECO, duration=td(hours=2))

    json = mock_put.call_args[1]["json"]

    assert json["system_mode"] == SystemMode.AUTO_WITH_ECO
    assert json["permanent"] is False
    assert json["time_until"] == dt(2025, 7, 10, 14, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param(
            {"until": dt(2025, 7, 11, tzinfo=UTC), "duration": td(hours=1)},
            id="duration",
        ),
        pytest.param(
            {"until": dt(2025, 7, 11, tzinfo=UTC), "period": td(days=1)}, id="period"
        ),
    ],
)
async def test_ctl_set_mode_rejects_until_and_timespan(
    tcs: ControlSystem,
    kwargs: dict[str, Any],  # some of these are rejected by the overloads
) -> None:
    """Test set_mode() rejects an until with a duration/period, before any PUT is made."""

    with pytest.raises(InvalidModeRequestError, match="Only one of until"):
        await tcs.set_mode(SystemMode.AWAY, **kwargs)


async def test_ctl_set_mode_does_not_limit_until(
    tcs: ControlSystem,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test set_mode() limits a duration by the max_duration, but not an until."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await tcs.set_mode(
            SystemMode.AUTO_WITH_ECO, until=dt.now(tz=UTC) + td(hours=25)
        )

    json = mock_put.call_args[1]["json"]

    assert json["permanent"] is False
    assert json["time_until"] == dt(2025, 7, 11, 13, 0, tzinfo=UTC)


# Test Zone/HotWater.set_mode() (with a duration, rather than an until)...


async def test_zon_set_mode_with_duration(
    zone: Zone,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a zone's duration ends that long from now (as a TemporaryOverride)."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE,
            temperature=20.5,
            duration=td(hours=1, minutes=30),
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.TEMPORARY_OVERRIDE,
            "heat_setpoint_value": 20.5,
            "time_until": dt(2025, 7, 10, 13, 30, tzinfo=UTC),
        },
    )


async def test_dhw_set_mode_with_duration(
    dhw: HotWater,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a DHW's duration ends that long from now (as a TemporaryOverride)."""

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_mode(
            ZoneMode.TEMPORARY_OVERRIDE, state=DhwState.ON, duration=td(hours=2)
        )

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={
            "mode": ZoneMode.TEMPORARY_OVERRIDE,
            "state": DhwState.ON,
            "until_time": dt(2025, 7, 10, 14, 0, tzinfo=UTC),
        },
    )


# the zone's and the DHW's max_duration is "1.00:00:00", timing_resolution "00:10:00"
_MUST_BE_NONE = "duration must be None, not '1:00:00'"
_MULTIPLE_OF = "must be a multiple of"

DURATION_REJECTS = [
    pytest.param(
        ZoneMode.FOLLOW_SCHEDULE, {"duration": td(hours=1)}, _MUST_BE_NONE, id="follow"
    ),
    pytest.param(
        ZoneMode.PERMANENT_OVERRIDE, {"duration": td(hours=1)}, _MUST_BE_NONE, id="perm"
    ),
    pytest.param(
        ZoneMode.TEMPORARY_OVERRIDE, {}, "duration must not be None", id="temp"
    ),
    pytest.param(
        ZoneMode.TEMPORARY_OVERRIDE, {"duration": td(0)}, _MULTIPLE_OF, id="zero"
    ),
    pytest.param(
        ZoneMode.TEMPORARY_OVERRIDE, {"duration": td(hours=-1)}, _MULTIPLE_OF, id="neg"
    ),
    pytest.param(
        ZoneMode.TEMPORARY_OVERRIDE, {"duration": td(hours=25)}, _MULTIPLE_OF, id="long"
    ),
    pytest.param(
        ZoneMode.TEMPORARY_OVERRIDE,
        {"duration": td(minutes=15)},
        _MULTIPLE_OF,
        id="resolution",
    ),
    pytest.param(  # not allowed here (if it were: "use until", see edges tests)
        ZoneMode.VACATION_HOLD, {"duration": td(days=7)}, "Unsupported mode", id="vac"
    ),
]


@pytest.mark.parametrize(("mode", "kwargs", "match"), DURATION_REJECTS)
async def test_zon_set_mode_rejects_duration(
    zone: Zone,
    mode: ZoneMode,
    kwargs: _SetZoneTimeT,
    match: str,
) -> None:
    """Test a zone's set_mode() rejects an invalid duration before any PUT is made."""

    temperature = None if mode is ZoneMode.FOLLOW_SCHEDULE else 20.0

    with pytest.raises(InvalidModeRequestError, match=match):
        await zone.set_mode(mode, temperature=temperature, **kwargs)


@pytest.mark.parametrize(("mode", "kwargs", "match"), DURATION_REJECTS)
async def test_dhw_set_mode_rejects_duration(
    dhw: HotWater,
    mode: ZoneMode,
    kwargs: _SetZoneTimeT,
    match: str,
) -> None:
    """Test a DHW's set_mode() rejects an invalid duration before any PUT is made."""

    state = None if mode is ZoneMode.FOLLOW_SCHEDULE else DhwState.ON

    with pytest.raises(InvalidModeRequestError, match=match):
        await dhw.set_mode(mode, state=state, **kwargs)


@pytest.mark.parametrize(
    ("mode", "temperature", "match"),
    [
        pytest.param(
            ZoneMode.FOLLOW_SCHEDULE,
            20.0,
            "temperature must be None, not '20.0'",
            id="follow",
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE,
            None,
            "temperature must not be None",
            id="missing",
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE, 99.0, "out of range", id="out_of_range"
        ),
    ],
)
async def test_zon_set_mode_rejects_temperature(
    zone: Zone,
    mode: ZoneMode,
    temperature: float | None,
    match: str,
) -> None:
    """Test a zone's set_mode() rejects an invalid temperature before any PUT."""

    with pytest.raises(InvalidModeRequestError, match=match):
        await zone.set_mode(mode, temperature=temperature)


@pytest.mark.parametrize(
    ("mode", "state", "match"),
    [
        pytest.param(
            ZoneMode.FOLLOW_SCHEDULE,
            DhwState.ON,
            "state must be None, not 'on'",
            id="follow",
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE, None, "state must not be None", id="missing"
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE, "invalid", "Unknown state", id="unknown"
        ),
    ],
)
async def test_dhw_set_mode_rejects_state(
    dhw: HotWater,
    mode: ZoneMode,
    state: DhwState | str | None,
    match: str,
) -> None:
    """Test a DHW's set_mode() rejects an invalid state before any PUT is made."""

    with pytest.raises(InvalidModeRequestError, match=match):
        await dhw.set_mode(mode, state=state)


async def test_dhw_set_mode_rejects_unsupported_state(
    dhw: HotWater,
) -> None:
    """Test a DHW's set_mode() rejects a state that is not in its allowed_states."""

    with (
        patch.object(
            type(dhw),
            "allowed_states",
            new_callable=PropertyMock,
            return_value=(DhwState.OFF,),
        ),
        pytest.raises(InvalidModeRequestError, match="Unsupported state: on"),
    ):
        await dhw.set_mode(ZoneMode.PERMANENT_OVERRIDE, state=DhwState.ON)


async def test_zon_set_mode_accepts_strings(
    zone: Zone,
) -> None:
    """Test a zone's set_mode() PUTs a string mode as a ZoneMode, indefinitely."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await zone.set_mode("permanent_override", temperature=20.5)

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"temperatureZone/{zone.id}/heatSetpoint",
        json={
            "setpoint_mode": ZoneMode.PERMANENT_OVERRIDE,
            "heat_setpoint_value": 20.5,
        },
    )


async def test_dhw_set_mode_accepts_strings(
    dhw: HotWater,
) -> None:
    """Test a DHW's set_mode() PUTs string mode/state as enums, indefinitely."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_put:
        await dhw.set_mode("permanent_override", state="on")

    mock_put.assert_awaited_once_with(
        HTTPMethod.PUT,
        f"domesticHotWater/{dhw.id}/state",
        json={"mode": ZoneMode.PERMANENT_OVERRIDE, "state": DhwState.ON},
    )


async def test_zon_set_mode_rejects_until_and_duration(
    zone: Zone,
) -> None:
    """Test a zone's set_mode() rejects an until with a duration, before any PUT."""

    kwargs: dict[str, Any] = {"until": dt.now(tz=UTC), "duration": td(hours=1)}

    with pytest.raises(InvalidModeRequestError, match="Only one of until or duration"):
        await zone.set_mode(ZoneMode.TEMPORARY_OVERRIDE, temperature=20.0, **kwargs)


async def test_dhw_set_mode_rejects_until_and_duration(
    dhw: HotWater,
) -> None:
    """Test a DHW's set_mode() rejects an until with a duration, before any PUT."""

    kwargs: dict[str, Any] = {"until": dt.now(tz=UTC), "duration": td(hours=1)}

    with pytest.raises(InvalidModeRequestError, match="Only one of until or duration"):
        await dhw.set_mode(ZoneMode.TEMPORARY_OVERRIDE, state=DhwState.ON, **kwargs)
