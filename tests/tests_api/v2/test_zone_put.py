"""Test the v2 PUT of a zone's mode (its setpoint).

  PUT /temperatureZone/{zon_id}/heatSetpoint
    {"setpointMode": "FollowSchedule"}
    {"setpointMode": "PermanentOverride", "heatSetpointValue": 20.5}
    {"setpointMode": "TemporaryOverride", "heatSetpointValue": 20.5,
                                          "timeUntil": "2026-11-01T13:00:00Z"}

It is answered 201 with a comm task (see test_comm_task.py). A TemporaryOverride
requires a timeUntil (a UTC datetime, with a Z; not untilTime, as for a DHW), and both
overrides require a heatSetpointValue. Zone._put_mode() builds the body (as is,
without checks); set_mode() checks the request first (see tests/tests), and turns a
duration into a timeUntil. This URL is PUT-only, but its GET is a 404 (HTML, as if it
did not exist), not a 405 (as for a TCS's mode or a DHW's state).

The vendor's errors:
- 400 HeatSetpointChangeTargetTemperatureNotSet: an override without its value
- 400 HeatSetpointChangeTimeUntilNotSet: a TemporaryOverride without its timeUntil
- 400 InvalidInput: a setpointMode that is not of its enum (e.g. one that is
  snake_case, or an undocumented mode, such as AdvancedOverride: there is none)
- 401 Unauthorized: an id that is not the user's
- 500: a setpointMode given as an int that is not of its enum (it is bound to an
  enum of 0-3, so 3, i.e. VacationHold, is accepted, but 4 is not)

The vendor accepts (as probed, 2026-11-04) a heatSetpointValue that is outside the
zone's min/maxHeatSetpoint, or not a multiple of its valueResolution, and reports it as
sent (e.g. 99); and a timeUntil that is beyond its maxDuration, or not a multiple of
its timingResolution, or that is now (or past), which it reports truncated to the
minute. It also accepts a heatSetpointValue with a FollowSchedule (e.g. 0.0), and a
null timeUntil with a PermanentOverride. It accepts a VacationHold (or 3), even for a
zone that does not have that mode, but then its comm task fails.

The controller (as seen by hand, 2026-11-04, an evohome) clamps a setpoint to its
min/maxHeatSetpoint (so the vendor then reports one that is not in use), but uses one
of a finer resolution as is (e.g. 20.1, though its valueResolution is 0.5); it honours
a timeUntil that is beyond its maxDuration (or off its resolution), but ignores one in
the past.

A timeUntil is UTC: the zone's status then reports it as its until (also UTC). (The v1
API differs: its NextTime is the location's local time.)
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import (
    ApiCallErrorReason,
    ApiCallFailedError,
    ApiCallRejectedError,
    ZoneMode,
)
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import URL_BASE_V2

from .vendor import NOT_THE_USERS_ID, USR_ACCOUNT, ZON_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import Zone
    from evohomeasync2.schemas.account import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


_NOW: Final = "2026-11-01T12:00:00+00:00"  # a time in GMT (the location's TZ)

TASK: Final[TccTaskResponseT] = {"id": "1668279943"}

URL_ZON_MODE: Final = f"{URL_BASE_V2}/temperatureZone/{ZON_ID}/heatSetpoint"


@pytest.mark.parametrize(
    ("mode", "value", "until", "body"),
    [
        pytest.param(
            ZoneMode.FOLLOW_SCHEDULE,
            None,
            None,
            {"setpointMode": "FollowSchedule"},
            id="follow_schedule",
        ),
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE,
            20.5,
            None,
            {"setpointMode": "PermanentOverride", "heatSetpointValue": 20.5},
            id="permanent_override",
        ),
        pytest.param(  # the timeUntil is UTC, with a Z, to the second
            ZoneMode.TEMPORARY_OVERRIDE,
            20.5,
            dt(2026, 11, 1, 13, 0, 0, 123456, tzinfo=UTC),
            {
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 20.5,
                "timeUntil": "2026-11-01T13:00:00Z",
            },
            id="temporary_override",
        ),
    ],
)
async def test_put_mode(
    *,  # keyword-only, as pytest passes them by name
    zone: Zone,
    mock: AioResponses,
    mode: ZoneMode,
    value: float | None,
    until: dt | None,
    body: dict[str, object],
) -> None:
    """Zone._put_mode() sends only the keys it is given."""

    mock.put(URL_ZON_MODE, status=HTTPStatus.CREATED, payload=TASK)

    task = await zone._put_mode(mode, heat_setpoint_value=value, time_until=until)

    mock.assert_called_once_with(URL_ZON_MODE, HTTPMethod.PUT, json=body)
    assert task.id == TASK["id"]


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda zone: zone.reset(),
            {"setpointMode": "FollowSchedule"},
            id="reset",
        ),
        pytest.param(
            lambda zone: zone.set_temperature(19.5),
            {"setpointMode": "PermanentOverride", "heatSetpointValue": 19.5},
            id="set_temperature",
        ),
        pytest.param(
            lambda zone: zone.set_temperature(
                19.5, until=dt(2026, 11, 1, 18, tzinfo=UTC)
            ),
            {
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 19.5,
                "timeUntil": "2026-11-01T18:00:00Z",
            },
            id="set_temperature_until",
        ),
        pytest.param(  # a duration ends that long from now
            lambda zone: zone.set_mode(
                ZoneMode.TEMPORARY_OVERRIDE, temperature=19.5, duration=td(hours=1)
            ),
            {
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 19.5,
                "timeUntil": "2026-11-01T13:00:00Z",
            },
            id="set_mode_duration",
        ),
    ],
)
async def test_set_mode(
    zone: Zone,
    mock: AioResponses,
    freezer: FrozenDateTimeFactory,
    call: Callable[[Zone], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """The public methods PUT the mode as below (each its own body)."""

    freezer.move_to(_NOW)

    mock.put(URL_ZON_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await call(zone)

    mock.assert_called_once_with(URL_ZON_MODE, HTTPMethod.PUT, json=body)


@pytest.mark.parametrize(
    ("mode", "value", "code", "message"),
    [
        pytest.param(
            ZoneMode.PERMANENT_OVERRIDE,
            None,
            TccFailureCode.HEAT_SETPOINT_CHANGE_TARGET_TEMPERATURE_NOT_SET,
            "Target temperature not specified when required",
            id="value_not_set",
        ),
        pytest.param(
            ZoneMode.TEMPORARY_OVERRIDE,
            19.5,
            TccFailureCode.HEAT_SETPOINT_CHANGE_TIME_UNTIL_NOT_SET,
            "Time until not specified when required",
            id="time_until_not_set",
        ),
    ],
)
async def test_put_mode_rejected(
    *,  # keyword-only, as pytest passes them by name
    zone: Zone,
    mock: AioResponses,
    mode: ZoneMode,
    value: float | None,
    code: TccFailureCode,
    message: str,
) -> None:
    """An override without the keys it requires is a 400."""

    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.put(URL_ZON_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await zone._put_mode(mode, heat_setpoint_value=value)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": code}
    assert message in err.value.message


async def test_put_mode_invalid_input(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A setpointMode that is not of the vendor's enum is a 400 (InvalidInput).

    The client sends only those of its ZoneMode, so this is via Auth.put() (which
    converts the keys to camelCase, and only a StrEnum's value to PascalCase).
    """

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.INVALID_INPUT,
            "message": 'Error converting value "AdvancedOverride" to type ...',
        }
    ]
    mock.put(URL_ZON_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    url = f"temperatureZone/{ZON_ID}/heatSetpoint"
    with pytest.raises(ApiCallRejectedError) as err:
        await zone._auth.put(url, {"setpoint_mode": "AdvancedOverride"})

    mock.assert_called_once_with(
        URL_ZON_MODE, HTTPMethod.PUT, json={"setpointMode": "AdvancedOverride"}
    )
    assert err.value.details == {"code": TccFailureCode.INVALID_INPUT}


async def test_put_mode_as_int(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A setpointMode that is an int not of the vendor's enum (0-3) is a 500."""

    mock.put(
        URL_ZON_MODE,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        payload={"message": "An error has occurred."},
    )

    url = f"temperatureZone/{ZON_ID}/heatSetpoint"
    with pytest.raises(ApiCallFailedError) as err:
        await zone._auth.put(url, {"setpoint_mode": 4, "heat_setpoint_value": 20.0})

    mock.assert_called_once_with(
        URL_ZON_MODE,
        HTTPMethod.PUT,
        json={"setpointMode": 4, "heatSetpointValue": 20.0},
    )
    assert err.value.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert err.value.reason is ApiCallErrorReason.SERVER_ERROR


async def test_put_mode_not_the_users(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401 (as for every URL, GET or PUT).

    So the client probes userAccount, to tell it from a 401 of the access token.
    """

    url = f"temperatureZone/{NOT_THE_USERS_ID}/heatSetpoint"
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.put(f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)
    mock.get(f"{URL_BASE_V2}/userAccount", payload=USR_ACCOUNT)  # the client's probe

    with pytest.raises(ApiCallFailedError) as err:
        await zone._auth.put(url, {"setpoint_mode": ZoneMode.FOLLOW_SCHEDULE})

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}
