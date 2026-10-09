"""Provides handling of TCC comm tasks (the vendor's tasks created by PUTs)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

import probatio as vol

from _evohome.helpers import Case

from . import exceptions as exc
from .const import SZ_COMMTASK_ID, SZ_ID, SZ_STATE, CommTaskState
from .schemas.account import factory_comm_task_response, factory_task_response

if TYPE_CHECKING:
    from _evohome.auth import AbstractAuth
    from _evohome.helpers import Validator

    from .schemas.account import TccTaskResponseT
    from .typedefs import EvoCommTaskResponseT


# the period between each GET of the task's state, when waiting for it to succeed
DEFAULT_INTERVAL: Final = 0.5  # seconds


_SCH_COMM_TASK: Final[Validator[EvoCommTaskResponseT]] = factory_comm_task_response(
    Case.PYTHONIC
)
_SCH_TASK_DICT: Final[Validator[TccTaskResponseT]] = factory_task_response()

# the response to a PUT is expected to be a dict, but tolerate it being wrapped in a list
# (as is the comm task, below), else an accepted PUT would raise BadApiResponseError
_SCH_TASK: Final[Validator[TccTaskResponseT]] = vol.Schema(
    vol.Any(
        _SCH_TASK_DICT,
        vol.All([_SCH_TASK_DICT], vol.Length(min=1, max=1), lambda x: x[0]),
    )
)

# the comm task is expected to be a dict, but the vendor may wrap it in a list
SCH_COMM_TASK: Final[Validator[EvoCommTaskResponseT]] = vol.Schema(
    vol.Any(
        _SCH_COMM_TASK,
        vol.All([_SCH_COMM_TASK], vol.Length(min=1, max=1), lambda x: x[0]),
    )
)


class CommTask:
    """A comm task: what the vendor creates to carry out an accepted PUT.

    A PUT (e.g. to set a zone's mode) is accepted by the vendor before the change has
    reached the system: its gateway carries out its tasks one at a time, each taking
    about 3-5 seconds. Awaiting `wait()` returns only once the task has succeeded.

    Nothing is polled unless `get_state()` or `wait()` is awaited.
    """

    def __init__(self, auth: AbstractAuth, task_id: str) -> None:
        """Initialise the comm task (it must already exist)."""

        self._auth: Final = auth
        self._id: Final = task_id

    @classmethod
    def from_response(cls, auth: AbstractAuth, response: object) -> CommTask:
        """Create the comm task from the vendor's response to a PUT.

        The response is e.g. {"id": "1668279943"} (or that, wrapped in a list of one).
        """

        try:
            task = _SCH_TASK(response)
        except vol.Invalid as err:
            raise exc.BadApiResponseError(
                f"PUT response is not a comm task: {response}: {err}"
            ) from err

        return cls(auth, task[SZ_ID])

    def __repr__(self) -> str:
        """Return an unambiguous string representation of the comm task."""
        return f"{self.__class__.__name__}(id='{self._id}')"

    @property
    def id(self) -> str:
        """Return the id of the comm task."""
        return self._id

    async def get_state(self) -> CommTaskState | str:
        """Return the current state of the comm task (a single GET).

        Will return a str only if the vendor's state is not a known CommTaskState.
        """

        url = f"commTasks?commTaskId={self._id}"
        task = await self._auth.get(url, schema=SCH_COMM_TASK)

        if task[SZ_COMMTASK_ID] != self._id:
            raise exc.BadApiResponseError(f"{self}: GET {url}: wrong comm task: {task}")

        return task[SZ_STATE]

    async def wait(self, *, interval: float = DEFAULT_INTERVAL) -> None:
        """Wait for the comm task to succeed, polling its state every `interval` secs.

        Raise CommTaskFailedError if the task fails. To limit how long to wait, use
        `asyncio.timeout()`; a task usually takes 3-5 secs, but its gateway carries out
        its tasks one at a time, so it may take longer if others are queued ahead of it:

            async with asyncio.timeout(30):
                await task.wait()
        """

        while (state := await self.get_state()) != CommTaskState.SUCCEEDED:
            if state == CommTaskState.FAILED:
                raise exc.CommTaskFailedError(f"{self}: the comm task failed")
            await asyncio.sleep(interval)
