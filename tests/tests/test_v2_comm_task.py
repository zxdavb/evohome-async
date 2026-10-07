"""evohome-async - validate the handling of comm tasks (the result of a PUT)."""

from __future__ import annotations

from contextlib import contextmanager
from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from _evohome.auth import AbstractAuth
from evohomeasync2 import BadApiResponseError, CommTask, CommTaskFailedError
from evohomeasync2.const import CommTaskState

from .conftest import FIXTURES_V2 as FIXTURES
from .const import PUT_RESPONSE_V2

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import AsyncMock as AsyncMockT

    from evohomeasync2 import Zone
    from evohomeasync2.auth import Auth


TASK_ID = PUT_RESPONSE_V2["id"]
URL = f"commTasks?commTaskId={TASK_ID}"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES).glob("*") if p.is_dir() and p.name == "default"
    ]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


@contextmanager
def patch_request(
    *, return_value: object = None, side_effect: list[object] | None = None
) -> Iterator[AsyncMockT]:
    """Mock AbstractAuth.request(), and undo the evohome_v2 fixture's patch of get()."""

    with (
        patch("evohomeasync2.auth.Auth.get", AbstractAuth.get),
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value=return_value,
            side_effect=side_effect,
        ) as mock,
    ):
        yield mock


def _task(state: str, task_id: str = TASK_ID) -> dict[str, str]:
    """Return a comm task's state, as returned by AbstractAuth.request()."""
    return {"commtask_id": task_id, "state": state}  # NOTE: is snake_case


async def test_put_returns_comm_task(zone: Zone) -> None:
    """Check a set_* method returns the PUT's comm task, without polling it."""

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_request:
        task = await zone.set_temperature(19.5)

    assert isinstance(task, CommTask)
    assert task.id == TASK_ID
    mock_request.assert_awaited_once()  # the PUT only (no GET of the task's state)


async def test_set_schedule_returns_comm_task(zone: Zone) -> None:
    """Check set_schedule() returns the PUT's comm task.

    Zone and HotWater share set_schedule() (only their schedule schema differs), so
    only a zone is tested.
    """

    schedule = await zone.get_schedule()

    with patch(
        "_evohome.auth.AbstractAuth.request",
        new_callable=AsyncMock,
        return_value=PUT_RESPONSE_V2,
    ) as mock_request:
        task = await zone.set_schedule(schedule)

    assert isinstance(task, CommTask)
    assert task.id == TASK_ID
    mock_request.assert_awaited_once()  # the PUT only (no GET of the task's state)


async def test_put_with_bad_response(zone: Zone) -> None:
    """Check a PUT whose response is not a comm task raises BadApiResponseError."""

    with (
        patch(
            "_evohome.auth.AbstractAuth.request",
            new_callable=AsyncMock,
            return_value={"id": "not_a_task_id"},
        ),
        pytest.raises(BadApiResponseError),
    ):
        await zone.reset()


@pytest.mark.parametrize("as_list", [False, True], ids=["dict", "list"])
async def test_get_state(auth: Auth, *, as_list: bool) -> None:
    """Check get_state() GETs the task's state (the vendor may wrap it in a list)."""

    task = CommTask(auth, TASK_ID)
    response = [_task("Running")] if as_list else _task("Running")

    with patch_request(
        return_value=response,
    ) as mock_request:
        assert await task.get_state() == CommTaskState.RUNNING

    mock_request.assert_awaited_once_with(HTTPMethod.GET, URL)


async def test_get_state_unknown(auth: Auth) -> None:
    """Check get_state() tolerates an unknown state (passed thru as a str)."""

    task = CommTask(auth, TASK_ID)

    with patch_request(
        return_value=_task("Postponed"),
    ):
        assert await task.get_state() == "postponed"


async def test_get_state_wrong_task(auth: Auth) -> None:
    """Check get_state() raises BadApiResponseError if the vendor returns another task."""

    task = CommTask(auth, TASK_ID)

    with (
        patch_request(
            return_value=_task("Running", task_id="9876543210"),
        ),
        pytest.raises(BadApiResponseError),
    ):
        await task.get_state()


async def test_wait_succeeds(auth: Auth) -> None:
    """Check wait() polls until the task succeeds (an unknown state isn't terminal)."""

    task = CommTask(auth, TASK_ID)
    states = ["Created", "Running", "Postponed", "Repeated", "Succeeded"]

    with patch_request(
        side_effect=[_task(s) for s in states],
    ) as mock_request:
        await task.wait(interval=0)

    assert mock_request.await_count == len(states)


async def test_wait_fails(auth: Auth) -> None:
    """Check wait() raises CommTaskFailedError if the task fails."""

    task = CommTask(auth, TASK_ID)

    with (
        patch_request(
            side_effect=[_task("Running"), _task("Failed")],
        ),
        pytest.raises(CommTaskFailedError),
    ):
        await task.wait(interval=0)
