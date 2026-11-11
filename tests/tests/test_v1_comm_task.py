"""Test the handling of v1 comm tasks (the result of a PUT)."""

from __future__ import annotations

from contextlib import contextmanager
from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from _evohome.auth import AbstractAuth
from evohomeasync import (
    BadApiResponseError,
    CommTask,
    CommTaskFailedError,
    ResponseErrorReason,
    TccCommTaskState,
    TccSystemMode,
)
from tests.common import get_tcs

from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterator
    from unittest.mock import AsyncMock as AsyncMockT

    from evohomeasync import EvohomeClient as EvohomeClientV1


TASK_ID = "1234567890"
PUT_RESPONSE = {"id": int(TASK_ID)}  # NOTE: the id is an int
URL = f"commTasks?commTaskId={TASK_ID}"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [p for p in Path(FIXTURES).glob("*") if p.name == "default"]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize("fixture_folder", folders, ids=(p.name for p in folders))


@contextmanager
def patch_request(
    *, return_value: object = None, side_effect: list[object] | None = None
) -> Iterator[AsyncMockT]:
    """Mock AbstractAuth.request(), and undo the ec1 fixture's patch of get()."""

    with (
        patch("evohomeasync.auth.Auth.get", AbstractAuth.get),
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=return_value,
            side_effect=side_effect,
        ) as mock,
    ):
        yield mock


def _task(state: str) -> dict[str, object]:
    """Return a comm task's state, as returned by AbstractAuth.request().

    Unlike the PUT's response, it does not include the task's own id.
    """
    return {  # NOTE: is snake_case
        "state": state,
        "started": "2026-09-22T20:08:04.053",
        "mac_id": "00D02D67C990",
        "gateway_id": 2678129,
        "device_id": 6860918,
    }


def _setters(
    ec1: EvohomeClientV1,
) -> dict[str, tuple[Callable[[], Awaitable[CommTask]], str]]:
    """Return each kind of PUT (a set_* method), with the URL it PUTs to."""

    tcs = get_tcs(ec1)
    zone = tcs.zones[0]
    dhw = tcs.hotwater
    assert dhw is not None  # the default/ fixture has a DHW

    return {
        "tcs": (
            lambda: tcs.set_mode(TccSystemMode.AWAY),
            f"evoTouchSystems?locationId={tcs.id}",
        ),
        "zone": (
            lambda: zone.set_temperature(19.5),
            f"devices/{zone.id}/thermostat/changeableValues/heatSetpoint",
        ),
        "dhw": (
            dhw.set_dhw_auto,
            f"devices/{dhw.id}/thermostat/changeableValues",
        ),
    }


@pytest.mark.parametrize("kind", ["tcs", "zone", "dhw"])
async def test_put_returns_comm_task(
    ec1: EvohomeClientV1,
    kind: str,
) -> None:
    """Check a set_* method returns the PUT's comm task, without polling it."""

    set_mode, url = _setters(ec1)[kind]

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE,
    ) as mock_request:
        task = await set_mode()

    assert isinstance(task, CommTask)
    assert task.id == TASK_ID  # a str, although the vendor's id is an int
    mock_request.assert_awaited_once()  # the PUT only (no GET of the task's state)

    # the task knows its PUT (so its errors can say which request has failed)
    assert str(task) == f"CommTask(id='{TASK_ID}', put='{url}')"


async def test_put_with_bad_response(
    ec1: EvohomeClientV1,
) -> None:
    """Check a PUT whose response is not a comm task raises BadApiResponseError."""

    zone = get_tcs(ec1).zones[0]
    url = f"devices/{zone.id}/thermostat/changeableValues/heatSetpoint"

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value={"id": "not_a_task_id"},  # the id is not an int
        ),
        pytest.raises(BadApiResponseError) as exc_info,
    ):
        await zone.set_zone_auto()

    assert exc_info.value.message.startswith(
        f"PUT {url}: response is not a comm task: "
    )
    assert exc_info.value.reason is ResponseErrorReason.COMM_TASK_INVALID


async def test_get_state(
    ec1: EvohomeClientV1,
) -> None:
    """Check get_state() GETs the task's state."""

    task = CommTask(ec1.auth, TASK_ID)

    with patch_request(
        return_value=_task("Running"),
    ) as mock_request:
        assert await task.get_state() is TccCommTaskState.RUNNING

    mock_request.assert_awaited_once_with(HTTPMethod.GET, URL)


async def test_get_state_unknown(
    ec1: EvohomeClientV1,
) -> None:
    """Check get_state() raises BadApiResponseError if the state is not known."""

    task = CommTask(ec1.auth, TASK_ID)

    with (
        patch_request(
            return_value=_task("Postponed"),
        ),
        pytest.raises(BadApiResponseError),
    ):
        await task.get_state()


async def test_wait_succeeds(
    ec1: EvohomeClientV1,
) -> None:
    """Check wait() polls until the task succeeds."""

    task = CommTask(ec1.auth, TASK_ID)
    states = ["Created", "Running", "Repeated", "Succeeded"]

    with patch_request(
        side_effect=[_task(s) for s in states],
    ) as mock_request:
        await task.wait(interval=0)

    assert mock_request.await_count == len(states)


async def test_wait_fails(
    ec1: EvohomeClientV1,
) -> None:
    """Check wait() raises CommTaskFailedError (naming its PUT) if the task fails."""

    put_url = "devices/1234567/thermostat/changeableValues/heatSetpoint"
    task = CommTask(ec1.auth, TASK_ID, put_url=put_url)

    with (
        patch_request(
            side_effect=[_task("Running"), _task("Failed")],
        ),
        pytest.raises(CommTaskFailedError) as exc_info,
    ):
        await task.wait(interval=0)

    assert exc_info.value.message == (
        f"CommTask(id='{TASK_ID}', put='{put_url}'): has failed"
    )
