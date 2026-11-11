"""Comm tasks: the vendor's tasks created by PUTs (shared by the v1 and v2 clients)."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Final, Self

import probatio as vol

from . import exceptions as exc

if TYPE_CHECKING:
    from collections.abc import Mapping
    from enum import StrEnum

    from aiohttp.typedefs import StrOrURL

    from .auth import AbstractAuth
    from .helpers import Validator


# the period between each GET of the task's state, when waiting for it to succeed
DEFAULT_INTERVAL: Final = 0.5  # seconds

SZ_ID: Final = "id"  # of the comm task, in the response to its PUT


class AbstractCommTask(ABC):
    """A comm task: what the vendor creates to carry out an accepted PUT.

    A PUT (e.g. to set a zone's mode) is accepted by the vendor before the change has
    reached the system: its gateway carries out its tasks one at a time, each taking
    about 3-7 seconds. Awaiting `wait()` returns only once the task has succeeded.

    Nothing is polled unless `get_state()` or `wait()` is awaited.

    Each API has its own subclass, as their responses (and states) differ.
    """

    # the vendor's response to the PUT, e.g. {"id": "1668279943"} (v1: an int)
    _SCH_TASK: ClassVar[Validator[Mapping[str, object]]]

    # the states that end the task (as returned by get_state())
    _STATE_SUCCEEDED: ClassVar[StrEnum]
    _STATE_FAILED: ClassVar[StrEnum]

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
    ) -> Self:
        """Make the PUT (as for `AbstractAuth.put()`), and return its comm task."""

        response = await auth.put(url, json, schema=schema)

        try:
            comm_task = cls._SCH_TASK(response)
        except vol.Invalid as err:
            raise exc.CommTaskFailedError(  # the PUT may yet take effect, or not
                f"PUT {url}: response is not a comm task: {response}: {err}"
            ) from err

        return cls(auth, str(comm_task[SZ_ID]), put_url=str(url))  # v1's id is an int

    def __str__(self) -> str:
        """Return a string representation of the comm task (e.g. for messages)."""

        put = f", put='{self._put_url}'" if self._put_url else ""
        return f"{self.__class__.__name__}(id='{self._id}'{put})"

    @property
    def id(self) -> str:
        """Return the id of the comm task."""
        return self._id

    @abstractmethod
    async def get_state(self) -> StrEnum | str:
        """Return the current state of the comm task (a single GET)."""

    async def wait(self, *, interval: float = DEFAULT_INTERVAL) -> None:
        """Wait for the comm task to succeed, polling its state every `interval` secs.

        Raise CommTaskFailedError if the task fails. To limit how long to wait, use
        `asyncio.timeout()`; a task usually takes 3-7 secs, but its gateway carries out
        its tasks one at a time, so it may take longer if others are queued ahead of it:

            async with asyncio.timeout(30):
                await task.wait()
        """

        while (state := await self.get_state()) is not self._STATE_SUCCEEDED:
            if state is self._STATE_FAILED:
                raise exc.CommTaskFailedError(f"{self}: has failed")
            await asyncio.sleep(interval)
