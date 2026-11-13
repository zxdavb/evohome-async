"""Test the v1 PUT of a zone's setpoint.

  PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint
    {"status": "Hold", "value": 19.5}
    {"status": "Temporary", "value": 19.5, "nextTime": "2026-07-01T22:00:00"}
    {"status": "Scheduled"}

It is answered 201 with a comm task (see test_comm_task.py). This URL is PUT-only (a GET
is a 404, as HTML). Zone._set_heat_setpoint() builds the body, and set_temperature()
and set_zone_auto() call it. The older (non-async) client sent PascalCase keys, and a
null for each key it did not need (e.g. {"Value": None, "Status": "Scheduled",
"NextTime": None}), whereas this library sends camelCase keys, and omits those it does
not need: the vendor accepts either (its keys and enum values are case-insensitive).

The same can be done via the zone's changeableValues (with its mode, Heat or Off, and
this body as its heatSetpoint), but the client does not do so:
  PUT /devices/{zon_id}/thermostat/changeableValues
    {"mode": "Off", "heatSetpoint": {"value": null, "status": "Scheduled", ...}}

A nextTime is the location's local time, without a Z (the vendor ignores any Z): so the
client converts an until to the location's time zone (which observes DST) before
sending it. The zone's changeableValues then report it as sent (without a Z), and the
v2 API reports it in UTC. Between v2.0.0 and v3.0.0 the client sent it in UTC, so (e.g.
in BST) an override ended early, by the location's UTC offset.

The vendor's errors:
- 400 DeviceIsLost: a zone that is not alive (i.e. its gateway is offline), whatever
  the body (it is first, followed by any of the errors below, but InvalidInput)
- 400 ParameterIsMissing: e.g. a Hold without its value ("'Value' is required."), with
  a ValueOutOfRange too ("Value of field Value is out of range.")
- 400 InvalidInput: a status that is not of its enum (its message names the .NET type)
- 400 ThermostatModeNotAllowed: (of changeableValues) a mode that the zone lacks ("Mode
  Cool is not allowed. Allowed modes are Heat, Off.")
- 401 Unauthorized: an id that is not the user's
"""

from __future__ import annotations

from datetime import UTC, datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync import ApiCallRejectedError
from evohomeasync.schemas import (
    TccFailureCode,
    TccSetpointStatus,
    TccThermostatMode,
    _TaskIdT,
)
from tests.const import URL_BASE_V1

from .vendor import ZON_ID, ZON_ID_2

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from evohomeasync import ControlSystem, Zone
    from evohomeasync.schemas import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


TASK: Final[TccTaskResponseT] = {"id": _TaskIdT(1234567890)}

URL_ZON_MODE: Final = (
    f"{URL_BASE_V1}/devices/{ZON_ID}/thermostat/changeableValues/heatSetpoint"
)

# the location is in GMT Standard Time (i.e. Europe/London): in July, that is BST
_UNTIL_IN_BST: Final = dt(2026, 7, 1, 21, tzinfo=UTC)  # i.e. 22:00 local
_UNTIL_IN_GMT: Final = dt(2026, 11, 1, 21, tzinfo=UTC)  # i.e. 21:00 local


@pytest.mark.parametrize(
    ("status", "value", "next_time", "body"),
    [
        pytest.param(
            TccSetpointStatus.HOLD,
            19.5,
            None,
            {"status": "Hold", "value": 19.5},
            id="hold",
        ),
        pytest.param(  # the nextTime is local time (here, BST), without a Z
            TccSetpointStatus.TEMPORARY,
            19.5,
            _UNTIL_IN_BST,
            {"status": "Temporary", "value": 19.5, "nextTime": "2026-07-01T22:00:00"},
            id="temporary",
        ),
        pytest.param(
            TccSetpointStatus.SCHEDULED,
            None,
            None,
            {"status": "Scheduled"},
            id="scheduled",
        ),
    ],
)
async def test_set_heat_setpoint(
    *,  # keyword-only, as pytest passes them by name
    zone: Zone,
    mock: AioResponses,
    status: TccSetpointStatus,
    value: float | None,
    next_time: dt | None,
    body: dict[str, object],
) -> None:
    """Zone._set_heat_setpoint() sends only the keys it is given (camelCase)."""

    mock.put(URL_ZON_MODE, status=HTTPStatus.CREATED, payload=TASK)

    task = await zone._set_heat_setpoint(status, value=value, next_time=next_time)

    mock.assert_called_once_with(URL_ZON_MODE, HTTPMethod.PUT, json=body)
    assert task.id == str(TASK["id"])


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda zone: zone.set_temperature(19.5),
            {"status": "Hold", "value": 19.5},
            id="set_temperature",
        ),
        pytest.param(  # in GMT, local time is UTC
            lambda zone: zone.set_temperature(19.5, until=_UNTIL_IN_GMT),
            {"status": "Temporary", "value": 19.5, "nextTime": "2026-11-01T21:00:00"},
            id="set_temperature_until_gmt",
        ),
        pytest.param(  # in BST, local time is UTC+1
            lambda zone: zone.set_temperature(19.5, until=_UNTIL_IN_BST),
            {"status": "Temporary", "value": 19.5, "nextTime": "2026-07-01T22:00:00"},
            id="set_temperature_until_bst",
        ),
        pytest.param(  # no value (the older client sent "Value": None)
            lambda zone: zone.set_zone_auto(),
            {"status": "Scheduled"},
            id="set_zone_auto",
        ),
    ],
)
async def test_set_temperature(
    zone: Zone,
    mock: AioResponses,
    call: Callable[[Zone], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """The public methods PUT the setpoint as below (each its own body)."""

    mock.put(URL_ZON_MODE, status=HTTPStatus.CREATED, payload=TASK)

    await call(zone)

    mock.assert_called_once_with(URL_ZON_MODE, HTTPMethod.PUT, json=body)


async def test_changeable_values(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A zone's setpoint can also be PUT via its changeableValues (with its mode).

    The client does not do so, so this is via Auth.put().
    """

    url = f"devices/{ZON_ID}/thermostat/changeableValues"
    mock.put(f"{URL_BASE_V1}/{url}", status=HTTPStatus.CREATED, payload=TASK)

    await zone._auth.put(
        url,
        {
            "mode": TccThermostatMode.OFF,  # i.e. the zone's current mode
            "heat_setpoint": {
                "value": None,
                "status": TccSetpointStatus.SCHEDULED,
                "next_time": None,
            },
        },
    )

    mock.assert_called_once_with(
        f"{URL_BASE_V1}/{url}",
        HTTPMethod.PUT,
        json={
            "mode": "Off",
            "heatSetpoint": {"value": None, "status": "Scheduled", "nextTime": None},
        },
    )


async def test_set_zone_auto_device_is_lost(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """A PUT to a zone that is not alive is a 400 (DeviceIsLost), whatever the body."""

    zone = tcs.zone_by_id[str(ZON_ID_2)]  # its isAlive is false

    url = f"{URL_BASE_V1}/devices/{ZON_ID_2}/thermostat/changeableValues/heatSetpoint"
    body: list[TccFailureResponseT] = [
        {"code": TccFailureCode.DEVICE_IS_LOST, "message": "Device is lost."}
    ]
    mock.put(url, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await zone.set_zone_auto()

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": TccFailureCode.DEVICE_IS_LOST}


# provenance: probed 2026-11-13 (of a lost zone, so each began with a DeviceIsLost,
# which is omitted here)
@pytest.mark.parametrize(
    ("url", "json", "body"),
    [
        pytest.param(
            f"devices/{ZON_ID}/thermostat/changeableValues/heatSetpoint",
            {"status": TccSetpointStatus.HOLD},
            [
                {
                    "code": TccFailureCode.PARAMETER_IS_MISSING,
                    "message": "'Value' is required.",
                },
                {
                    "code": "ValueOutOfRange",  # not (yet) a TccFailureCode
                    "message": "Value of field Value is out of range.",
                },
            ],
            id="value_is_missing",
        ),
        pytest.param(
            f"devices/{ZON_ID}/thermostat/changeableValues/heatSetpoint",
            {"status": "NoSuchStatus"},
            [
                {
                    "code": TccFailureCode.INVALID_INPUT,
                    "message": 'Error converting value "NoSuchStatus" to type '
                    "'System.Nullable`1[TrueHome.WebApi.Models.SetpointStatus]'. "
                    "Path 'status', line 1, position 25.",
                },
            ],
            id="invalid_input",
        ),
        pytest.param(  # a ThermostatMode, but not of an evohome zone
            f"devices/{ZON_ID}/thermostat/changeableValues",
            {"mode": "Cool"},
            [
                {
                    "code": TccFailureCode.PARAMETER_IS_MISSING,
                    "message": "'HeatSetpoint' is required.",
                },
                {
                    "code": "ThermostatModeNotAllowed",  # not (yet) a TccFailureCode
                    "message": "Mode Cool is not allowed. Allowed modes are Heat, Off.",
                },
            ],
            id="mode_not_allowed",
        ),
    ],
)
async def test_put_rejected(
    zone: Zone,
    mock: AioResponses,
    url: str,
    json: dict[str, object],
    body: list[TccFailureResponseT],
) -> None:
    """A bad request is a 400, with every error of its body (the first is the code).

    Via Auth.put(), as the client would not send such a request.
    """

    mock.put(f"{URL_BASE_V1}/{url}", status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await zone._auth.put(url, json)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": body[0]["code"]}
    assert all(e["code"] in err.value.message for e in body)  # all are kept
