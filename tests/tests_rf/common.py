"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import functools
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, overload

import pytest

import evohomeasync as evo0
import evohomeasync2 as evo2
from evohomeasync.schemas import TCC_GET_COMM_TASK
from evohomeasync2.comm_task import DEFAULT_INTERVAL
from tests.const import (
    _DBG_DISABLE_STRICT_ASSERTS,
    _DBG_USE_REAL_AIOHTTP,
    _DBG_WAIT_FOR_COMM_TASKS,
    TEST_LOC_IDX,
    TIMEOUT_COMM_TASK,
    TIMEOUT_COMM_TASK_V0,
    URL_BASE_V0,
    URL_BASE_V2,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from _evohome.helpers import Validator
    from evohomeasync import EvohomeClient as EvohomeClientV0
    from evohomeasync.schemas import TccCommTaskResponseT, TccDeviceResponseT
    from evohomeasync2 import EvohomeClient as EvohomeClientV2

if _DBG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .faked_server import aiohttp  # type: ignore[no-redef]


@overload
def get_loc(evo: EvohomeClientV0) -> evo0.Location: ...


@overload
def get_loc(evo: EvohomeClientV2) -> evo2.Location: ...


def get_loc(evo: EvohomeClientV0 | EvohomeClientV2) -> evo0.Location | evo2.Location:
    """Return the Location object to test against (see TEST_LOC_IDX)."""
    return evo.locations[TEST_LOC_IDX]


def get_dhw(evo: EvohomeClientV2) -> evo2.HotWater | None:
    """Return the first DHW object found across all TCSs of the location under test."""
    for gwy in get_loc(evo).gateways:
        for tcs in gwy.systems:
            if tcs.hotwater:
                return tcs.hotwater
    return None


def get_zon(evo: EvohomeClientV2) -> evo2.Zone | None:
    """Return the first Zone object found across all TCSs of the location under test."""
    for gwy in get_loc(evo).gateways:
        for tcs in gwy.systems:
            if tcs.zones:
                return tcs.zones[0]
    return None


# NOTE: Global flag to indicate if AuthenticationFailedError has been encountered
global_auth_failed = False


# decorator to skip remaining tests if an AuthenticationFailedError is encountered
def skipif_auth_failed[**P](
    fnc: Callable[P, Awaitable[Any]],
) -> Callable[P, Awaitable[Any]]:
    """Decorator to skip tests if AuthenticationFailedError is encountered."""

    @functools.wraps(fnc)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        global global_auth_failed  # noqa: PLW0603

        if global_auth_failed:
            pytest.skip("Unable to authenticate")

        try:
            return await fnc(*args, **kwargs)

        except (
            evo0.AuthenticationFailedError,
            evo2.AuthenticationFailedError,
        ) as err:
            if not _DBG_USE_REAL_AIOHTTP:
                raise

            global_auth_failed = True
            pytest.fail(f"Unable to authenticate: {err}")

    return wrapper


def error_codes(response: object) -> list[str]:
    """Return the distinct error codes of a vendor error response (a list of dicts).

    Both APIs return errors in this form (although v2 may add a parameterName), e.g.:
      [{"code": "ForbiddenParameter", "message": "'Status' is forbidden."}]
      [{"code": "ParameterIsMissing", "parameterName": "Mode", "message": "..."}]
    """

    assert isinstance(response, list), response
    return sorted({str(err["code"]) for err in response})


# version 1 helpers ###################################################################


@overload
async def should_work_v0[T](
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: Validator[T],
) -> T: ...


@overload
async def should_work_v0(
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: None = None,
) -> dict[str, Any] | list[dict[str, Any]] | str: ...


async def should_work_v0[T](
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: Validator[T] | None = None,
) -> T | dict[str, Any] | list[dict[str, Any]] | str:
    """Make a request that is expected to succeed.

    Used to document the behaviour of a 'real' server and to validate the faked server.
    """

    response: dict[str, Any] | list[dict[str, Any]] | str  # JSON or text

    async with auth.websession.request(
        method, f"{URL_BASE_V0}/{url}", json=json, headers=await auth._headers()
    ) as rsp:
        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            response = await rsp.json()
        else:
            response = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK (a GET), or 201/Created (a PUT)
        except aiohttp.ClientResponseError as err:
            pytest.fail(f"status={err.status}: {response}")

        assert rsp.content_type == content_type

        if rsp.content_type != "application/json":
            if schema:  # a schema is only for JSON
                pytest.fail(f"response is not JSON, so can't validate: {response}")
            assert isinstance(response, str)  # mypy
            return response

        assert isinstance(response, dict | list)  # mypy
        return schema(response) if schema else response


async def should_fail_v0(
    auth: evo0.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | str:
    """Make a request that is expected to fail.

    Used to document the behaviour of a 'real' server and to validate the faked server.
    """

    response: dict[str, Any] | list[dict[str, Any]] | str  # JSON or text

    rsp = await auth.websession.request(
        method, f"{URL_BASE_V0}/{url}", json=json, headers=await auth._headers()
    )

    # need to do this before raise_for_status()
    if rsp.content_type == "application/json":
        response = await rsp.json()
    else:
        response = await rsp.text()

    assert rsp.content_type == content_type, response

    # beware if JSON not passed in (i.e. is None, c.f. should_work())
    with pytest.raises(aiohttp.ClientResponseError) as exc_info:
        rsp.raise_for_status()
    assert exc_info.value.status == status, exc_info.value.status

    if _DBG_DISABLE_STRICT_ASSERTS:
        return response

    if isinstance(response, dict):
        assert "message" in response, response

    elif isinstance(response, list):
        assert "message" in response[0], response[0]

    elif isinstance(response, str):
        assert status == HTTPStatus.NOT_FOUND, status
        # '<!DOCTYPE html PUBLIC ... not found ...'

    else:
        pytest.fail(f"Did not return expected response: {rsp.content_type}")

    return response


def is_zone_v0(dev: TccDeviceResponseT) -> bool:
    """Return True if a (vendor-cased) v0 device is an evohome zone."""
    # Honeywell TH9320WF3003 can send thermostatModelType as an int, so guard startswith()
    return isinstance(t := dev["thermostatModelType"], str) and t.startswith("EMEA_")


def is_dhw_v0(dev: TccDeviceResponseT) -> bool:
    """Return True if a (vendor-cased) v0 device is an evohome DHW."""
    return dev["thermostatModelType"] == "DOMESTIC_HOT_WATER"


def is_alive_v0(dev: TccDeviceResponseT) -> bool:
    """Return True if a (vendor-cased) v0 device is alive (i.e. its gateway is online).

    The vendor rejects any PUT to a device that is not alive: 400, "DeviceIsLost".
    """
    return dev.get("isAlive") is True


def status_of_v0(dev: TccDeviceResponseT) -> str | None:
    """Return the status of a (vendor-cased) v0 zone or DHW, e.g. "Scheduled".

    A zone's is under changeableValues.heatSetpoint, a DHW's under changeableValues.
    """

    values: dict[str, Any] = dict(dev["thermostat"].get("changeableValues", {}))
    if not is_dhw_v0(dev):
        values = values.get("heatSetpoint", {})
    return None if (status := values.get("status")) is None else str(status)


def task_id_v0(response: object) -> str:
    """Return the id of the comm task that a v0 PUT returns (a dict, or a list of one).

    e.g. {"id": 1234567890} (an int); the older (non-async) client also allowed for a
    list of one, i.e. [{"id": 1234567890}].
    """

    task = response[0] if isinstance(response, list) else response
    assert isinstance(task, dict), response
    assert "id" in task, response
    return str(task["id"])


# a tolerance for the difference between the vendor's clock and ours
_CLOCK_SKEW: Final = td(seconds=5)


def is_stale_task_v0(task: Mapping[str, Any], sent: dt) -> bool:
    """Return True if a v0 comm task had started before its PUT was sent.

    The vendor sometimes answers a v0 PUT with the comm task of an earlier, equivalent
    PUT to the same device (a task that has already succeeded), and does not apply it,
    even if the device's state has changed since. This is how to detect that it has.

    The rule for when it does so is not known. It has been seen repeatedly for a revert
    to schedule (which has only the one form), and sometimes for an override (but never
    for one with a NextTime not used before), from seconds to minutes after the earlier
    PUT, but not always. The two PUTs need not be identical: e.g. they have differed in
    their key casing, and in having a null key vs not having that key at all.
    """

    started = dt.fromisoformat(task["started"]).replace(tzinfo=UTC)  # TZ-naive UTC
    return started < sent - _CLOCK_SKEW


async def wait_for_comm_task_v0(
    auth: evo0.auth.Auth, task_id: str
) -> TccCommTaskResponseT:
    """Wait for a v0 communication task (API call) to succeed, and return it.

    GET /commTasks?commTaskId={task_id} returns the state of the comm task (as returned
    by a PUT), and what it acted upon (but not the task's own id):
      {
        "state": "Succeeded",
        "started": "2026-09-22T20:08:04.053",  # TZ-naive
        "finished": "2026-09-22T20:08:07.13",  # TZ-naive, and only once finished
        "macId": "00D02D67C990",
        "gatewayId": 2678129,
        "deviceId": 6860918,
        "activityId": "0187be9d-1f3c-41e7-abd6-28f5442feddd"
      }

    Only "Succeeded" is known to be terminal: the older (non-async) client polled until
    it saw it, and its tests used "pending" otherwise. No other states are documented.

    Unlike the v2 tests, always waits (the caller needs the succeeded task), and skips
    the test if it has not succeeded within TIMEOUT_COMM_TASK_V0 seconds.
    """

    url = f"commTasks?commTaskId={task_id}"

    async def poll() -> TccCommTaskResponseT:
        while True:
            task = await should_work_v0(
                auth, HTTPMethod.GET, url, schema=TCC_GET_COMM_TASK
            )
            if task["state"] == "Succeeded":
                return task

            await asyncio.sleep(DEFAULT_INTERVAL)  # as per CommTask.wait()

    return await _wait_or_skip(poll(), task_id, seconds=TIMEOUT_COMM_TASK_V0)


# version 2 helpers ###################################################################


@overload
async def should_work_v2[T](
    auth: evo2.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: Validator[T],
) -> T: ...


@overload
async def should_work_v2(
    auth: evo2.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: None = None,
) -> dict[str, Any] | list[dict[str, Any]] | str: ...


async def should_work_v2[T](
    auth: evo2.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    schema: Validator[T] | None = None,
) -> T | dict[str, Any] | list[dict[str, Any]] | str:
    """Make a HTTP request and check it succeeds as expected.

    Used to document the behaviour of a 'real' server and to validate the faked server.

    After a PUT, wait for its comm task to succeed (see wait_for_comm_task_id()).
    """

    response: dict[str, Any] | list[dict[str, Any]] | str  # JSON or text

    async with auth.websession.request(
        method, f"{URL_BASE_V2}/{url}", json=json, headers=await auth._headers()
    ) as rsp:
        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            response = await rsp.json()
        else:
            response = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK (a GET), or 201/Created (a PUT)
        except aiohttp.ClientResponseError as err:
            pytest.fail(f"status={err.status}: {response}")

        assert rsp.content_type == content_type, response

        if rsp.content_type != "application/json":
            if schema:  # a schema is only for JSON
                pytest.fail(f"response is not JSON, so can't validate: {response}")
            assert isinstance(response, str)  # mypy
            return response

        assert isinstance(response, dict | list)  # mypy

    if method == HTTPMethod.PUT:
        task = response[0] if isinstance(response, list) else response
        await wait_for_comm_task_id(auth, task["id"])  # e.g. {"id": "1668279943"}

    return schema(response) if schema else response  # may raise vol.Invalid


async def should_fail_v2(
    auth: evo2.auth.Auth,
    method: HTTPMethod,
    url: str,
    /,
    *,
    json: Mapping[str, object] | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | str:
    """Make a HTTP request and check it fails as expected.

    Used to document the behaviour of a 'real' server and to validate the faked server.
    """

    response: dict[str, Any] | list[dict[str, Any]] | str  # JSON or text

    rsp = await auth.websession.request(
        method, f"{URL_BASE_V2}/{url}", json=json, headers=await auth._headers()
    )

    # need to do this before raise_for_status()
    if rsp.content_type == "application/json":
        response = await rsp.json()
    else:
        response = await rsp.text()

    # beware if JSON not passed in (i.e. is None, c.f. should_work())
    with pytest.raises(aiohttp.ClientResponseError) as exc_info:
        rsp.raise_for_status()
    assert exc_info.value.status == status, exc_info.value.status

    assert rsp.content_type == content_type, response

    if _DBG_DISABLE_STRICT_ASSERTS:
        return response

    if isinstance(response, dict):
        assert status in (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.METHOD_NOT_ALLOWED,
        ), response
        assert "message" in response, response  # sometimes "code" too

    elif isinstance(response, list):
        assert status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,  # CommTaskNotFound
            HTTPStatus.UNAUTHORIZED,
        ), response
        assert "message" in response[0], response[0]  # sometimes "code" too

    elif isinstance(response, str):  # 404
        assert status == HTTPStatus.NOT_FOUND, status

    else:
        pytest.fail(f"status={status}: {response}")

    return response


# the id of the first comm task (if any) that did not succeed within its timeout
_timed_out_comm_tasks: Final[list[str]] = []


def timed_out_comm_task() -> str | None:
    """Return the id of the first comm task that timed out, if any (else None).

    After such a timeout, the gateway's queue of tasks is likely backed up, so the
    remaining real-API tests are skipped (see tests_rf/conftest.py).
    """
    return _timed_out_comm_tasks[0] if _timed_out_comm_tasks else None


async def _wait_or_skip[T](
    wait: Awaitable[T], task_id: str, *, seconds: float = TIMEOUT_COMM_TASK
) -> T:
    """Await a wait for a comm task to succeed, within the given seconds.

    Returns what the wait returns (e.g. the succeeded task).

    If the task has not succeeded by then (the vendor's gateway may be slow), skip the
    test (and, via timed_out_comm_task(), all those after it): that is not a failure of
    the test. Any other TimeoutError (e.g. of a request, within TIMEOUT_REAL_AIOHTTP
    seconds) is raised.
    """

    cm = asyncio.timeout(seconds)

    try:
        async with cm:
            return await wait
    except TimeoutError:
        if not cm.expired():
            raise
        _timed_out_comm_tasks.append(task_id)
        pytest.skip(f"Comm task {task_id} did not succeed within {seconds}s")


async def wait_for_comm_task_id(auth: evo2.auth.Auth, task_id: str) -> None:
    """Wait for a comm task (i.e. of an earlier PUT) to succeed.

    Only if _DBG_WAIT_FOR_COMM_TASKS (and against the vendor's server), poll the task's
    state until it succeeds, and skip the test if it has not done so within
    TIMEOUT_COMM_TASK seconds. Otherwise, do nothing (not even check its state once).
    """

    if not (_DBG_USE_REAL_AIOHTTP and _DBG_WAIT_FOR_COMM_TASKS):
        return

    url = f"commTasks?commTaskId={task_id}"

    async def poll() -> None:
        while True:
            response = await should_work_v2(auth, HTTPMethod.GET, url)
            # {'commtaskId': '840367013', 'state': 'Created'}
            # {'commtaskId': '840367013', 'state': 'Running'}
            # {'commtaskId': '840367013', 'state': 'Succeeded'}

            task = response[0] if isinstance(response, list) else response
            assert isinstance(task, dict), task  # mypy  # TODO: use a SCHEMA
            assert task["commtaskId"] == task_id, task

            if task["state"] == "Succeeded":
                return

            if task["state"] not in ("Created", "Running"):
                pytest.fail(f"Unexpected task state: {task}")

            await asyncio.sleep(DEFAULT_INTERVAL)  # as per CommTask.wait()

    await _wait_or_skip(poll(), task_id)


async def wait_for_comm_task_obj(task: evo2.CommTask) -> None:
    """Wait for the comm task returned by a client method (i.e. of its PUT) to succeed.

    Only if _DBG_WAIT_FOR_COMM_TASKS (and against the vendor's server), wait for the
    task to succeed, and skip the test if it has not done so within TIMEOUT_COMM_TASK
    seconds. Otherwise, do nothing (not even check its state once).
    """

    if not (_DBG_USE_REAL_AIOHTTP and _DBG_WAIT_FOR_COMM_TASKS):
        return

    await _wait_or_skip(task.wait(), task.id)
