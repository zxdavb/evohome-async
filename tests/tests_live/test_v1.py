"""Replay the recorded v1 requests against the vendor's servers (see tests/tests_api/v1).

Each request is as recorded (with the ids of the user under test), and its answer is
checked against the recording in status, content type and shape (not values). Every
PUT is made (as is), so changes the test system; its comm task is checked only if
_DBG_WAIT_FOR_COMM_TASKS (see conftest.py).

A PUT to a device that is not alive (i.e. its gateway is offline) is a 400
(DeviceIsLost), whatever its body: so a PUT that would be a 201 is expected to be that,
if its device is lost (the test system's gateway has been offline since 2026-11-04).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod as M, HTTPStatus as S
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync.auth import _APPLICATION_ID, Auth
from evohomeasync.schemas import (
    TCC_GET_COMM_TASK,
    TCC_GET_USR_INFO,
    TCC_GET_USR_LOCS,
    TCC_POST_USR_SESSION,
    TCC_TASK_RESPONSE,
)
from tests.const import (
    _DBG_TEST_CRED_URLS,
    _DBG_USE_REAL_AIOHTTP,
    _DBG_WAIT_FOR_COMM_TASKS,
    HEADERS_BASE,
    HEADERS_CRED_V1,
    TIMEOUT_COMM_TASK_V1,
    URL_BASE_V1,
    URL_CRED_V1,
)

from .common import Answer, Call, Expect, check, replay

if TYPE_CHECKING:
    import aiohttp

    from evohome_cli.auth import TokenCacheManager


pytestmark = pytest.mark.skipif(
    not _DBG_USE_REAL_AIOHTTP, reason="requires the vendor's servers"
)

_NOT_THE_USERS: Final = "123456"  # an id that is not the user's (see vendor.py)

_LOCAL_STRFTIME: Final = "%Y-%m-%dT%H:%M:%S"  # i.e. a nextTime (local, without a Z)

NOT_FOUND_HTML: Final = Expect(S.NOT_FOUND, html=True)
NOT_FOUND_JSON: Final = Expect(S.NOT_FOUND)
TASK: Final = Expect(S.CREATED, schema=TCC_TASK_RESPONSE)
DEVICE_IS_LOST: Final = Expect(S.BAD_REQUEST, code="DeviceIsLost")


def _bad(code: str) -> Expect:
    return Expect(S.BAD_REQUEST, code=code)


def _loc(body: object) -> object:
    """Validate a location (as is a list of one, by its schema)."""
    return TCC_GET_USR_LOCS([body])


ZON_MODE: Final = "devices/{zon}/thermostat/changeableValues/heatSetpoint"
ZON_VALUES: Final = "devices/{zon}/thermostat/changeableValues"
DHW_VALUES: Final = "devices/{dhw}/thermostat/changeableValues"

# the GETs (as per test_get.py, test_get_device.py, test_comm_task.py, test_tcs_put.py)
GETS: Final = [
    pytest.param(
        Call(M.GET, "accountInfo"),
        Expect(S.OK, schema=TCC_GET_USR_INFO),
        id="account_info",
    ),
    pytest.param(
        Call(M.GET, "locations?userId={usr}&allData=True"),
        Expect(S.OK, schema=TCC_GET_USR_LOCS),
        id="locations",
    ),
    pytest.param(
        Call(M.GET, "locations?userId={usr}"),
        Expect(S.OK, absent='"devices"'),
        id="locations_sans_all_data",
    ),
    pytest.param(
        Call(M.GET, "locations?locationId={loc}&allData=True"),
        Expect(S.OK, schema=_loc),
        id="location",
    ),
    pytest.param(
        Call(M.GET, "locations?locationId={loc}"),
        Expect(S.OK, absent='"devices"'),
        id="location_sans_all_data",
    ),
    pytest.param(
        Call(M.GET, "gateways?locationId={loc}&allData=True"),
        Expect(S.OK),
        id="gateways",
    ),
    pytest.param(
        Call(M.GET, "gateways?locationId={loc}"),
        Expect(S.OK, absent='"devices"'),
        id="gateways_sans_all_data",
    ),
    pytest.param(
        Call(M.GET, "devices?locationId={loc}&allData=True"),
        Expect(S.OK),
        id="devices",
    ),
    pytest.param(
        Call(M.GET, "devices?locationId={loc}"),
        Expect(S.OK, absent='"thermostat"'),
        id="devices_sans_all_data",
    ),
    pytest.param(
        Call(M.GET, "devices/{zon}"),
        Expect(S.OK, absent='"thermostat"'),
        id="device",
    ),
    pytest.param(
        Call(M.GET, "devices/{zon}/thermostat"),
        Expect(S.OK, absent='"changeableValues"'),
        id="thermostat",
    ),
    pytest.param(Call(M.GET, ZON_VALUES), Expect(S.OK), id="changeable_values"),
    # the wrong method (a GET of a PUT-only URL, or vice versa)
    pytest.param(Call(M.GET, ZON_MODE), NOT_FOUND_HTML, id="get_heat_setpoint"),
    pytest.param(
        Call(M.PUT, "locations?userId={usr}&allData=True", {}),
        NOT_FOUND_JSON,
        id="put_locations",
    ),
    # an unknown path, or a known path without its required query key
    pytest.param(Call(M.GET, "xxxxxxx"), NOT_FOUND_HTML, id="unknown_path"),
    pytest.param(
        Call(M.GET, "locations?noSuchKey={usr}"), NOT_FOUND_JSON, id="no_user_id"
    ),
    # an id that is not the user's, or is not numeric
    pytest.param(
        Call(M.GET, f"locations?userId={_NOT_THE_USERS}&allData=True"),
        Expect(S.UNAUTHORIZED, code="Unauthorized"),
        id="locations_not_the_users",
    ),
    pytest.param(
        Call(M.GET, f"locations?userId='{_NOT_THE_USERS}'"),
        Expect(S.BAD_REQUEST),
        id="locations_not_numeric",
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
        Call(M.GET, "commTasks?commTaskId="), _bad("InvalidInput"), id="task_empty"
    ),
    pytest.param(Call(M.GET, "commTasks"), NOT_FOUND_JSON, id="task_no_id"),
    # the TCS's mode (its URL has been removed)
    pytest.param(
        Call(M.GET, "evoTouchSystems?locationId={loc}"),
        NOT_FOUND_HTML,
        id="get_tcs_mode",
    ),
    pytest.param(
        Call(
            M.PUT,
            "evoTouchSystems?locationId={loc}",
            {"QuickAction": "Auto", "QuickActionNextTime": None},
        ),
        NOT_FOUND_HTML,
        id="put_tcs_mode",
    ),
]

# the PUTs of a device (as per test_zone_put.py, test_dhw_put.py), each with the device
# that it is of (if its PUT is a 201, it is a DeviceIsLost if that device is lost)
PUTS: Final = [
    # a zone's setpoint
    pytest.param(
        Call(
            M.PUT,
            ZON_MODE,
            {
                "status": "Temporary",
                "value": "{zon_setpoint}",
                "nextTime": "{until_local}",
            },
        ),
        TASK,
        "zon",
        id="zon_temporary",
    ),
    pytest.param(
        Call(M.PUT, ZON_MODE, {"Status": "Hold", "Value": "{zon_setpoint}"}),
        TASK,
        "zon",
        id="zon_hold_pascal_case",
    ),
    pytest.param(
        Call(M.PUT, ZON_MODE, {"status": "Scheduled"}),
        TASK,
        "zon",
        id="zon_scheduled",
    ),
    pytest.param(  # the older client's body
        Call(M.PUT, ZON_MODE, {"Value": None, "Status": "Scheduled", "NextTime": None}),
        TASK,
        "zon",
        id="zon_scheduled_older_client",
    ),
    pytest.param(
        Call(
            M.PUT,
            ZON_VALUES,
            {
                "mode": "{zon_mode}",
                "heatSetpoint": {
                    "value": None,
                    "status": "Scheduled",
                    "nextTime": None,
                },
            },
        ),
        TASK,
        "zon",
        id="zon_changeable_values",
    ),
    pytest.param(
        Call(M.PUT, ZON_MODE, {"status": "Hold"}),
        _bad("ParameterIsMissing"),
        None,
        id="zon_hold_no_value",
    ),
    pytest.param(
        Call(M.PUT, ZON_MODE, {"STATUS": "hold"}),
        _bad("ParameterIsMissing"),
        None,
        id="zon_hold_upper_lower_case",
    ),
    pytest.param(
        Call(M.PUT, ZON_MODE, {"status": "NoSuchStatus"}),
        _bad("InvalidInput"),
        None,
        id="zon_invalid_status",
    ),
    pytest.param(
        Call(M.PUT, ZON_VALUES, {"mode": "Cool"}),
        _bad("ThermostatModeNotAllowed"),
        None,
        id="zon_mode_not_allowed",
    ),
    # a DHW's mode
    pytest.param(
        Call(M.PUT, DHW_VALUES, {"mode": "{dhw_mode}"}),
        TASK,
        "dhw",
        id="dhw_mode",
    ),
    pytest.param(
        Call(M.PUT, DHW_VALUES, {"Mode": "{dhw_mode}"}),
        TASK,
        "dhw",
        id="dhw_mode_pascal_case",
    ),
    pytest.param(  # the older client's body, without its Status
        Call(
            M.PUT,
            DHW_VALUES,
            {
                "Mode": "{dhw_mode}",
                "NextTime": None,
                "SpecialModes": None,
                "HeatSetpoint": None,
                "CoolSetpoint": None,
            },
        ),
        TASK,
        "dhw",
        id="dhw_older_client_sans_status",
    ),
    pytest.param(
        Call(M.PUT, DHW_VALUES, {}),
        _bad("ParameterIsMissing"),
        None,
        id="dhw_empty",
    ),
    pytest.param(
        Call(M.PUT, DHW_VALUES, {"mode": None}),
        _bad("ParameterIsMissing"),
        None,
        id="dhw_mode_null",
    ),
    pytest.param(  # on the test system
        Call(M.PUT, DHW_VALUES, {"mode": "{dhw_mode}", "status": "Hold"}),
        _bad("ForbiddenParameter"),
        None,
        id="dhw_status_forbidden",
    ),
    pytest.param(  # on the test system
        Call(M.PUT, DHW_VALUES, {"mode": "{dhw_mode}", "nextTime": "{until_local}"}),
        _bad("ForbiddenParameter"),
        None,
        id="dhw_next_time_forbidden",
    ),
    pytest.param(  # on the test system: the library's set_dhw_auto() (see O1)
        Call(M.PUT, DHW_VALUES, {"status": "Scheduled", "mode": None}),
        Expect(S.BAD_REQUEST),
        None,
        id="dhw_set_dhw_auto",
    ),
    pytest.param(
        Call(M.PUT, DHW_VALUES, {"mode": "Off"}),
        _bad("ThermostatModeNotAllowed"),
        None,
        id="dhw_mode_not_allowed",
    ),
    pytest.param(
        Call(M.PUT, DHW_VALUES, {"mode": "Auto"}),
        _bad("InvalidInput"),
        None,
        id="dhw_invalid_mode",
    ),
]


@pytest.fixture
def auth(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
) -> Auth:
    """Return the client's Auth (with its session id, from the cache if valid)."""
    return Auth(credentials_manager, client_session)


@pytest.fixture
async def ids(
    auth: Auth,
) -> dict[str, object]:
    """Return the ids of the user's first location, and its devices (and more).

    Also whether each device is alive, the first zone's current setpoint and mode, the
    DHW's current mode, and a nextTime (an hour hence, in the location's local time).
    A key is absent if the location has no such device.
    """

    usr = TCC_GET_USR_INFO(await auth._make_request(M.GET, "accountInfo"))
    locs = TCC_GET_USR_LOCS(
        await auth._make_request(
            M.GET, f"locations?userId={usr['userID']}&allData=True"
        )
    )

    loc = locs[0]
    offset = td(minutes=loc["timeZone"]["currentOffsetMinutes"])

    result: dict[str, object] = {
        "usr": usr["userID"],
        "loc": loc["locationID"],
        "until_local": (dt.now(tz=UTC) + offset + td(hours=1)).strftime(
            _LOCAL_STRFTIME
        ),
    }

    for dev in loc["devices"]:
        values = dict(dev["thermostat"]["changeableValues"])
        if dev["thermostatModelType"] == "DOMESTIC_HOT_WATER" and "dhw" not in result:
            result |= {"dhw": dev["deviceID"], "dhw_alive": dev["isAlive"]}
            result["dhw_mode"] = values["mode"]
        elif "zon" not in result:
            result |= {"zon": dev["deviceID"], "zon_alive": dev["isAlive"]}
            result["zon_mode"] = values["mode"]
            setpoint = values["heatSetpoint"]
            assert isinstance(setpoint, dict)  # mypy
            result["zon_setpoint"] = setpoint["value"]

    return result


async def _wait_for_task(
    auth: Auth,
    task_id: str,
) -> str:
    """Poll a comm task until it ends (its state is Succeeded or Failed).

    Return its final state, or skip the test after TIMEOUT_COMM_TASK_V1 seconds (e.g.
    as the gateway is offline, when its tasks never end).
    """

    try:
        async with asyncio.timeout(TIMEOUT_COMM_TASK_V1):
            while True:
                task = TCC_GET_COMM_TASK(
                    await auth._make_request(M.GET, f"commTasks?commTaskId={task_id}")
                )
                if task["state"] in ("Succeeded", "Failed"):
                    return task["state"]
                await asyncio.sleep(1)
    except TimeoutError:
        pytest.skip(f"Comm task {task_id} did not end in {TIMEOUT_COMM_TASK_V1}s")


async def _replay_and_check(
    auth: Auth,
    ids: dict[str, object],
    call: Call,
    expect: Expect,
) -> None:
    """Replay the request, check its answer, and (maybe) check its comm task."""

    answer: Answer = await replay(auth, call, ids)

    check(answer, expect)

    if answer.status == S.CREATED and _DBG_WAIT_FOR_COMM_TASKS:
        state = await _wait_for_task(auth, str(answer.body["id"]))
        assert state == expect.task, (call, answer)


@pytest.mark.parametrize(("call", "expect"), GETS)
async def test_replay_get(
    auth: Auth,
    ids: dict[str, object],
    call: Call,
    expect: Expect,
) -> None:
    """The vendor answers each recorded request as recorded."""

    await _replay_and_check(auth, ids, call, expect)


@pytest.mark.parametrize(("call", "expect", "device"), PUTS)
async def test_replay_put(
    auth: Auth,
    ids: dict[str, object],
    call: Call,
    expect: Expect,
    device: str | None,
) -> None:
    """The vendor answers each recorded PUT as recorded (DeviceIsLost if it is lost)."""

    if device is not None and ids.get(f"{device}_alive") is False:
        expect = DEVICE_IS_LOST

    await _replay_and_check(auth, ids, call, expect)


@pytest.mark.parametrize(
    "path",
    [
        "WebAPI/api/accountinfo",
        "WebAPI/api/ACCOUNTINFO",
        "webapi/API/accountInfo",
        "WEBAPI/API/ACCOUNTINFO",
    ],
)
async def test_url_case_insensitive(
    auth: Auth,
    path: str,
) -> None:
    """The path of a URL (including its base path) is case-insensitive."""

    url = f"{URL_BASE_V1.split('/WebAPI')[0]}/{path}"
    async with auth.websession.get(url, headers=await auth._headers({})) as rsp:
        assert rsp.status == S.OK, url
        TCC_GET_USR_INFO(await rsp.json())


@pytest.mark.parametrize(
    "url",
    [
        "locations?USERID={usr}&ALLDATA=True",
        "locations?userid={usr}&alldata=True",
        "LOCATIONS?UserId={usr}&AllData=True",
    ],
)
async def test_query_case_insensitive(
    auth: Auth,
    ids: dict[str, object],
    url: str,
) -> None:
    """The query keys of a URL are case-insensitive (but are recognised)."""

    check(
        await replay(auth, Call(M.GET, url), ids),
        Expect(S.OK, schema=TCC_GET_USR_LOCS),
    )


async def test_session_id_invalid(
    client_session: aiohttp.ClientSession,
) -> None:
    """A bad session id is a 401 (Unauthorized, 'Unauthorized')."""

    headers = HEADERS_BASE | {"sessionId": "bad session id"}
    async with client_session.get(f"{URL_BASE_V1}/accountInfo", headers=headers) as rsp:
        assert rsp.status == S.UNAUTHORIZED
        body = await rsp.json()

    assert body == [{"code": "Unauthorized", "message": "Unauthorized"}]


@pytest.mark.skipif(not _DBG_TEST_CRED_URLS, reason="may invalidate the token cache")
async def test_session(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """The session POST of good credentials is a 200."""

    data = {
        "applicationId": _APPLICATION_ID,
        "username": credentials[0],
        "password": credentials[1],
    }
    async with client_session.post(
        URL_CRED_V1, headers=HEADERS_CRED_V1, data=data
    ) as rsp:
        assert rsp.status == S.OK
        TCC_POST_USR_SESSION(await rsp.json())


@pytest.mark.skipif(not _DBG_TEST_CRED_URLS, reason="may invalidate the token cache")
async def test_session_invalid(
    client_session: aiohttp.ClientSession,
) -> None:
    """Bad credentials are a 401 (EmailOrPasswordIncorrect)."""

    data = {"applicationId": _APPLICATION_ID, "username": "x", "password": ""}
    async with client_session.post(
        URL_CRED_V1, headers=HEADERS_CRED_V1, data=data
    ) as rsp:
        assert rsp.status == S.UNAUTHORIZED
        body = await rsp.json()

    assert body[0]["code"] == "EmailOrPasswordIncorrect"
