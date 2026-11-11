"""Comm tasks (for the TCC v2 API): the vendor's tasks created by PUTs."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from _evohome.comm_task import DEFAULT_INTERVAL, AbstractCommTask
from _evohome.helpers import Case

from .const import SZ_STATE, URL_COMM_TASK, CommTaskState
from .schemas.account import factory_comm_task_response, factory_task_response

if TYPE_CHECKING:
    from collections.abc import Mapping

    from _evohome.helpers import Validator

    from .typedefs import EvoCommTaskResponseT

__all__ = ["DEFAULT_INTERVAL", "CommTask"]


# the state of a comm task (a dict: only an error response is seen as a list)
SCH_COMM_TASK: Final[Validator[EvoCommTaskResponseT]] = factory_comm_task_response(
    Case.PYTHONIC
)


class CommTask(AbstractCommTask):
    """A comm task (for the TCC v2 API): what the vendor creates for an accepted PUT.

    The vendor's response to the PUT is e.g. {"id": "1668279943"}.
    """

    _SCH_TASK: ClassVar[Validator[Mapping[str, object]]] = factory_task_response()

    _STATE_SUCCEEDED: ClassVar = CommTaskState.SUCCEEDED
    _STATE_FAILED: ClassVar = CommTaskState.FAILED

    async def get_state(self) -> CommTaskState | str:
        """Return the current state of the comm task (a single GET).

        Will return a str only if the vendor's state is not a known CommTaskState.
        """

        comm_task = await self._auth.get(
            URL_COMM_TASK.format(comm_task_id=self._id),
            schema=SCH_COMM_TASK,
        )

        return comm_task[SZ_STATE]
