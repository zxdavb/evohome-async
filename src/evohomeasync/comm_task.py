"""Comm tasks (for the TCC v1 API): the vendor's tasks created by PUTs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

import probatio as vol

from _evohome.helpers import Case

from . import exceptions as exc
from .const import SZ_ID, SZ_STATE, URL_COMM_TASK
from .exceptions import ResponseErrorReason
from .schemas import TccCommTaskState, factory_comm_task_response, factory_task_response

if TYPE_CHECKING:
    from collections.abc import Mapping

    from aiohttp.typedefs import StrOrURL

    from _evohome.auth import AbstractAuth
    from _evohome.helpers import Validator

    from .typedefs import EvoCommTaskDictT, EvoTaskDictT


# the period between each GET of the task's state, when waiting for it to succeed
DEFAULT_INTERVAL: Final = 0.5  # seconds


# the response to a PUT (e.g. {"id": 1234567890}), and the state of its comm task
_SCH_TASK: Final[Validator[EvoTaskDictT]] = factory_task_response(Case.PYTHONIC)
SCH_COMM_TASK: Final[Validator[EvoCommTaskDictT]] = factory_comm_task_response(
    Case.PYTHONIC
)


class CommTask:
    """A comm task: what the vendor creates to carry out an accepted PUT.

    A PUT (e.g. to set a zone's mode) is accepted by the vendor before the change has
    reached the system: its gateway carries out its tasks one at a time, each taking
    about 3-7 seconds. Awaiting `wait()` returns only once the task has succeeded.

    Nothing is polled unless `get_state()` or `wait()` is awaited.
    """

    def __init__(
        self, auth: AbstractAuth, task_id: str, *, put_url: str | None = None
    ) -> None:
        """Initialise the comm task (it must already exist).

        The put_url is that of the PUT that created the task (if known), so that the
        task's errors can say which request has failed.
        """

        self._auth: Final = auth
        self._id: Final = task_id
        self._put_url: Final = put_url

    @classmethod
    async def from_put(
        cls,
        auth: AbstractAuth,
        url: StrOrURL,
        /,
        json: Mapping[str, object],
        *,
        schema: Validator[Mapping[str, object]] | None = None,
    ) -> CommTask:
        """Make the PUT (as for `AbstractAuth.put()`), and return its comm task.

        The vendor's response is e.g. {"id": 1234567890} (the id is an int).
        """

        response = await auth.put(url, json, schema=schema)

        try:
            task = _SCH_TASK(response)
        except vol.Invalid as err:
            raise exc.BadApiResponseError(
                f"PUT {url}: response is not a comm task: {response}: {err}",
                reason=ResponseErrorReason.COMM_TASK_INVALID,
            ) from err

        return cls(auth, str(task[SZ_ID]), put_url=str(url))

    def __str__(self) -> str:
        """Return a string representation of the comm task (e.g. for messages)."""

        put = f", put='{self._put_url}'" if self._put_url else ""
        return f"{self.__class__.__name__}(id='{self._id}'{put})"

    @property
    def id(self) -> str:
        """Return the id of the comm task."""
        return self._id

    async def get_state(self) -> TccCommTaskState:
        """Return the current state of the comm task (a single GET).

        Unlike its PUT's response, the state does not include the task's id.
        """

        task = await self._auth.get(
            URL_COMM_TASK.format(comm_task_id=self._id),
            schema=SCH_COMM_TASK,
        )

        return TccCommTaskState(task[SZ_STATE])

    async def wait(self, *, interval: float = DEFAULT_INTERVAL) -> None:
        """Wait for the comm task to succeed, polling its state every `interval` secs.

        Raise CommTaskFailedError if the task fails. To limit how long to wait, use
        `asyncio.timeout()`; a task usually takes 3-7 secs, but its gateway carries out
        its tasks one at a time, so it may take longer if others are queued ahead of it:

            async with asyncio.timeout(30):
                await task.wait()
        """

        while (state := await self.get_state()) is not TccCommTaskState.SUCCEEDED:
            if state is TccCommTaskState.FAILED:
                raise exc.CommTaskFailedError(f"{self}: has failed")
            await asyncio.sleep(interval)
