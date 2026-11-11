"""Comm tasks (for the TCC v1 API): the vendor's tasks created by PUTs."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from _evohome.comm_task import DEFAULT_INTERVAL, AbstractCommTask
from _evohome.helpers import Case

from .const import SZ_STATE, URL_COMM_TASK
from .schemas import TccCommTaskState, factory_comm_task_response, factory_task_response

if TYPE_CHECKING:
    from collections.abc import Mapping

    from _evohome.helpers import Validator

    from .typedefs import EvoCommTaskDictT

__all__ = ["DEFAULT_INTERVAL", "CommTask"]


# the state of a comm task (unlike its PUT's response, it does not include its id)
SCH_COMM_TASK: Final[Validator[EvoCommTaskDictT]] = factory_comm_task_response(
    Case.PYTHONIC
)


class CommTask(AbstractCommTask):
    """A comm task (for the TCC v1 API): what the vendor creates for an accepted PUT.

    The vendor's response to the PUT is e.g. {"id": 1234567890} (the id is an int).
    """

    _SCH_TASK: ClassVar[Validator[Mapping[str, object]]] = factory_task_response(
        Case.PYTHONIC
    )

    _STATE_SUCCEEDED: ClassVar = TccCommTaskState.SUCCEEDED
    _STATE_FAILED: ClassVar = TccCommTaskState.FAILED

    async def get_state(self) -> TccCommTaskState:
        """Return the current state of the comm task (a single GET).

        Unlike its PUT's response, the state does not include the task's id.
        """

        comm_task = await self._auth.get(
            URL_COMM_TASK.format(comm_task_id=self._id),
            schema=SCH_COMM_TASK,
        )

        return TccCommTaskState(comm_task[SZ_STATE])
