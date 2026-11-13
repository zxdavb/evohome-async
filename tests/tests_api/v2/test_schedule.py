"""Test the v2 GET and PUT of a zone's (or a DHW's) schedule.

  GET  /temperatureZone/{zon_id}/schedule
  PUT  /temperatureZone/{zon_id}/schedule
  GET  /domesticHotWater/{dhw_id}/schedule
  PUT  /domesticHotWater/{dhw_id}/schedule

A schedule is a week of days, each with its switchpoints, and is PUT in the same form
as it is got (the PUT is answered 201 with a comm task: see test_comm_task.py):
  {"dailySchedules": [
     {"dayOfWeek": "Monday",
      "switchpoints": [{"heatSetpoint": 19.0, "timeOfDay": "06:30:00"}, ...]},
     ...]}
A DHW's switchpoints have a dhwState ("On"/"Off"), not a heatSetpoint. The keys are
camelCase, the dayOfWeek is a name (not an ordinal), a heatSetpoint is a float, and a
timeOfDay is a str ("HH:MM:SS"). The client gets it with its keys (and enums)
snake_cased, and sends it back as the vendor's.

The vendor's errors:
- 400 ParameterIsMissing: a null body (with its parameterName, request)
- 400 DayOfWeekMissing: a body without its days, e.g. {}
- 400 ScheduleNotFound: a GET of a zone's schedule with an id that is the user's but not
  of a zone with a schedule (e.g. a TCS's id, or that of a zone that has none)
- 400 DHWNotFound: a GET of a DHW's schedule with an id of another type (e.g. a zone's)
- 401 Unauthorized: an id that is not the user's (a GET or a PUT)

The client raises an InvalidGetScheduleError for a 400 of the GET (its reason is
SCHEDULE_MISSING), and any other error as is.
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import (
    ApiCallFailedError,
    ApiCallRejectedError,
    DayOfWeek,
    DhwState,
    InvalidGetScheduleError,
    ResponseErrorReason,
)
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import URL_BASE_V2

from .vendor import DHW_ID, DHW_SCHEDULE, NOT_THE_USERS_ID, ZON_ID, ZON_SCHEDULE

if TYPE_CHECKING:
    from evohomeasync2 import HotWater, Zone
    from evohomeasync2.schemas.account import TccFailureResponseT, TccTaskResponseT
    from tests.tests.aioresponses import AioResponses


TASK: Final[TccTaskResponseT] = {"id": "1668279943"}

URL_ZON_SCHEDULE: Final = f"{URL_BASE_V2}/temperatureZone/{ZON_ID}/schedule"
URL_DHW_SCHEDULE: Final = f"{URL_BASE_V2}/domesticHotWater/{DHW_ID}/schedule"


async def test_zone_get_schedule(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A zone's schedule is a 200; the client snake_cases its keys and enums."""

    mock.get(URL_ZON_SCHEDULE, payload=ZON_SCHEDULE)

    schedule = await zone.get_schedule()

    mock.assert_called_once_with(URL_ZON_SCHEDULE, HTTPMethod.GET, json=None)

    assert [d["day_of_week"] for d in schedule] == list(DayOfWeek)  # Monday first
    assert schedule[0]["switchpoints"][0] == {
        "heat_setpoint": 19.0,
        "time_of_day": "06:30:00",
    }


async def test_dhw_get_schedule(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A DHW's schedule is a 200; its switchpoints have a dhwState."""

    mock.get(URL_DHW_SCHEDULE, payload=DHW_SCHEDULE)

    schedule = await dhw.get_schedule()

    mock.assert_called_once_with(URL_DHW_SCHEDULE, HTTPMethod.GET, json=None)

    assert [d["day_of_week"] for d in schedule] == list(DayOfWeek)
    assert schedule[0]["switchpoints"][0] == {
        "dhw_state": DhwState.ON,
        "time_of_day": "06:30:00",
    }


async def test_zone_set_schedule(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A zone's schedule is PUT as it was got (the vendor's form), and is a 201."""

    mock.get(URL_ZON_SCHEDULE, payload=ZON_SCHEDULE)
    mock.put(URL_ZON_SCHEDULE, status=HTTPStatus.CREATED, payload=TASK)

    task = await zone.set_schedule(await zone.get_schedule())

    mock.assert_any_call(URL_ZON_SCHEDULE, HTTPMethod.PUT, json=ZON_SCHEDULE)
    assert task.id == TASK["id"]


async def test_dhw_set_schedule(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A DHW's schedule is PUT as it was got (the vendor's form), and is a 201."""

    mock.get(URL_DHW_SCHEDULE, payload=DHW_SCHEDULE)
    mock.put(URL_DHW_SCHEDULE, status=HTTPStatus.CREATED, payload=TASK)

    task = await dhw.set_schedule(await dhw.get_schedule())

    mock.assert_any_call(URL_DHW_SCHEDULE, HTTPMethod.PUT, json=DHW_SCHEDULE)
    assert task.id == TASK["id"]


async def test_zone_get_schedule_not_found(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A zone without a schedule is a 400 (ScheduleNotFound).

    For example, a ghost zone (one that is in the config, but not in the controller),
    or the id of a TCS as a zone's. The client raises an InvalidGetScheduleError.
    """

    body: list[TccFailureResponseT] = [
        {"code": TccFailureCode.SCHEDULE_NOT_FOUND, "message": "Schedule not found."}
    ]
    mock.get(URL_ZON_SCHEDULE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(InvalidGetScheduleError) as err:
        await zone.get_schedule()

    assert err.value.reason is ResponseErrorReason.SCHEDULE_MISSING
    assert isinstance(err.value.__cause__, ApiCallRejectedError)
    assert err.value.__cause__.details == {"code": TccFailureCode.SCHEDULE_NOT_FOUND}


async def test_dhw_get_schedule_not_found(
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """A DHW's schedule, of an id that is not a DHW's, is a 400 (DHWNotFound)."""

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.DHW_NOT_FOUND,
            "message": f"Domestic Hot Water {DHW_ID} not found.",
        }
    ]
    mock.get(URL_DHW_SCHEDULE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(InvalidGetScheduleError) as err:
        await dhw.get_schedule()

    assert err.value.reason is ResponseErrorReason.SCHEDULE_MISSING


async def test_get_schedule_not_the_users(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401: it is raised as is."""

    url = f"temperatureZone/{NOT_THE_USERS_ID}/schedule"
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.get(f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)
    mock.put(f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)

    with pytest.raises(ApiCallFailedError) as err:
        await zone._auth.get(url, schema=zone.SCH_SCHEDULE)

    assert err.value.status == HTTPStatus.UNAUTHORIZED

    with pytest.raises(ApiCallFailedError) as err:  # a PUT too
        await zone._auth.put(url, ZON_SCHEDULE)

    assert err.value.status == HTTPStatus.UNAUTHORIZED


async def test_put_schedule_without_days(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A schedule without its days is a 400 (DayOfWeekMissing)."""

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.DAY_OF_WEEK_MISSING,
            "message": "One or more days missing.",
        }
    ]
    mock.put(URL_ZON_SCHEDULE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await zone._auth.put(f"temperatureZone/{ZON_ID}/schedule", {})

    mock.assert_called_once_with(URL_ZON_SCHEDULE, HTTPMethod.PUT, json={})
    assert err.value.details == {"code": TccFailureCode.DAY_OF_WEEK_MISSING}


async def test_put_schedule_null(
    zone: Zone,
    mock: AioResponses,
) -> None:
    """A null body is a 400 (ParameterIsMissing, with its parameterName: request)."""

    # NOTE: not a list[TccFailureResponseT], as that lacks parameterName (B1)
    body = [
        {
            "code": "ParameterIsMissing",
            "parameterName": "request",
            "message": "Parameter is missing.",
        }
    ]
    mock.put(URL_ZON_SCHEDULE, status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await zone._auth.request(HTTPMethod.PUT, f"temperatureZone/{ZON_ID}/schedule")

    mock.assert_called_once_with(URL_ZON_SCHEDULE, HTTPMethod.PUT, json=None)
    assert err.value.details == {"code": TccFailureCode.PARAMETER_IS_MISSING}
