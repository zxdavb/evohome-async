"""Test the v2 comm tasks: what a PUT returns, and the GET of a task's state.

  PUT  (any)                               -> 201, {"id": "1668279943"}
  GET  /commTasks?commTaskId={tsk_id}      -> 200, {"commtaskId": "1668279943",
                                                    "state": "Created"}

Every accepted PUT is answered 201 (Created) with the id of a comm task (a str of
digits; v1's is an int), which is the vendor's task of sending the change to the
gateway. The client returns it as a CommTask, whose state is then got by a GET (note
its key commtaskId, not commTaskId). Its states are Created, Running, and Succeeded
(only these have been seen), and Failed (both are terminal); Repeated is documented
for v1 only.

A task fails if the gateway (i.e. the controller) can't carry it out: e.g. a zone's
VacationHold, if the zone has no such mode (only some non-evohome systems do): so the
PUT of an invalid request may be accepted (201), and its failure seen only via its
task. Tasks are carried out one at a time, so one may wait behind others. The tasks of
a gateway that is offline are accepted (201), but stay Created, and later fail (as
probed, 2026-11-13: after more than a minute).

The vendor sometimes answers a PUT with the comm task of an earlier, equivalent PUT
(which may have already succeeded), and does not carry it out: the rule for this is
not known (see v1's test_comm_task.py, where it can be detected).

The id is normalised (e.g. a zero-padded id is that of the same task), and the state
of any (recent) task can be got by any user (not only the user whose task it is: the
other URLs are a 401 for any id that is not the user's). An id of no task (or of an
old one) is a 404 (CommTaskNotFound), one that is not numeric is a 400 (InvalidInput),
one that is empty is a 400 (ParameterIsMissing, with a parameterName), and no id at all is a 404 (as JSON,
but without a code).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import (
    ApiCallRejectedError,
    CommTask,
    CommTaskFailedError,
    CommTaskState,
)
from evohomeasync2.schemas.const import TccCommTaskState, TccFailureCode, TccZoneMode
from tests.const import URL_BASE_V2

from .vendor import ZON_ID

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient as EvohomeClientV2
    from evohomeasync2.schemas.account import (
        TccCommTaskResponseT,
        TccFailureResponseT,
        TccTaskResponseT,
    )
    from tests.tests.aioresponses import AioResponses


TASK_ID: Final = "1668279943"

# provenance: the old tests_rf (v2_urls_task, comments of a PUT, and of its polling)
TASK: Final[TccTaskResponseT] = {"id": TASK_ID}

URL_TASK: Final = f"{URL_BASE_V2}/commTasks?commTaskId={TASK_ID}"


def _state(
    state: TccCommTaskState,
) -> TccCommTaskResponseT:
    """Return the vendor's state of the task under test."""
    return {"commtaskId": TASK_ID, "state": state}


async def test_from_put(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """A PUT is a 201 (Created), with the id of its comm task (a str)."""

    url = f"temperatureZone/{ZON_ID}/heatSetpoint"
    mock.put(f"{URL_BASE_V2}/{url}", status=HTTPStatus.CREATED, payload=TASK)

    task = await CommTask.from_put(
        ec2.auth, url, {"setpoint_mode": TccZoneMode.FOLLOW_SCHEDULE}
    )

    mock.assert_called_once_with(
        f"{URL_BASE_V2}/{url}",
        HTTPMethod.PUT,
        json={"setpointMode": "FollowSchedule"},
    )
    assert task.id == TASK_ID
    assert str(task) == f"CommTask(id='{TASK_ID}', put='{url}')"


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        pytest.param(TccCommTaskState.CREATED, CommTaskState.CREATED, id="created"),
        pytest.param(TccCommTaskState.RUNNING, CommTaskState.RUNNING, id="running"),
        pytest.param(
            TccCommTaskState.SUCCEEDED, CommTaskState.SUCCEEDED, id="succeeded"
        ),
        pytest.param(TccCommTaskState.FAILED, CommTaskState.FAILED, id="failed"),
    ],
)
async def test_get_state(
    ec2: EvohomeClientV2,
    mock: AioResponses,
    state: TccCommTaskState,
    expected: CommTaskState,
) -> None:
    """The state of a task is a 200, with its id (as commtaskId) and its state."""

    mock.get(URL_TASK, payload=_state(state))

    result = await CommTask(ec2.auth, TASK_ID).get_state()

    mock.assert_called_once_with(URL_TASK, HTTPMethod.GET, json=None)
    assert result is expected


async def test_get_state_of_padded_id(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """A zero-padded id is that of the same task (its id is normalised)."""

    mock.get(
        f"{URL_BASE_V2}/commTasks?commTaskId=0{TASK_ID}",
        payload=_state(TccCommTaskState.SUCCEEDED),
    )

    result = await CommTask(ec2.auth, f"0{TASK_ID}").get_state()

    assert result is CommTaskState.SUCCEEDED


async def test_wait_succeeds(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """wait() polls the task's state until it has succeeded."""

    states = (
        TccCommTaskState.CREATED,
        TccCommTaskState.RUNNING,
        TccCommTaskState.SUCCEEDED,
    )
    for state in states:
        mock.get(URL_TASK, payload=_state(state))

    await CommTask(ec2.auth, TASK_ID).wait(interval=0)

    assert len(mock.requests[(HTTPMethod.GET, URL_TASK)]) == len(states)


async def test_wait_fails(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """wait() raises a CommTaskFailedError if the task fails.

    For example, a zone's VacationHold, if the zone has no such mode: its PUT is a 201,
    but its task then fails.
    """

    for state in (TccCommTaskState.RUNNING, TccCommTaskState.FAILED):
        mock.get(URL_TASK, payload=_state(state))

    with pytest.raises(CommTaskFailedError) as err:
        await CommTask(ec2.auth, TASK_ID).wait(interval=0)

    assert TASK_ID in err.value.message


@pytest.mark.parametrize(
    ("task_id", "status", "code", "message"),
    [
        pytest.param(  # of no task, or of an old one
            "12345678",
            HTTPStatus.NOT_FOUND,
            TccFailureCode.COMM_TASK_NOT_FOUND,
            "Communication task not found.",
            id="not_found",
        ),
        pytest.param(
            "ABC",
            HTTPStatus.BAD_REQUEST,
            TccFailureCode.INVALID_INPUT,
            "Invalid Input.",
            id="not_numeric",
        ),
    ],
)
async def test_get_state_of_bad_id(
    *,  # keyword-only, as pytest passes them by name
    ec2: EvohomeClientV2,
    mock: AioResponses,
    task_id: str,
    status: HTTPStatus,
    code: TccFailureCode,
    message: str,
) -> None:
    """An id that is not of a (recent) task is a 404 (or a 400, if not numeric)."""

    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.get(
        f"{URL_BASE_V2}/commTasks?commTaskId={task_id}", status=status, payload=body
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await CommTask(ec2.auth, task_id).get_state()

    assert err.value.status == status
    assert err.value.details == {"code": code}


async def test_get_state_of_empty_id(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """An id that is empty is a 400 (ParameterIsMissing, with its parameterName)."""

    body: list[TccFailureResponseT] = [
        {
            "code": "ParameterIsMissing",
            "parameterName": "commTaskId.String",
            "message": "A value is required but was not present in the request.",
        }
    ]
    mock.get(
        f"{URL_BASE_V2}/commTasks?commTaskId=",
        status=HTTPStatus.BAD_REQUEST,
        payload=body,
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await CommTask(ec2.auth, "").get_state()

    assert err.value.details == {"code": TccFailureCode.PARAMETER_IS_MISSING}


async def test_get_without_id(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """No commTaskId at all is a 404, as JSON (a dict, without a code)."""

    mock.get(
        f"{URL_BASE_V2}/commTasks",
        status=HTTPStatus.NOT_FOUND,
        payload={
            "message": "No HTTP resource was found that matches the request URI "
            f"'{URL_BASE_V2}/commTasks'."
        },
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec2.auth.request(HTTPMethod.GET, "commTasks")

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.details == {}
