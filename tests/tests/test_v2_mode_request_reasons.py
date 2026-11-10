"""Test the reason (and details) of each InvalidModeRequestError, by its raise site.

The reasons are public API (e.g. HA maps each one to its own translated message), so
each raise site is tested, as is that each reason is raised by at least one site.
"""

from __future__ import annotations

import math
from contextlib import nullcontext
from datetime import UTC, datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from evohomeasync2 import InvalidModeRequestError, RequestErrorReason as Reason
from evohomeasync2.const import DhwState, SystemMode, ZoneMode

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync2 import ControlSystem, HotWater, Zone


class _Call(NamedTuple):
    """A call of an entity's method that sets its mode."""

    entity: str  # the name of the entity's fixture: tcs, zone or dhw
    mode: str  # a SystemMode/ZoneMode, or a string that is neither
    kwargs: dict[str, Any]  # some of these are rejected by the overloads
    method: str = "set_mode"


_PAST = dt(2020, 1, 1, tzinfo=UTC)
_FUTURE = dt.now(tz=UTC) + td(days=1)  # the tests take far less than a day
_NAIVE = dt.fromisoformat("2030-01-01T00:00:00")  # no offset

_AUTO = SystemMode.AUTO
_ECO = SystemMode.AUTO_WITH_ECO
_AWAY = SystemMode.AWAY
_FOLLOW = ZoneMode.FOLLOW_SCHEDULE
_PERM = ZoneMode.PERMANENT_OVERRIDE
_TEMP = ZoneMode.TEMPORARY_OVERRIDE

_ON = DhwState.ON

# the default fixture's TCS allows: HeatingOff, Auto, AutoWithReset (all permanent
# only), AutoWithEco (a duration), Away, DayOff & Custom (a period); its zone/DHW allow
# FollowSchedule, PermanentOverride & TemporaryOverride (a duration)
CASES = [
    # the mode itself
    pytest.param(
        _Call("tcs", "no_such_mode", {}),
        Reason.MODE_UNKNOWN,
        {"mode": "no_such_mode"},
        id="tcs-mode_unknown",
    ),
    pytest.param(
        _Call("zone", "no_such_mode", {}),
        Reason.MODE_UNKNOWN,
        {"mode": "no_such_mode"},
        id="zon-mode_unknown",
    ),
    pytest.param(
        _Call("tcs", SystemMode.HEAT, {}),
        Reason.MODE_UNSUPPORTED,
        {"mode": "heat"},
        id="tcs-mode_unsupported",
    ),
    pytest.param(
        _Call("zone", ZoneMode.VACATION_HOLD, {}),
        Reason.MODE_UNSUPPORTED,
        {"mode": "vacation_hold"},
        id="zon-mode_unsupported",
    ),
    #
    # the timespan, given more than one way (e.g. an until and a duration)
    pytest.param(
        _Call("tcs", _ECO, {"until": _FUTURE, "duration": td(hours=1)}),
        Reason.TIMESPAN_CONFLICTING,
        {},
        id="tcs-timespan_conflicting-until",
    ),
    pytest.param(
        _Call("tcs", _AWAY, {"duration": td(hours=1), "period": td(days=1)}),
        Reason.TIMESPAN_CONFLICTING,
        {},
        id="tcs-timespan_conflicting-duration",
    ),
    pytest.param(
        _Call(
            "zone", _TEMP, {"temperature": 20.0, "until": _FUTURE, "duration": td(1)}
        ),
        Reason.TIMESPAN_CONFLICTING,
        {},
        id="zon-timespan_conflicting",
    ),
    pytest.param(
        _Call("dhw", _TEMP, {"state": _ON, "until": _FUTURE, "duration": td(1)}),
        Reason.TIMESPAN_CONFLICTING,
        {},
        id="dhw-timespan_conflicting",
    ),
    #
    # the timespan (an until, duration or period)
    pytest.param(
        _Call("zone", _TEMP, {"temperature": 20.0}),
        Reason.TIMESPAN_REQUIRED,
        {"mode": "temporary_override", "timing_mode": "duration"},
        id="zon-timespan_required",
    ),
    pytest.param(  # set_mode() without an until calls _set_tcc_mode(), not this
        _Call("zone", _TEMP, {"temperature": 20.0}, method="_set_mode"),
        Reason.TIMESPAN_REQUIRED,
        {"mode": "temporary_override"},
        id="zon-timespan_required-until",
    ),
    pytest.param(  # set_mode() without an until calls _set_tcc_mode(), not this
        _Call("dhw", _TEMP, {"state": _ON}, method="_set_mode"),
        Reason.TIMESPAN_REQUIRED,
        {"mode": "temporary_override"},
        id="dhw-timespan_required-until",
    ),
    pytest.param(
        _Call("tcs", _AUTO, {"until": _FUTURE}),
        Reason.TIMESPAN_NOT_ALLOWED,
        {"mode": "auto"},
        id="tcs-timespan_not_allowed-until",
    ),
    pytest.param(
        _Call("tcs", _AUTO, {"duration": td(hours=1)}),
        Reason.TIMESPAN_NOT_ALLOWED,
        {"mode": "auto"},
        id="tcs-timespan_not_allowed-duration",
    ),
    pytest.param(
        _Call("zone", _FOLLOW, {"until": _FUTURE}),
        Reason.TIMESPAN_NOT_ALLOWED,
        {"mode": "follow_schedule"},
        id="zon-timespan_not_allowed-until",
    ),
    pytest.param(
        _Call("dhw", _PERM, {"state": _ON, "until": _FUTURE}),
        Reason.TIMESPAN_NOT_ALLOWED,
        {"mode": "permanent_override"},
        id="dhw-timespan_not_allowed-until",
    ),
    pytest.param(
        _Call("tcs", _AWAY, {"duration": td(days=1)}),
        Reason.TIMESPAN_UNSUPPORTED,
        {"mode": "away", "timing_mode": "period"},
        id="tcs-timespan_unsupported",
    ),
    pytest.param(
        _Call("tcs", _AWAY, {"until": _NAIVE}),
        Reason.TIMESPAN_INVALID,
        {"mode": "away"},
        id="tcs-timespan_invalid-naive",
    ),
    pytest.param(
        _Call("zone", _TEMP, {"temperature": 20.0, "until": "not-a-datetime"}),
        Reason.TIMESPAN_INVALID,
        {"mode": "temporary_override"},
        id="zon-timespan_invalid-string",
    ),
    pytest.param(
        _Call("tcs", _AWAY, {"period": td.max}),
        Reason.TIMESPAN_OUT_OF_RANGE,
        {"mode": "away", "timing_mode": "period"},
        id="tcs-timespan_out_of_range",
    ),
    pytest.param(
        _Call("tcs", _AWAY, {"until": _PAST}),
        Reason.TIMESPAN_NOT_IN_FUTURE,
        {"mode": "away"},
        id="tcs-timespan_not_in_future-until",
    ),
    pytest.param(
        _Call("tcs", _ECO, {"duration": td(0)}),
        Reason.TIMESPAN_NOT_IN_FUTURE,
        {"mode": "auto_with_eco"},
        id="tcs-timespan_not_in_future-duration",
    ),
    #
    # the zone's temperature
    pytest.param(
        _Call("zone", _PERM, {}),
        Reason.TEMPERATURE_REQUIRED,
        {"mode": "permanent_override"},
        id="zon-temperature_required",
    ),
    pytest.param(
        _Call("zone", _FOLLOW, {"temperature": 20.0}),
        Reason.TEMPERATURE_NOT_ALLOWED,
        {"mode": "follow_schedule"},
        id="zon-temperature_not_allowed",
    ),
    pytest.param(
        _Call("zone", _PERM, {"temperature": math.nan}),
        Reason.TEMPERATURE_INVALID,
        {"mode": "permanent_override"},
        id="zon-temperature_invalid",
    ),
    #
    # the DHW's state
    pytest.param(
        _Call("dhw", _PERM, {}),
        Reason.STATE_REQUIRED,
        {"mode": "permanent_override"},
        id="dhw-state_required",
    ),
    pytest.param(
        _Call("dhw", _FOLLOW, {"state": _ON}),
        Reason.STATE_NOT_ALLOWED,
        {"mode": "follow_schedule"},
        id="dhw-state_not_allowed",
    ),
    pytest.param(
        _Call("dhw", _PERM, {"state": "no_such_state"}),
        Reason.STATE_UNKNOWN,
        {"state": "no_such_state"},
        id="dhw-state_unknown",
    ),
    pytest.param(
        _Call("dhw", _PERM, {"state": _ON}),  # see the patch of allowed_states
        Reason.STATE_UNSUPPORTED,
        {"state": "on"},
        id="dhw-state_unsupported",
    ),
]


@pytest.fixture
def fixture_folder() -> Path:
    return Path(FIXTURES) / "default"


@pytest.fixture
def entities(
    tcs: ControlSystem,
    zone: Zone,
    dhw: HotWater,
) -> dict[str, ControlSystem | Zone | HotWater]:
    """Return the entities under test, keyed by the name of their fixture."""
    return {"tcs": tcs, "zone": zone, "dhw": dhw}


@pytest.mark.parametrize(("call", "reason", "details"), CASES)
async def test_mode_request_error_reason(
    entities: dict[str, ControlSystem | Zone | HotWater],
    call: _Call,
    reason: Reason,
    details: dict[str, str],
) -> None:
    """Test a rejected mode request has the reason (and details) of its raise site."""

    entity = entities[call.entity]

    # the default fixture's DHW allows both states, so one is removed
    allowed_states = (
        patch.object(
            type(entity),
            "allowed_states",
            new_callable=PropertyMock,
            return_value=(DhwState.OFF,),
        )
        if reason is Reason.STATE_UNSUPPORTED
        else nullcontext()
    )

    with (
        allowed_states,
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock,
        pytest.raises(InvalidModeRequestError) as exc_info,
    ):
        await getattr(entity, call.method)(call.mode, **call.kwargs)

    mock.assert_not_awaited()  # it is rejected before any request is made

    assert exc_info.value.reason is reason
    assert exc_info.value.details == details


def test_mode_request_error_reasons_are_all_raised() -> None:
    """Test every reason of a mode request is raised by at least one site (above)."""

    others = {Reason.DATETIME_INVALID, Reason.SCHEDULE_INVALID, Reason.ZONE_UNKNOWN}

    raised = {case.values[1] for case in CASES}
    assert raised == set(Reason) - others
