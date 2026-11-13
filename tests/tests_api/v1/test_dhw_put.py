"""Test the v1 PUT of a DHW's mode (via its changeableValues).

  PUT /devices/{dhw_id}/thermostat/changeableValues
    {"status": "Hold", "mode": "DHWOn"}
    {"status": "Hold", "mode": "DHWOff", "nextTime": "2026-07-01T22:00:00"}
    {"status": "Scheduled", "mode": null}

It is answered 201 with a comm task (see test_comm_task.py). HotWater._set_dhw() builds
the body (it always has a mode, even if null), and set_dhw_on(), set_dhw_off() and
set_dhw_auto() call it. A DHW's mode is DHWOn or DHWOff (there is no Auto), and its
nextTime (if any) is the location's local time, without a Z (as for a zone's). The
older (non-async) client sent PascalCase keys, and a null for each other key: e.g.
{"Status": "Scheduled", "Mode": None, "NextTime": None, "SpecialModes": None,
 "HeatSetpoint": None, "CoolSetpoint": None}.

On some installations (e.g. the test system), the vendor requires a DHW's mode, and
forbids its status and nextTime (if not null), so it can't be set to follow its
schedule, nor to a mode until a given time, via this API (and a mode-only PUT that is
accepted is not carried out). There, the vendor validates only the non-null values (and
ignores unknown keys): so the older client's revert body fails on its Status alone, and
is accepted without it. It is not known if this is so of all DHWs. (The v2 API sets
the same DHW as expected.)

The vendor's errors:
- 400 DeviceIsLost: a DHW that is not alive (i.e. its gateway is offline), whatever
  the body (it is first, followed by any of the errors below, but InvalidInput)
- 400 ParameterIsMissing: no mode, or a null one ("'ThermostatMode' is required.")
- 400 ForbiddenParameter: e.g. "'Status' is forbidden." (see above)
- 400 ThermostatModeNotAllowed: a mode that is valid, but not for a DHW (e.g. Off)
- 400 InvalidInput: a mode that is not of the vendor's enum (e.g. Auto)
"""

from __future__ import annotations

from datetime import UTC, datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync import ApiCallRejectedError
from evohomeasync.schemas import TccDhwMode, TccFailureCode, _TaskIdT
from tests.const import URL_BASE_V1

from .vendor import DHW_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from evohomeasync import HotWater
    from evohomeasync.schemas import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


TASK: Final[TccTaskResponseT] = {"id": _TaskIdT(1234567890)}

URL_DHW_MODE: Final = f"{URL_BASE_V1}/devices/{DHW_ID}/thermostat/changeableValues"

# the location is in GMT Standard Time (i.e. Europe/London): in July, that is BST
_UNTIL_IN_BST: Final = dt(2026, 7, 1, 21, tzinfo=UTC)  # i.e. 22:00 local


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda dhw: dhw.set_dhw_on(),
            {"status": "Hold", "mode": "DHWOn"},
            id="set_dhw_on",
        ),
        pytest.param(  # the nextTime is local time (here, BST), without a Z
            lambda dhw: dhw.set_dhw_off(until=_UNTIL_IN_BST),
            {"status": "Hold", "mode": "DHWOff", "nextTime": "2026-07-01T22:00:00"},
            id="set_dhw_off_until",
        ),
        pytest.param(  # its mode is null (see O1 in the ledger)
            lambda dhw: dhw.set_dhw_auto(),
            {"status": "Scheduled", "mode": None},
            id="set_dhw_auto",
        ),
    ],
)
async def test_set_dhw(
    dhw: HotWater,
    mock: AioResponses,
    call: Callable[[HotWater], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """The public methods PUT the mode as below (each its own body)."""

    mock.put(URL_DHW_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await call(dhw)

    mock.assert_called_once_with(URL_DHW_MODE, HTTPMethod.PUT, json=body)


async def test_put_mode_only(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A body of only a mode (DHWOn/DHWOff) is accepted (a 201).

    The client does not send one (see set_dhw_on()), so this is via Auth.put().
    """

    url = f"devices/{DHW_ID}/thermostat/changeableValues"
    mock.put(URL_DHW_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await dhw._auth.put(url, {"mode": TccDhwMode.DHW_OFF})

    mock.assert_called_once_with(URL_DHW_MODE, HTTPMethod.PUT, json={"mode": "DHWOff"})


@pytest.mark.parametrize(
    ("json", "code", "message"),
    [
        pytest.param(
            {"mode": None},
            TccFailureCode.PARAMETER_IS_MISSING,
            "'ThermostatMode' is required.",
            id="mode_is_missing",
        ),
        pytest.param(  # on the test system
            {"mode": "DHWOff", "status": "Scheduled"},
            TccFailureCode.FORBIDDEN_PARAMETER,
            "'Status' is forbidden.",
            id="status_is_forbidden",
        ),
        pytest.param(  # on the test system
            {"mode": "DHWOff", "next_time": "2026-07-01T22:00:00"},
            TccFailureCode.FORBIDDEN_PARAMETER,
            "'NextTime' is forbidden.",
            id="next_time_is_forbidden",
        ),
        pytest.param(  # a ThermostatMode, but not for a DHW
            {"mode": "Off"},
            "ThermostatModeNotAllowed",  # not (yet) a TccFailureCode
            "Mode Off is not allowed. Allowed modes are DHWOn, DHWOff.",  # 2026-11-13
            id="mode_not_allowed",
        ),
        pytest.param(  # not a ThermostatMode at all (there is no Auto)
            {"mode": "Auto"},
            TccFailureCode.INVALID_INPUT,
            'Error converting value "Auto" ...',  # abridged
            id="invalid_input",
        ),
    ],
)
async def test_put_rejected(
    dhw: HotWater,
    mock: AioResponses,
    json: dict[str, object],
    code: str,
    message: str,
) -> None:
    """A bad request is a 400 (via Auth.put(), as the client would not send it)."""

    url = f"devices/{DHW_ID}/thermostat/changeableValues"
    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.put(URL_DHW_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await dhw._auth.put(url, json)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": code}


async def test_set_dhw_auto_forbidden(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """On the test system, set_dhw_auto() is a 400 (its status is forbidden).

    Its mode is null too, but (with a status) that is not a ParameterIsMissing (probed
    2026-11-13, of a lost DHW: its errors were DeviceIsLost, then this one).
    """

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.FORBIDDEN_PARAMETER,
            "message": "'Status' is forbidden.",
        }
    ]
    mock.put(URL_DHW_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await dhw.set_dhw_auto()

    assert err.value.details == {"code": TccFailureCode.FORBIDDEN_PARAMETER}


async def test_set_dhw_device_is_lost(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A PUT to a DHW that is not alive is a 400 (DeviceIsLost), whatever the body."""

    body: list[TccFailureResponseT] = [
        {"code": TccFailureCode.DEVICE_IS_LOST, "message": "Device is lost."}
    ]
    mock.put(URL_DHW_MODE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await dhw.set_dhw_on()

    assert err.value.details == {"code": TccFailureCode.DEVICE_IS_LOST}
