"""Replay the recorded v2 requests against the vendor's servers (see tests/tests_api/v2).

Each request is as recorded (with the ids of the user under test), and its answer is
checked against the recording in status, content type and shape (not values). Every
PUT is made (as is), so changes the test system; its comm task is checked only if
_DBG_WAIT_FOR_COMM_TASKS (see conftest.py).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod as M, HTTPStatus as S
from typing import TYPE_CHECKING, Final

import pytest

from _evohome.helpers import TCC_DTM_STRFTIME
from evohomeasync2.auth import Auth
from evohomeasync2.schemas.account import (
    TCC_GET_COMM_TASK,
    TCC_GET_USR_ACCOUNT,
    TCC_TASK_RESPONSE,
)
from evohomeasync2.schemas.config import (
    TCC_GET_DHW_CONFIG,
    TCC_GET_GWY_CONFIG,
    TCC_GET_LOC_CONFIG,
    TCC_GET_TCS_CONFIG,
    TCC_GET_USR_LOCATIONS,
    TCC_GET_ZON_CONFIG,
)
from evohomeasync2.schemas.schedule import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE
from evohomeasync2.schemas.status import (
    TCC_GET_DHW_STATUS,
    TCC_GET_GWY_STATUS,
    TCC_GET_LOC_STATUS,
    TCC_GET_TCS_STATUS,
    TCC_GET_ZON_STATUS,
)
from tests.const import (
    _DBG_TEST_CRED_URLS,
    _DBG_USE_REAL_AIOHTTP,
    _DBG_WAIT_FOR_COMM_TASKS,
    HEADERS_BASE,
    HEADERS_CRED_V2,
    TIMEOUT_COMM_TASK,
    URL_BASE_V2,
    URL_CRED_V2,
)

from .common import Answer, Call, Expect, check, replay

if TYPE_CHECKING:
    import aiohttp

    from evohome_cli.auth import TokenCacheManager


pytestmark = pytest.mark.skipif(
    not _DBG_USE_REAL_AIOHTTP, reason="requires the vendor's servers"
)

_NOT_THE_USERS: Final = "1234567"  # an id that is not the user's (see vendor.py)

INC_TCS: Final = "includeTemperatureControlSystems=True"

UNAUTHORIZED: Final = Expect(S.UNAUTHORIZED, code="Unauthorized")
NOT_FOUND_HTML: Final = Expect(S.NOT_FOUND, html=True)
NOT_FOUND_JSON: Final = Expect(S.NOT_FOUND)
NOT_ALLOWED: Final = Expect(S.METHOD_NOT_ALLOWED)
SERVER_ERROR: Final = Expect(S.INTERNAL_SERVER_ERROR)
TASK: Final = Expect(S.CREATED, schema=TCC_TASK_RESPONSE)


def _bad(code: str) -> Expect:
    return Expect(S.BAD_REQUEST, code=code)


# the GETs (as per test_get.py, test_get_entity.py, test_schedule.py, test_comm_task.py)
GETS: Final = [
    pytest.param(
        Call(M.GET, "userAccount"),
        Expect(S.OK, schema=TCC_GET_USR_ACCOUNT),
        id="usr_account",
    ),
    pytest.param(
        Call(M.GET, f"location/installationInfo?userId={{usr}}&{INC_TCS}"),
        Expect(S.OK, schema=TCC_GET_USR_LOCATIONS),
        id="usr_locations",
    ),
    pytest.param(
        Call(M.GET, "location/installationInfo?userId={usr}"),
        Expect(S.OK, absent="temperatureControlSystems"),
        id="usr_locations_sans_tcss",
    ),
    pytest.param(
        Call(M.GET, f"location/{{loc}}/installationInfo?{INC_TCS}"),
        Expect(S.OK, schema=TCC_GET_LOC_CONFIG),
        id="loc_config",
    ),
    pytest.param(
        Call(M.GET, "location/{loc}/installationInfo"),
        Expect(S.OK, absent="temperatureControlSystems"),
        id="loc_config_sans_tcss",
    ),
    pytest.param(
        Call(M.GET, f"location/{{loc}}/status?{INC_TCS}"),
        Expect(S.OK, schema=TCC_GET_LOC_STATUS),
        id="loc_status",
    ),
    pytest.param(
        Call(M.GET, "location/{loc}/status"),
        Expect(S.OK, absent="temperatureControlSystems"),
        id="loc_status_sans_tcss",
    ),
    pytest.param(
        Call(M.GET, f"gateway/{{gwy}}/installationInfo?{INC_TCS}"),
        Expect(S.OK, schema=TCC_GET_GWY_CONFIG),
        id="gwy_config",
    ),
    pytest.param(
        Call(M.GET, "gateway/{gwy}/installationInfo"),
        Expect(S.OK, absent="temperatureControlSystems"),
        id="gwy_config_sans_tcss",
    ),
    pytest.param(
        Call(M.GET, f"gateway/{{gwy}}/status?{INC_TCS}"),
        Expect(S.OK, schema=TCC_GET_GWY_STATUS),
        id="gwy_status",
    ),
    pytest.param(
        Call(M.GET, "gateway/{gwy}/status"),
        Expect(S.OK, absent="temperatureControlSystems"),
        id="gwy_status_sans_tcss",
    ),
    pytest.param(
        Call(M.GET, "temperatureControlSystem/{tcs}/installationInfo"),
        Expect(S.OK, schema=TCC_GET_TCS_CONFIG),
        id="tcs_config",
    ),
    pytest.param(
        Call(M.GET, "temperatureControlSystem/{tcs}/status"),
        Expect(S.OK, schema=TCC_GET_TCS_STATUS),
        id="tcs_status",
    ),
    pytest.param(
        Call(M.GET, "temperatureZone/{zon}/installationInfo"),
        Expect(S.OK, schema=TCC_GET_ZON_CONFIG),
        id="zon_config",
    ),
    pytest.param(
        Call(M.GET, "temperatureZone/{zon}/status"),
        Expect(S.OK, schema=TCC_GET_ZON_STATUS),
        id="zon_status",
    ),
    pytest.param(
        Call(M.GET, "temperatureZone/{zon}/schedule"),
        Expect(S.OK, schema=TCC_GET_ZON_SCHEDULE),
        id="zon_schedule",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{dhw}/installationInfo"),
        Expect(S.OK, schema=TCC_GET_DHW_CONFIG),
        id="dhw_config",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{dhw}/status"),
        Expect(S.OK, schema=TCC_GET_DHW_STATUS),
        id="dhw_status",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{dhw}/schedule"),
        Expect(S.OK, schema=TCC_GET_DHW_SCHEDULE),
        id="dhw_schedule",
    ),
    # an unknown path, or a known path without its required query key
    pytest.param(Call(M.GET, "userXxxxxxx"), NOT_FOUND_HTML, id="unknown_path"),
    pytest.param(
        Call(M.GET, "location/installationInfo?xxxxXx=xxxxxxx"),
        NOT_FOUND_JSON,
        id="no_user_id",
    ),
    pytest.param(Call(M.GET, "location/{loc}"), NOT_FOUND_HTML, id="loc_no_verb"),
    pytest.param(
        Call(M.GET, "location/{loc}/xxxxxxx"), NOT_FOUND_HTML, id="loc_bad_verb"
    ),
    # an id that is not the user's (whether or not it exists)
    pytest.param(
        Call(M.GET, f"location/installationInfo?userId={_NOT_THE_USERS}&{INC_TCS}"),
        UNAUTHORIZED,
        id="usr_locations_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"location/{_NOT_THE_USERS}/installationInfo?{INC_TCS}"),
        UNAUTHORIZED,
        id="loc_config_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"location/{_NOT_THE_USERS}/status?{INC_TCS}"),
        UNAUTHORIZED,
        id="loc_status_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"temperatureControlSystem/{_NOT_THE_USERS}/status"),
        UNAUTHORIZED,
        id="tcs_status_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"temperatureZone/{_NOT_THE_USERS}/status"),
        UNAUTHORIZED,
        id="zon_status_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"temperatureZone/{_NOT_THE_USERS}/schedule"),
        UNAUTHORIZED,
        id="zon_schedule_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"domesticHotWater/{_NOT_THE_USERS}/status"),
        UNAUTHORIZED,
        id="dhw_status_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"domesticHotWater/{_NOT_THE_USERS}/schedule"),
        UNAUTHORIZED,
        id="dhw_schedule_not_the_users",
    ),
    # an id that is not numeric
    pytest.param(
        Call(M.GET, "location/installationInfo?userId=xxxxxxx"),
        Expect(S.BAD_REQUEST),
        id="usr_locations_not_numeric",
    ),
    pytest.param(
        Call(M.GET, "location/xxxxxxx/status"),
        Expect(S.BAD_REQUEST),
        id="loc_status_not_numeric",
    ),
    # an id that is the user's, but of another type of entity
    pytest.param(
        Call(M.GET, "temperatureZone/{tcs}/status"),
        _bad("TemperatureZoneNotFound"),
        id="zon_status_of_tcs",
    ),
    pytest.param(
        Call(M.GET, "temperatureZone/{tcs}/schedule"),
        _bad("ScheduleNotFound"),
        id="zon_schedule_of_tcs",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{zon}/status"),
        _bad("DHWNotFound"),
        id="dhw_status_of_zon",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{zon}/schedule"),
        _bad("DHWNotFound"),
        id="dhw_schedule_of_zon",
    ),
    # the wrong method (a GET of a PUT-only URL, or vice versa)
    pytest.param(
        Call(M.GET, "temperatureControlSystem/{tcs}/mode"), NOT_ALLOWED, id="tcs_mode"
    ),
    pytest.param(
        Call(M.GET, "temperatureZone/{zon}/heatSetpoint"),
        NOT_FOUND_HTML,  # not a 405, unlike the others
        id="zon_heat_setpoint",
    ),
    pytest.param(
        Call(M.GET, "domesticHotWater/{dhw}/state"), NOT_ALLOWED, id="dhw_state"
    ),
    pytest.param(
        Call(M.PUT, "userAccount", json={}), NOT_ALLOWED, id="put_usr_account"
    ),
    pytest.param(
        Call(M.PUT, f"location/{{loc}}/status?{INC_TCS}", json={}),
        NOT_ALLOWED,
        id="put_loc_status",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/status", json={}),
        NOT_ALLOWED,
        id="put_dhw_status",
    ),
    # comm tasks (of no task, or with a bad id)
    pytest.param(
        Call(M.GET, "commTasks?commTaskId=12345678"),
        Expect(S.NOT_FOUND, code="CommTaskNotFound"),
        id="task_not_found",
    ),
    pytest.param(
        Call(M.GET, "commTasks?commTaskId=ABC"),
        _bad("InvalidInput"),
        id="task_not_numeric",
    ),
    pytest.param(
        Call(M.GET, "commTasks?commTaskId="),
        _bad("ParameterIsMissing"),
        id="task_empty",
    ),
    pytest.param(Call(M.GET, "commTasks"), NOT_FOUND_JSON, id="task_no_id"),
]

# the PUTs (as per test_tcs_put.py, test_zone_put.py, test_dhw_put.py, test_schedule.py)
PUTS: Final = [
    # a TCS's mode
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/mode",
            {"systemMode": "Away", "permanent": False, "timeUntil": "{until}"},
        ),
        TASK,
        id="tcs_away_temporary",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/mode",
            {"systemMode": "Auto", "permanent": True},
        ),
        TASK,
        id="tcs_auto",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/mode",
            {"systemMode": "Away", "permanent": False, "untilTime": "{until}"},
        ),
        _bad("SystemModeChangeTimeUntilNotSet"),
        id="tcs_until_time",
    ),
    pytest.param(
        Call(M.PUT, "temperatureControlSystem/{tcs}/mode", {}),
        _bad("ParameterIsMissing"),
        id="tcs_empty",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/mode",
            {"systemMode": "xxxxx", "permanent": True},
        ),
        _bad("InvalidInput"),
        id="tcs_invalid_mode",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/mode",
            {"systemMode": "Cool", "permanent": True},
        ),
        SERVER_ERROR,
        id="tcs_cool",
    ),
    pytest.param(
        Call(
            M.PUT,
            f"temperatureControlSystem/{_NOT_THE_USERS}/mode",
            {"systemMode": "Auto", "permanent": True},
        ),
        UNAUTHORIZED,
        id="tcs_not_the_users",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureControlSystem/{tcs}/systemMode",
            {"systemMode": "Auto", "permanent": True},
        ),
        NOT_FOUND_HTML,
        id="tcs_bad_verb",
    ),
    # a zone's mode
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 20.5,
                "timeUntil": "{until}",
            },
        ),
        TASK,
        id="zon_temporary",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "PermanentOverride", "HeatSetpointValue": 20.5},
        ),
        TASK,
        id="zon_permanent_pascal_case",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "FollowSchedule"},
        ),
        TASK,
        id="zon_follow_schedule",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "PermanentOverride"},
        ),
        _bad("HeatSetpointChangeTargetTemperatureNotSet"),
        id="zon_no_value",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "TemporaryOverride", "heatSetpointValue": 19.5},
        ),
        _bad("HeatSetpointChangeTimeUntilNotSet"),
        id="zon_no_until",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {
                "setpointMode": "TemporaryOverride",
                "heatSetpointValue": 19.5,
                "untilTime": "{until}",
            },
        ),
        _bad("HeatSetpointChangeTimeUntilNotSet"),
        id="zon_until_time",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "permanentoverride"},  # lower case is recognised...
        ),
        _bad("HeatSetpointChangeTargetTemperatureNotSet"),
        id="zon_lower_case",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": "permanent_override"},  # ...but snake_case is not
        ),
        _bad("InvalidInput"),
        id="zon_snake_case",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {
                "setpointMode": "AdvancedOverride",
                "heatSetpointValue": 20.0,
                "timeUntil": "{until}",
            },
        ),
        _bad("InvalidInput"),
        id="zon_advanced_override",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {"setpointMode": 4, "heatSetpointValue": 20.0, "timeUntil": "{until}"},
        ),
        SERVER_ERROR,
        id="zon_mode_as_int",
    ),
    pytest.param(
        Call(
            M.PUT,
            "temperatureZone/{zon}/heatSetpoint",
            {
                "setpointMode": "VacationHold",
                "heatSetpointValue": 12.0,
                "timeUntil": "{until}",
            },
        ),
        Expect(S.CREATED, schema=TCC_TASK_RESPONSE, task="Failed"),
        id="zon_vacation_hold",
    ),
    pytest.param(
        Call(
            M.PUT,
            f"temperatureZone/{_NOT_THE_USERS}/heatSetpoint",
            {"setpointMode": "FollowSchedule"},
        ),
        UNAUTHORIZED,
        id="zon_not_the_users",
    ),
    # a DHW's mode
    pytest.param(
        Call(
            M.PUT,
            "domesticHotWater/{dhw}/state",
            {"mode": "TemporaryOverride", "state": "On", "untilTime": "{until}"},
        ),
        TASK,
        id="dhw_temporary",
    ),
    pytest.param(
        Call(
            M.PUT,
            "domesticHotWater/{dhw}/state",
            {"Mode": "PermanentOverride", "State": "Off"},
        ),
        TASK,
        id="dhw_permanent_pascal_case",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/state", {"mode": "FollowSchedule"}),
        TASK,
        id="dhw_follow_schedule",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/state", {}),
        _bad("ParameterIsMissing"),
        id="dhw_empty",
    ),
    pytest.param(
        Call(
            M.PUT,
            "domesticHotWater/{dhw}/state",
            {"state": "TemporaryOverride", "mode": "Off"},
        ),
        _bad("InvalidInput"),
        id="dhw_swapped",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/state", {"mode": "PermanentOverride"}),
        _bad("DHWStateNotSet"),
        id="dhw_no_state",
    ),
    pytest.param(
        Call(
            M.PUT,
            "domesticHotWater/{dhw}/state",
            {"mode": "TemporaryOverride", "state": "On", "timeUntil": "{until}"},
        ),
        _bad("DHWUntilTimeNotSet"),
        id="dhw_time_until",
    ),
    pytest.param(
        Call(
            M.PUT,
            f"domesticHotWater/{_NOT_THE_USERS}/state",
            {"mode": "FollowSchedule"},
        ),
        UNAUTHORIZED,
        id="dhw_not_the_users",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/mode", {"mode": "FollowSchedule"}),
        NOT_FOUND_HTML,
        id="dhw_bad_verb",
    ),
    # a schedule (PUT as it was got: so a no-op)
    pytest.param(
        Call(M.PUT, "temperatureZone/{zon}/schedule", "{zon_schedule}"),
        TASK,
        id="zon_schedule",
    ),
    pytest.param(
        Call(M.PUT, "temperatureZone/{zon}/schedule", {}),
        _bad("DayOfWeekMissing"),
        id="zon_schedule_empty",
    ),
    pytest.param(
        Call(M.PUT, f"temperatureZone/{_NOT_THE_USERS}/schedule", "{zon_schedule}"),
        UNAUTHORIZED,
        id="zon_schedule_not_the_users",
    ),
    pytest.param(
        Call(M.PUT, "domesticHotWater/{dhw}/schedule", "{dhw_schedule}"),
        TASK,
        id="dhw_schedule",
    ),
]


@pytest.fixture
def auth(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
) -> Auth:
    """Return the client's Auth (with its access token, from the cache if valid)."""
    return Auth(credentials_manager, client_session)


@pytest.fixture
async def ids(
    auth: Auth,
) -> dict[str, object]:
    """Return the ids of the user's first location, and its entities (and more).

    Also an until (an hour hence), and the schedules of its first zone and its DHW (to
    PUT back as they are). A key is absent if the location has no such entity.
    """

    usr = TCC_GET_USR_ACCOUNT(await auth._make_request(M.GET, "userAccount"))
    locs = TCC_GET_USR_LOCATIONS(
        await auth._make_request(
            M.GET, f"location/installationInfo?userId={usr['userId']}&{INC_TCS}"
        )
    )

    gwy = locs[0]["gateways"][0]
    tcs = gwy["temperatureControlSystems"][0]

    result: dict[str, object] = {
        "usr": usr["userId"],
        "loc": locs[0]["locationInfo"]["locationId"],
        "gwy": gwy["gatewayInfo"]["gatewayId"],
        "tcs": tcs["systemId"],
        "zon": tcs["zones"][0]["zoneId"],
        "until": (dt.now(tz=UTC) + td(hours=1)).strftime(TCC_DTM_STRFTIME),
    }
    result["zon_schedule"] = await auth._make_request(
        M.GET, f"temperatureZone/{result['zon']}/schedule"
    )
    if "dhw" in tcs:
        result["dhw"] = tcs["dhw"]["dhwId"]
        result["dhw_schedule"] = await auth._make_request(
            M.GET, f"domesticHotWater/{result['dhw']}/schedule"
        )
    return result


async def _wait_for_task(
    auth: Auth,
    task_id: str,
) -> str:
    """Poll a comm task until it ends (its state is Succeeded or Failed).

    Return its final state, or skip the test after TIMEOUT_COMM_TASK seconds (e.g. as
    the gateway is offline, when its tasks never end).
    """

    try:
        async with asyncio.timeout(TIMEOUT_COMM_TASK):
            while True:
                task = TCC_GET_COMM_TASK(
                    await auth._make_request(M.GET, f"commTasks?commTaskId={task_id}")
                )
                if task["state"] in ("Succeeded", "Failed"):
                    return task["state"]
                await asyncio.sleep(1)
    except TimeoutError:
        pytest.skip(f"Comm task {task_id} did not end in {TIMEOUT_COMM_TASK}s")


@pytest.mark.parametrize(("call", "expect"), GETS + PUTS)
async def test_replay(
    auth: Auth,
    ids: dict[str, object],
    call: Call,
    expect: Expect,
) -> None:
    """The vendor answers each recorded request as recorded."""

    answer: Answer = await replay(auth, call, ids)

    check(answer, expect)

    if answer.status == S.CREATED and _DBG_WAIT_FOR_COMM_TASKS:
        state = await _wait_for_task(auth, answer.body["id"])
        assert state == expect.task, (call, answer)


async def test_comm_task_id_normalised(
    auth: Auth,
    ids: dict[str, object],
) -> None:
    """A zero-padded comm task id is that of the same task (its id is normalised)."""

    call = Call(
        M.PUT, "temperatureZone/{zon}/heatSetpoint", {"setpointMode": "FollowSchedule"}
    )
    answer = await replay(auth, call, ids)
    check(answer, TASK)

    task_id = answer.body["id"]
    task = TCC_GET_COMM_TASK(
        await auth._make_request(M.GET, f"commTasks?commTaskId=0{task_id}")
    )
    assert task["commtaskId"] == task_id


@pytest.mark.parametrize(
    "path",
    [
        "WebAPI/emea/api/v1/useraccount",
        "WebAPI/emea/api/v1/USERACCOUNT",
        "webapi/EMEA/API/V1/userAccount",
        "WEBAPI/EMEA/API/V1/USERACCOUNT",
    ],
)
async def test_url_case_insensitive(
    auth: Auth,
    path: str,
) -> None:
    """The path of a URL (including its base path) is case-insensitive."""

    url = f"{URL_BASE_V2.split('/WebAPI')[0]}/{path}"
    async with auth.websession.get(url, headers=await auth._headers({})) as rsp:
        assert rsp.status == S.OK, url
        TCC_GET_USR_ACCOUNT(await rsp.json())


@pytest.mark.parametrize(
    ("usr_key", "tcs_key"),
    [
        ("USERID", "INCLUDETEMPERATURECONTROLSYSTEMS"),
        ("userid", "includetemperaturecontrolsystems"),
        ("UserId", "IncludeTemperatureControlSystems"),
    ],
)
async def test_query_case_insensitive(
    auth: Auth,
    ids: dict[str, object],
    usr_key: str,
    tcs_key: str,
) -> None:
    """The query keys of a URL are case-insensitive (but are recognised)."""

    url = f"location/installationInfo?{usr_key}={{usr}}&{tcs_key}=True"
    check(
        await replay(auth, Call(M.GET, url), ids),
        Expect(S.OK, schema=TCC_GET_USR_LOCATIONS),
    )


async def test_bearer_invalid(
    client_session: aiohttp.ClientSession,
) -> None:
    """A bad access token is a 401 (Unauthorized, 'Unauthorized.')."""

    headers = HEADERS_BASE | {"Authorization": "bearer bad access token"}
    async with client_session.get(f"{URL_BASE_V2}/userAccount", headers=headers) as rsp:
        assert rsp.status == S.UNAUTHORIZED
        body = await rsp.json()

    assert body == [{"code": "Unauthorized", "message": "Unauthorized."}]


@pytest.mark.skipif(not _DBG_TEST_CRED_URLS, reason="may invalidate the token cache")
async def test_token(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """The token POST: a password grant, then a refresh grant (each a 200)."""

    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "Username": credentials[0],
        "Password": credentials[1],
    }
    async with client_session.post(
        URL_CRED_V2, headers=HEADERS_CRED_V2, data=data
    ) as rsp:
        assert rsp.status == S.OK
        token = await rsp.json()

    data = {
        "grant_type": "refresh_token",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "refresh_token": token["refresh_token"],
    }
    async with client_session.post(
        URL_CRED_V2, headers=HEADERS_CRED_V2, data=data
    ) as rsp:
        assert rsp.status == S.OK


@pytest.mark.skipif(not _DBG_TEST_CRED_URLS, reason="may invalidate the token cache")
async def test_token_invalid(
    client_session: aiohttp.ClientSession,
) -> None:
    """Bad credentials are a 400 (invalid_grant)."""

    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "Username": "x",
        "Password": "",
    }
    async with client_session.post(
        URL_CRED_V2, headers=HEADERS_CRED_V2, data=data
    ) as rsp:
        assert rsp.status == S.BAD_REQUEST
        assert await rsp.json() == {"error": "invalid_grant"}
