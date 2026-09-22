"""evohome-async - helper functions."""

from __future__ import annotations

import asyncio
import functools
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, overload

import pytest

import evohomeasync as evo0
import evohomeasync2 as evo2
from evohomeasync2.const import SystemMode
from tests.const import (
    _DBG_DISABLE_STRICT_ASSERTS,
    _DBG_USE_REAL_AIOHTTP,
    URL_BASE_V0,
    URL_BASE_V2,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from _evohome.helpers import Validator
    from evohomeasync.schemas import TccDeviceResponseT
    from tests.conftest import EvohomeClientV2

if _DBG_USE_REAL_AIOHTTP:
    import aiohttp
else:
    from .faked_server import aiohttp  # type: ignore[no-redef]


def get_dhw(evo: EvohomeClientV2) -> evo2.HotWater | None:
    """Return the first DHW object found across all TCSs of the user's installation."""
    for loc in evo.locations:
        for gwy in loc.gateways:
            for tcs in gwy.systems:
                if tcs.hotwater:
                    return tcs.hotwater
    return None


def get_zon(evo: EvohomeClientV2) -> evo2.Zone | None:
    """Return the first Zone object found across all TCSs of the user's installation."""
    for loc in evo.locations:
        for gwy in loc.gateways:
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
            rsp.raise_for_status()  # should be 200/OK
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

    e.g. {"id": "123"} or [{"id": "123"}], as per the older (non-async) client.
    """

    task = response[0] if isinstance(response, list) else response
    assert isinstance(task, dict), response
    assert "id" in task, response
    return str(task["id"])


async def wait_for_comm_task_v0(auth: evo0.auth.Auth, task_id: str) -> dict[str, Any]:
    """Wait for a v0 communication task (API call) to succeed, and return it.

    Only "Succeeded" is known to be terminal: the older (non-async) client polled until
    it saw it, and its tests used "pending" otherwise. No other states are documented,
    so invoke this within an asyncio.timeout().
    """

    url = f"commTasks?commTaskId={task_id}"

    while True:
        task = await should_work_v0(auth, HTTPMethod.GET, url)
        assert isinstance(task, dict), task

        if task["state"] == "Succeeded":
            return task

        await asyncio.sleep(0.5)


async def is_permanent_auto_v2(evo: EvohomeClientV2, loc_id: int | str) -> bool:
    """Return True if a location's TCS is in permanent Auto mode, as per the v2 API.

    The v0 API cannot read a system mode, so the v2 API is used to confirm that setting
    a v0 location to Auto would be a no-op (i.e. would not disturb a real system).
    """

    await evo.update()

    for loc in evo.locations:
        if loc.id != str(loc_id):
            continue
        for gwy in loc.gateways:
            for tcs in gwy.systems:
                status = tcs.system_mode_status
                return status["mode"] == SystemMode.AUTO and status["is_permanent"]

    return False


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
            rsp.raise_for_status()  # should be 200/OK
        except aiohttp.ClientResponseError as err:
            pytest.fail(f"status={err.status}: {response}")

        assert rsp.content_type == content_type, response

        if rsp.content_type != "application/json":
            if schema:  # a schema is only for JSON
                pytest.fail(f"response is not JSON, so can't validate: {response}")
            assert isinstance(response, str)  # mypy
            return response

        assert isinstance(response, dict | list)  # mypy
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


async def wait_for_comm_task_v2(auth: evo2.auth.Auth, task_id: str) -> bool:
    """Wait for a communication task (API call) to complete."""

    # invoke via:
    # async with asyncio.timeout(2):
    #     await wait_for_comm_task()

    url = f"commTasks?commTaskId={task_id}"

    while True:
        rsp = await auth.websession.request(HTTPMethod.GET, f"{URL_BASE_V2}/{url}")

        # need to do this before raise_for_status()
        if rsp.content_type == "application/json":
            response = await rsp.json()
        else:
            response = await rsp.text()

        try:
            rsp.raise_for_status()  # should be 200/OK
        except aiohttp.ClientResponseError as err:
            pytest.fail(f"status={err.status}: {response}")

        assert rsp.content_type == "application/json", response

        task: dict[str, str] = response[0] if isinstance(response, list) else response

        if task["state"] == "Succeeded":
            return True

        if task["state"] in ("Created", "Running"):
            await asyncio.sleep(0.3)
            continue

        pytest.fail(f"Unexpected task state: {task}")
