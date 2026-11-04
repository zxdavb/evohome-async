"""Test how the vendor's v2 URLs treat requests that are outside an entity's config.

This is used to document the RESTful API that is provided by the vendor: in particular,
that it accepts requests that break the limits in an entity's config, for which the
client only logs a warning (see _TccModeMixin in zone.py), rather than raising.

Testing is at HTTP request layer (e.g. GET/PUT). Only against the vendor's server, and
every PUT here waits for its comm task (whether or not _DBG_WAIT_FOR_COMM_TASKS), as the
status that follows is then asserted. The vendor:

- accepts an until of a TCS/zone/DHW that is beyond the mode's maxDuration, or that is
  not a multiple of its timingResolution (even one less than it), and then reports it
  truncated to the minute (its seconds are dropped)

- accepts an until that is now, or in the past, and then reports the mode as if it
  were in effect (with that until)

- accepts an until of a TCS that is not of the mode's timingMode (e.g. an Away that ends
  at other than midnight): it receives only an absolute until, so can't tell a duration
  from a period

- accepts (and reports) a zone's heatSetpointValue that is outside its min/max
  HeatSetpoint, or that is not a multiple of its valueResolution

- rejects a TemporaryOverride without an until (a 400): HeatSetpointChangeTimeUntilNotSet
  for a zone, DHWUntilTimeNotSet for a DHW

- has a zone setpointMode enum of only four values (also accepted as 0-3), so there is
  no (e.g.) AdvancedOverride: an unknown name is a 400 (InvalidInput), an unknown int a
  500; VacationHold (i.e. 3) is accepted, but its comm task fails if the zone does not
  have that mode (only some non-evohome systems do)

The controller itself was observed (by hand, 2026-11-04, an evohome system) to:

- clamp a setpoint to its min/max HeatSetpoint (so the vendor then reports a value that
  is not in use), but use one of 0.1 resolution as is (20.1, although that of 0.5)
- honour an until of a zone/DHW that is beyond its maxDuration, or off its resolution
- end an AutoWithEco at its until, to the minute (it showed +72h as 'Eco (3d)')
- ignore an until of a TCS/zone/DHW that is in the past (hence, the client rejects a
  duration/period that would not end in the future)
- run an Away that would end before the coming midnight until then (the vendor reports
  Away, with the until that was sent, until midnight), but honour a later until (and
  show more than 99 days as '99d': whether that is only a display limit is unknown)

Each test ends with a PUT of Auto (a TCS), or of FollowSchedule (a zone or DHW).
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import pytest

import evohomeasync2 as evo2
from _evohome.helpers import TCC_DTM_STRFTIME
from evohomeasync2.const import SystemMode, ZoneMode
from evohomeasync2.schemas.account import TCC_TASK_RESPONSE
from evohomeasync2.schemas.const import (
    S2_CODE,
    S2_HEAT_SETPOINT_VALUE,
    S2_IS_PERMANENT,
    S2_MESSAGE,
    S2_MODE,
    S2_PERMANENT,
    S2_SETPOINT_MODE,
    S2_SETPOINT_STATUS,
    S2_STATE,
    S2_STATE_STATUS,
    S2_SYSTEM_MODE,
    S2_SYSTEM_MODE_STATUS,
    S2_TARGET_HEAT_TEMPERATURE,
    S2_TIME_UNTIL,
    S2_UNTIL,
    S2_UNTIL_TIME,
    TccDhwState,
    TccSystemMode,
    TccZoneMode,
)
from evohomeasync2.schemas.status import (
    TCC_GET_DHW_STATUS,
    TCC_GET_TCS_STATUS,
    TCC_GET_ZON_STATUS,
)
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import _wait_or_skip, should_fail_v2, should_work_v2, skipif_auth_failed

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from evohomeasync2.auth import Auth


# the vendor binds an int to its enum, and its zone setpointMode enum has only 0-3
_VACATION_HOLD_AS_INT: Final = 3

pytestmark = pytest.mark.skipif(
    not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver"
)


def _now() -> dt:
    return dt.now(tz=UTC)


def _as_until(dtm: dt) -> str:
    """Return a datetime in the vendor's format (it is truncated to the second)."""
    return dtm.strftime(TCC_DTM_STRFTIME)


def _as_reported(dtm: dt) -> str:
    """Return an until, as the vendor reports it (truncated to the minute)."""
    return _as_until(dtm.replace(second=0))


async def _put(auth: Auth, url: str, /, json: Mapping[str, object]) -> str:
    """PUT a request the vendor accepts, wait for its comm task to succeed.

    Return the task's id. The test is skipped if the task does not succeed in time.
    """

    task = TCC_TASK_RESPONSE(await auth._make_request(HTTPMethod.PUT, url, json=json))
    await _wait_or_skip(evo2.CommTask(auth, task["id"]).wait(), task["id"])
    return task["id"]


def _error_codes(response: object) -> list[str]:
    """Return the vendor's error codes, from the list of its errors."""
    assert isinstance(response, list), response
    return [e[S2_CODE] for e in response]


#######################################################################################
# A TCS


@skipif_auth_failed
@pytest.mark.parametrize(
    ("system_mode", "until"),
    [
        pytest.param(  # maxDuration is 1.00:00:00
            TccSystemMode.AUTO_WITH_ECO,
            lambda: _now() + td(hours=25),
            id="eco_beyond_max",
        ),
        pytest.param(  # timingResolution is 01:00:00
            TccSystemMode.AUTO_WITH_ECO,
            lambda: _now() + td(minutes=90),
            id="eco_off_resolution",
        ),
        pytest.param(
            TccSystemMode.AUTO_WITH_ECO,
            lambda: _now() + td(minutes=5),
            id="eco_under_resolution",
        ),
        pytest.param(  # timingMode is Period (i.e. ends at midnight)
            TccSystemMode.AWAY,
            lambda: _now() + td(hours=3),
            id="away_not_at_midnight",
        ),
        pytest.param(  # the controller ignores it
            TccSystemMode.AUTO_WITH_ECO,
            lambda: _now() - td(hours=1),
            id="eco_in_the_past",
        ),
    ],
)
async def test_tcs_until_outside_config(
    tcs: evo2.ControlSystem,
    system_mode: TccSystemMode,
    until: Callable[[], dt],
) -> None:
    """Test the vendor accepts a TCS until that is outside the mode's config."""

    if SystemMode[system_mode.name] not in tcs.allowed_modes:
        pytest.skip(f"The TCS has no {system_mode} mode")

    auth = tcs._auth
    url = f"{tcs._TCC_TYPE}/{tcs.id}/mode"
    time_until = until()

    await _put(
        auth,
        url,
        json={
            S2_SYSTEM_MODE: system_mode,
            S2_PERMANENT: False,
            S2_TIME_UNTIL: _as_until(time_until),
        },
    )

    status = await should_work_v2(
        auth,
        HTTPMethod.GET,
        f"{tcs._TCC_TYPE}/{tcs.id}/status",
        schema=TCC_GET_TCS_STATUS,
    )

    assert status[S2_SYSTEM_MODE_STATUS] == {
        S2_MODE: system_mode,
        S2_IS_PERMANENT: False,
        S2_TIME_UNTIL: _as_reported(time_until),
    }

    await _put(auth, url, json={S2_SYSTEM_MODE: TccSystemMode.AUTO, S2_PERMANENT: True})


#######################################################################################
# A zone


@skipif_auth_failed
@pytest.mark.parametrize(
    ("temperature", "until"),
    [
        pytest.param(  # maxDuration is 1.00:00:00
            20.0, lambda: _now() + td(hours=25), id="beyond_max"
        ),
        pytest.param(  # timingResolution is 00:10:00
            20.5, lambda: _now() + td(minutes=15), id="off_resolution"
        ),
        pytest.param(  # minHeatSetpoint is 5.0 (the controller clamps it)
            4.5, lambda: _now() + td(minutes=30), id="below_min"
        ),
        pytest.param(  # maxHeatSetpoint is 35.0 (the controller clamps it)
            35.5, lambda: _now() + td(minutes=31), id="above_max"
        ),
        pytest.param(  # valueResolution is 0.5 (the controller uses it as is)
            20.1, lambda: _now() + td(minutes=32), id="off_value_resolution"
        ),
        pytest.param(  # the controller ignores it
            19.0, lambda: _now() - td(hours=1), id="in_the_past"
        ),
    ],
)
async def test_zon_setpoint_outside_config(
    zone: evo2.Zone,
    temperature: float,
    until: Callable[[], dt],
) -> None:
    """Test the vendor accepts a zone setpoint that is outside the zone's config."""

    auth = zone._auth
    url = f"{zone._TCC_TYPE}/{zone.id}/heatSetpoint"
    time_until = until()

    await _put(
        auth,
        url,
        json={
            S2_SETPOINT_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
            S2_HEAT_SETPOINT_VALUE: temperature,
            S2_TIME_UNTIL: _as_until(time_until),
        },
    )

    status = await should_work_v2(
        auth,
        HTTPMethod.GET,
        f"{zone._TCC_TYPE}/{zone.id}/status",
        schema=TCC_GET_ZON_STATUS,
    )

    assert status[S2_SETPOINT_STATUS] == {
        S2_TARGET_HEAT_TEMPERATURE: temperature,
        S2_SETPOINT_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_UNTIL: _as_reported(time_until),
    }

    await _put(auth, url, json={S2_SETPOINT_MODE: TccZoneMode.FOLLOW_SCHEDULE})


@skipif_auth_failed
async def test_zon_setpoint_rejected(
    zone: evo2.Zone,
) -> None:
    """Test the vendor rejects a zone setpoint that is invalid, rather than limited."""

    auth = zone._auth
    url = f"{zone._TCC_TYPE}/{zone.id}/heatSetpoint"
    body: dict[str, Any]

    # a TemporaryOverride requires a timeUntil
    body = {
        S2_SETPOINT_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_HEAT_SETPOINT_VALUE: 20.0,
    }
    response = await should_fail_v2(
        auth, HTTPMethod.PUT, url, json=body, status=HTTPStatus.BAD_REQUEST
    )
    assert _error_codes(response) == ["HeatSetpointChangeTimeUntilNotSet"]

    # there is no undocumented mode (e.g. for 'advance to the next switchpoint')
    for mode in ("AdvancedOverride", "AdvanceOverride", "Advance", "NextPeriod"):
        body = {
            S2_SETPOINT_MODE: mode,
            S2_HEAT_SETPOINT_VALUE: 20.0,
            S2_TIME_UNTIL: _as_until(_now() + td(hours=1)),
        }
        response = await should_fail_v2(
            auth, HTTPMethod.PUT, url, json=body, status=HTTPStatus.BAD_REQUEST
        )
        assert _error_codes(response) == ["InvalidInput"], mode

    # the enum has only four values, 0-3 (e.g. 3 is VacationHold), so 4 is a 500
    body = {
        S2_SETPOINT_MODE: _VACATION_HOLD_AS_INT + 1,
        S2_HEAT_SETPOINT_VALUE: 20.0,
        S2_TIME_UNTIL: _as_until(_now() + td(hours=1)),
    }
    response = await should_fail_v2(
        auth, HTTPMethod.PUT, url, json=body, status=HTTPStatus.INTERNAL_SERVER_ERROR
    )
    assert isinstance(response, dict), response
    assert response[S2_MESSAGE] == "An error has occurred."


@skipif_auth_failed
async def test_zon_vacation_hold_task_fails(
    zone: evo2.Zone,
) -> None:
    """Test the vendor accepts a VacationHold that the zone lacks, but its task fails.

    So, unless the comm task is awaited, nothing shows that the PUT was not carried out.
    """

    if ZoneMode.VACATION_HOLD in zone.allowed_modes:
        pytest.skip("The zone has a VacationHold mode")

    auth = zone._auth
    url = f"{zone._TCC_TYPE}/{zone.id}/heatSetpoint"

    for i, mode in enumerate((TccZoneMode.VACATION_HOLD, _VACATION_HOLD_AS_INT)):
        body = {
            S2_SETPOINT_MODE: mode,
            S2_HEAT_SETPOINT_VALUE: 12.0 + i,  # avoid an equivalent PUT
            S2_TIME_UNTIL: _as_until(_now() + td(hours=1)),
        }
        task = TCC_TASK_RESPONSE(
            await auth._make_request(HTTPMethod.PUT, url, json=body)
        )

        with pytest.raises(evo2.CommTaskFailedError):
            await _wait_or_skip(evo2.CommTask(auth, task["id"]).wait(), task["id"])

    status = await should_work_v2(
        auth,
        HTTPMethod.GET,
        f"{zone._TCC_TYPE}/{zone.id}/status",
        schema=TCC_GET_ZON_STATUS,
    )
    assert status[S2_SETPOINT_STATUS][S2_SETPOINT_MODE] != TccZoneMode.VACATION_HOLD


#######################################################################################
# A DHW


@skipif_auth_failed
@pytest.mark.parametrize(
    "until",
    [
        pytest.param(  # maxDuration is 1.00:00:00
            lambda: _now() + td(hours=25), id="beyond_max"
        ),
        pytest.param(  # timingResolution is 00:10:00
            lambda: _now() + td(minutes=15), id="off_resolution"
        ),
        pytest.param(  # the controller ignores it
            lambda: _now() - td(hours=1), id="in_the_past"
        ),
    ],
)
async def test_dhw_until_outside_config(
    dhw: evo2.HotWater,
    until: Callable[[], dt],
) -> None:
    """Test the vendor accepts a DHW until that is outside the DHW's config."""

    auth = dhw._auth
    url = f"{dhw._TCC_TYPE}/{dhw.id}/state"
    until_time = until()

    await _put(
        auth,
        url,
        json={
            S2_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
            S2_STATE: TccDhwState.OFF,
            S2_UNTIL_TIME: _as_until(until_time),
        },
    )

    status = await should_work_v2(
        auth,
        HTTPMethod.GET,
        f"{dhw._TCC_TYPE}/{dhw.id}/status",
        schema=TCC_GET_DHW_STATUS,
    )

    assert status[S2_STATE_STATUS] == {
        S2_STATE: TccDhwState.OFF,
        S2_MODE: TccZoneMode.TEMPORARY_OVERRIDE,
        S2_UNTIL: _as_reported(until_time),  # NOTE: until, not untilTime
    }

    response = await should_fail_v2(  # a TemporaryOverride requires an untilTime
        auth,
        HTTPMethod.PUT,
        url,
        json={S2_MODE: TccZoneMode.TEMPORARY_OVERRIDE, S2_STATE: TccDhwState.OFF},
        status=HTTPStatus.BAD_REQUEST,
    )
    assert _error_codes(response) == ["DHWUntilTimeNotSet"]

    await _put(auth, url, json={S2_MODE: TccZoneMode.FOLLOW_SCHEDULE})
