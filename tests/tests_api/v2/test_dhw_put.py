"""Test the v2 PUT of a DHW's mode (its state).

  PUT /domesticHotWater/{dhw_id}/state
    {"mode": "FollowSchedule"}
    {"mode": "PermanentOverride", "state": "Off"}
    {"mode": "TemporaryOverride", "state": "On", "untilTime": "2026-11-01T13:00:00Z"}

It is answered 201 with a comm task (see test_comm_task.py). Its modes and states are
as per the DHW's dhwStateCapabilitiesResponse. A TemporaryOverride requires an
untilTime (a UTC datetime, with a Z), not timeUntil (as for a TCS or zone), and both
overrides require a state. HotWater._put_mode() builds the body (as is, without
checks); set_mode() checks the request first (see tests/tests), and turns a duration
into an untilTime. The DHW's status then reports it as its until (not untilTime).

The vendor's errors:
- 400 ParameterIsMissing: no mode (with its parameterName, Mode)
- 400 InvalidInput: a mode, or a state, that is not of its enum (one error for each,
  whose message names the enum's .NET type, and the JSON path of the value)
- 400 DHWStateNotSet: an override without its state
- 400 DHWUntilTimeNotSet: a TemporaryOverride without its untilTime
- 401 Unauthorized: an id that is not the user's

The vendor accepts (as probed, 2026-11-04) an untilTime that is beyond the DHW's
maxDuration, or not a multiple of its timingResolution, or that is now (or past), and
reports it (as until) truncated to the minute. The controller (as seen by hand,
2026-11-04, an evohome) honours one that is beyond its maxDuration (or off its
resolution), but ignores one in the past.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import ApiCallFailedError, ApiCallRejectedError, DhwState, ZoneMode
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import URL_BASE_V2

from .vendor import DHW_ID, NOT_THE_USERS_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import HotWater
    from evohomeasync2.schemas.account import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


_NOW: Final = "2026-11-01T12:00:00+00:00"  # a time in GMT (the location's TZ)

TASK: Final[TccTaskResponseT] = {"id": "1668279943"}

URL_DHW_STATE: Final = f"{URL_BASE_V2}/domesticHotWater/{DHW_ID}/state"


@pytest.mark.parametrize(
    ("mode", "state", "until", "body"),
    [
        pytest.param(
            ZoneMode.FOLLOW_SCHEDULE,
            None,
            None,
            {"mode": "FollowSchedule"},
            id="follow_schedule",
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE,
            DhwState.OFF,
            None,
            {"mode": "PermanentOverride", "state": "Off"},
            id="permanent_override",
        ),
        pytest.param(  # the untilTime is UTC, with a Z, to the second
            ZoneMode.TEMPORARY_OVERRIDE,
            DhwState.ON,
            dt(2026, 11, 1, 13, 0, 0, 123456, tzinfo=UTC),
            {
                "mode": "TemporaryOverride",
                "state": "On",
                "untilTime": "2026-11-01T13:00:00Z",
            },
            id="temporary_override",
        ),
    ],
)
async def test_put_mode(
    *,  # keyword-only, as pytest passes them by name
    dhw: HotWater,
    mock: AioResponses,
    mode: ZoneMode,
    state: DhwState | None,
    until: dt | None,
    body: dict[str, object],
) -> None:
    """HotWater._put_mode() sends only the keys it is given."""

    mock.put(URL_DHW_STATE, status=HTTPStatus.CREATED, payload=TASK)

    task = await dhw._put_mode(mode, state=state, until_time=until)

    mock.assert_called_once_with(URL_DHW_STATE, HTTPMethod.PUT, json=body)
    assert task.id == TASK["id"]


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda dhw: dhw.reset(),
            {"mode": "FollowSchedule"},
            id="reset",
        ),
        pytest.param(
            lambda dhw: dhw.set_on(),
            {"mode": "PermanentOverride", "state": "On"},
            id="set_on",
        ),
        pytest.param(
            lambda dhw: dhw.set_off(until=dt(2026, 11, 1, 18, tzinfo=UTC)),
            {
                "mode": "TemporaryOverride",
                "state": "Off",
                "untilTime": "2026-11-01T18:00:00Z",
            },
            id="set_off_until",
        ),
        pytest.param(  # a duration ends that long from now
            lambda dhw: dhw.set_mode(
                ZoneMode.TEMPORARY_OVERRIDE, state=DhwState.ON, duration=td(hours=1)
            ),
            {
                "mode": "TemporaryOverride",
                "state": "On",
                "untilTime": "2026-11-01T13:00:00Z",
            },
            id="set_mode_duration",
        ),
    ],
)
async def test_set_mode(
    dhw: HotWater,
    mock: AioResponses,
    freezer: FrozenDateTimeFactory,
    call: Callable[[HotWater], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """The public methods PUT the mode as below (each its own body)."""

    freezer.move_to(_NOW)

    mock.put(URL_DHW_STATE, status=HTTPStatus.CREATED, payload=TASK)

    await call(dhw)

    mock.assert_called_once_with(URL_DHW_STATE, HTTPMethod.PUT, json=body)


@pytest.mark.parametrize(
    ("mode", "state", "code", "message"),
    [
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE,
            None,
            TccFailureCode.DHW_STATE_NOT_SET,
            "Domestic hot water state is not set when required",
            id="state_not_set",
        ),
        pytest.param(
            ZoneMode.TEMPORARY_OVERRIDE,
            DhwState.ON,
            TccFailureCode.DHW_UNTIL_TIME_NOT_SET,
            "Domestic hot water until time is not set when required",
            id="until_time_not_set",
        ),
    ],
)
async def test_put_mode_rejected(
    *,  # keyword-only, as pytest passes them by name
    dhw: HotWater,
    mock: AioResponses,
    mode: ZoneMode,
    state: DhwState | None,
    code: TccFailureCode,
    message: str,
) -> None:
    """An override without the keys it requires is a 400."""

    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.put(URL_DHW_STATE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await dhw._put_mode(mode, state=state)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": code}
    assert message in err.value.message


async def test_put_mode_invalid_input(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A mode or state not of the vendor's enum is a 400 (InvalidInput), for each.

    The client sends only those of its ZoneMode/DhwState, so this is via Auth.put():
    here, a mode and state that are swapped.
    """

    # provenance: the old tests_rf/test_v2_urls_task.py (its line breaks removed)
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.INVALID_INPUT,
            "message": "Error converting value 'TemporaryOverride' to type "
            "'DomesticHotWater.Enums.EMEADomesticHotWaterState'. "
            "Path 'state', line 1, position 29.",
        },
        {
            "code": TccFailureCode.INVALID_INPUT,
            "message": "Error converting value 'Off' to type "
            "'DomesticHotWater.Enums.EMEADomesticHotWaterSetpointMode'. "
            "Path 'mode', line 1, position 44.",
        },
    ]
    mock.put(URL_DHW_STATE, status=HTTPStatus.BAD_REQUEST, payload=body)

    url = f"domesticHotWater/{DHW_ID}/state"
    with pytest.raises(ApiCallRejectedError) as err:
        await dhw._auth.put(url, {"state": "TemporaryOverride", "mode": "Off"})

    assert err.value.details == {"code": TccFailureCode.INVALID_INPUT}  # the first's
    assert "EMEADomesticHotWaterSetpointMode" in err.value.message  # all are kept


async def test_put_mode_parameter_is_missing(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A body without a mode is a 400 (ParameterIsMissing, with its parameterName)."""

    # NOTE: not a list[TccFailureResponseT], as that lacks parameterName (B1)
    body = [
        {
            "code": "ParameterIsMissing",
            "parameterName": "Mode",
            "message": "Parameter is missing.",
        }
    ]
    mock.put(URL_DHW_STATE, status=HTTPStatus.BAD_REQUEST, payload=body)

    url = f"domesticHotWater/{DHW_ID}/state"
    with pytest.raises(ApiCallRejectedError) as err:
        await dhw._auth.put(url, {})

    mock.assert_called_once_with(URL_DHW_STATE, HTTPMethod.PUT, json={})
    assert err.value.details == {"code": TccFailureCode.PARAMETER_IS_MISSING}


async def test_put_mode_not_the_users(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401 (as for every URL, GET or PUT)."""

    url = f"domesticHotWater/{NOT_THE_USERS_ID}/state"
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.put(f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)

    with pytest.raises(ApiCallFailedError) as err:
        await dhw._auth.put(url, {"mode": ZoneMode.FOLLOW_SCHEDULE})

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}
