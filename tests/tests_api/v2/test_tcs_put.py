"""Test the v2 PUT of a TCS's mode.

  PUT /temperatureControlSystem/{tcs_id}/mode
    {"systemMode": "Auto", "permanent": true}
    {"systemMode": "Away", "permanent": false, "timeUntil": "2026-11-14T00:00:00Z"}

It is answered 201 with a comm task (see test_comm_task.py). The TCS's modes (and
which of them may be temporary, i.e. have a timeUntil) are as per its
allowedSystemModes. A temporary mode requires timeUntil (a UTC datetime, with a Z), not
untilTime (as for a DHW). ControlSystem._put_mode() builds the body (as is, without
checks); set_mode() checks the request first (see tests/tests), and turns a duration
(e.g. of an AutoWithEco) or a period (e.g. of an Away) into a timeUntil.

The vendor's errors:
- 400 ParameterIsMissing: one per missing key, with a (PascalCase) parameterName
- 400 InvalidInput: a systemMode that is not of its enum
- 400 SystemModeChangeTimeUntilNotSet: a temporary mode, without its timeUntil
- 401 Unauthorized: an id that is not the user's
- 500: a systemMode that is of its enum, but that the TCS does not have (e.g. Cool)

The vendor accepts (as probed, 2026-11-04) a timeUntil that is beyond the mode's
maxDuration, or not a multiple of its timingResolution (even less than it), or not of
its timingMode (e.g. an Away that ends other than at midnight: it gets only a
datetime, so can't tell a duration from a period), or that is now (or past): it then
reports the mode with that timeUntil, truncated to the minute. The controller (as seen
by hand, 2026-11-04, an evohome) ends an AutoWithEco at its timeUntil (to the minute),
ignores one in the past, and runs an Away that would end before the coming midnight
until then (but honours a later one, showing more than 99 days as '99d').
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
    SystemMode,
)
from evohomeasync2.schemas.account import TCC_FAILURE_RESPONSE
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import URL_BASE_V2

from .vendor import NOT_THE_USERS_ID, TCS_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import ControlSystem
    from evohomeasync2.schemas.account import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


_NOW: Final = "2026-11-01T12:00:00+00:00"  # a time in GMT (the location's TZ)

TASK: Final[TccTaskResponseT] = {"id": "1668279943"}

URL_TCS_MODE: Final = f"{URL_BASE_V2}/temperatureControlSystem/{TCS_ID}/mode"

# NOTE: not a list[TccFailureResponseT], as that lacks parameterName (B1)
# provenance: the old tests_rf/test_v2_urls_auth.py (a PUT of {})
_PARAMETERS_ARE_MISSING: Final = [
    {
        "code": "ParameterIsMissing",
        "parameterName": "SystemMode",
        "message": "Parameter is missing.",
    },
    {
        "code": "ParameterIsMissing",
        "parameterName": "Permanent",
        "message": "Parameter is missing.",
    },
]


async def test_put_mode_permanent(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """A permanent mode has no timeUntil."""

    mock.put(URL_TCS_MODE, status=HTTPStatus.CREATED, payload=TASK)

    task = await tcs._put_mode(SystemMode.AUTO, permanent=True)

    mock.assert_called_once_with(
        URL_TCS_MODE,
        HTTPMethod.PUT,
        json={"systemMode": "Auto", "permanent": True},
    )
    assert task.id == TASK["id"]


async def test_put_mode_temporary(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """A temporary mode has a timeUntil (in UTC, with a Z, to the second)."""

    mock.put(URL_TCS_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await tcs._put_mode(
        SystemMode.AWAY,
        permanent=False,
        time_until=dt(2026, 11, 14, 0, 0, 0, 123456, tzinfo=UTC),
    )

    mock.assert_called_once_with(
        URL_TCS_MODE,
        HTTPMethod.PUT,
        json={
            "systemMode": "Away",
            "permanent": False,
            "timeUntil": "2026-11-14T00:00:00Z",
        },
    )


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda tcs: tcs.set_auto(),
            {"systemMode": "Auto", "permanent": True},
            id="set_auto",
        ),
        pytest.param(
            lambda tcs: tcs.set_heatingoff(),
            {"systemMode": "HeatingOff", "permanent": True},
            id="set_heatingoff",
        ),
        pytest.param(  # the TCS has AutoWithReset, so it is not emulated
            lambda tcs: tcs.reset(),
            {"systemMode": "AutoWithReset", "permanent": True},
            id="reset",
        ),
        pytest.param(  # a duration ends that long from now
            lambda tcs: tcs.set_mode(SystemMode.AUTO_WITH_ECO, duration=td(hours=1)),
            {
                "systemMode": "AutoWithEco",
                "permanent": False,
                "timeUntil": "2026-11-01T13:00:00Z",
            },
            id="eco_duration",
        ),
        pytest.param(  # a period ends that long from the start of the (local) day
            lambda tcs: tcs.set_mode(SystemMode.AWAY, period=td(days=1)),
            {
                "systemMode": "Away",
                "permanent": False,
                "timeUntil": "2026-11-02T00:00:00Z",
            },
            id="away_period",
        ),
        pytest.param(
            lambda tcs: tcs.set_away(until=dt(2026, 11, 3, tzinfo=UTC)),
            {
                "systemMode": "Away",
                "permanent": False,
                "timeUntil": "2026-11-03T00:00:00Z",
            },
            id="away_until",
        ),
    ],
)
async def test_set_mode(
    tcs: ControlSystem,
    mock: AioResponses,
    freezer: FrozenDateTimeFactory,
    call: Callable[[ControlSystem], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """The public methods PUT the mode as below (each its own body)."""

    freezer.move_to(_NOW)

    mock.put(URL_TCS_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await call(tcs)

    mock.assert_called_once_with(URL_TCS_MODE, HTTPMethod.PUT, json=body)


@pytest.mark.parametrize(
    ("body", "code"),
    [
        pytest.param(
            _PARAMETERS_ARE_MISSING,
            TccFailureCode.PARAMETER_IS_MISSING,
            id="parameter_is_missing",
        ),
        pytest.param(  # the message is abridged (it names the enum's .NET type)
            [
                {
                    "code": TccFailureCode.INVALID_INPUT,
                    "message": 'Error converting value "xxxxx" to type ...',
                }
            ],
            TccFailureCode.INVALID_INPUT,
            id="invalid_input",
        ),
        pytest.param(  # e.g. an untilTime (a DHW's key), not a timeUntil
            [
                {
                    "code": TccFailureCode.SYSTEM_MODE_CHANGE_TIME_UNTIL_NOT_SET,
                    "message": "No message available.",  # probed 2026-11-13
                }
            ],
            TccFailureCode.SYSTEM_MODE_CHANGE_TIME_UNTIL_NOT_SET,
            id="time_until_not_set",
        ),
    ],
)
async def test_put_mode_rejected(
    tcs: ControlSystem,
    mock: AioResponses,
    body: list[dict[str, str]],
    code: TccFailureCode,
) -> None:
    """A bad request is a 400, with a list of the vendor's errors (the first's code)."""

    mock.put(URL_TCS_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await tcs._put_mode(SystemMode.AWAY, permanent=False)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": code}


async def test_put_mode_not_the_users(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401 (as for every URL, GET or PUT)."""

    url = f"temperatureControlSystem/{NOT_THE_USERS_ID}/mode"
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.put(f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)

    with pytest.raises(ApiCallFailedError) as err:
        await tcs._auth.put(url, {"system_mode": SystemMode.AUTO, "permanent": True})

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}


async def test_put_mode_not_the_tcss(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """A mode that is of the vendor's enum, but that the TCS lacks, is a 500.

    For example, Cool (of some non-evohome systems). set_mode() would not send it, as
    the TCS lacks it, but _put_mode() does not check.
    """

    mock.put(
        URL_TCS_MODE,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        payload={"message": "An error has occurred."},
    )

    with pytest.raises(ApiCallFailedError) as err:
        await tcs._put_mode(SystemMode.COOL, permanent=True)

    mock.assert_called_once_with(
        URL_TCS_MODE, HTTPMethod.PUT, json={"systemMode": "Cool", "permanent": True}
    )
    assert not isinstance(err.value, ApiCallRejectedError)
    assert err.value.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert err.value.reason is ApiCallErrorReason.SERVER_ERROR


@pytest.mark.xfail(
    strict=True, reason="B1: TCC_FAILURE_RESPONSE rejects the vendor's parameterName"
)
def test_failure_response_schema() -> None:
    """The schema of a failed request accepts the vendor's ParameterIsMissing errors."""

    TCC_FAILURE_RESPONSE(_PARAMETERS_ARE_MISSING)
