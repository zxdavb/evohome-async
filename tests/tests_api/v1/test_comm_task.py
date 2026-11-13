"""Test the v1 comm tasks: what a PUT returns, and the GET of a task's state.

  PUT  (any)                               -> 201, {"id": 1234567890}
  GET  /commTasks?commTaskId={tsk_id}      -> 200, {"state": "Succeeded", "started": ...}

Every accepted PUT is answered 201 (Created) with the id of a comm task (an int; v2's
is a str), the vendor's task of sending the change to the gateway. (The original, 2014,
client also allowed for a list of one such dict, but none has been seen.) The client
returns it as a CommTask, whose state is then got by a GET. Unlike v2's, the state does
not include the task's own id, but does include what it acted upon:
  {"state": "Succeeded",
   "started": "2026-09-22T20:08:04.053",   # TZ-naive (UTC)
   "finished": "2026-09-22T20:08:07.13",   # TZ-naive (UTC), only once finished
   "macId": "00D02DEE0000", "gatewayId": 2000020, "deviceId": 2000041,
   "activityId": "0187be9d-1f3c-41e7-abd6-28f5442feddd"}
Its states (as documented by the vendor) are Created, Running, Repeated (running again,
after an earlier run failed), Succeeded and Failed (the last two are terminal). A task
has been seen to take 29s (2026-10-07), as the gateway carries out its tasks one at a
time; a gateway that is offline never completes them.

The vendor sometimes answers a PUT with the comm task of an earlier, equivalent PUT
(one that has already succeeded), and does not carry it out, even if the device's state
has since changed: so a change is then not applied. The rule for this is not known: it
has been seen repeatedly for a revert to schedule (which has only the one form), and
sometimes for an override (but never for one with a NextTime not used before), from
seconds to minutes after the earlier PUT, but not always; the two PUTs need not be
identical (e.g. they have differed in their key casing, and in having a null key vs not
having that key). It can be detected by the task's started being before the PUT was
sent. Otherwise, a change has appeared via GET within a second of its task succeeding.

The id is normalised (a zero-padded id is that of the same task), and the state of any
(recent) task can be got by any user (including the ids of their gateway and device):
the other URLs are a 401 for an id that is not the user's. An id of no task (or of an
old one) is a 404 (CommTaskNotFound); one that is not numeric (or is beyond an Int32,
or is empty) is a 400 (InvalidInput; v2's empty id is a ParameterIsMissing); no id at
all is a 404 (as JSON, but without a code).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync import ApiCallRejectedError, CommTask, CommTaskFailedError
from evohomeasync.schemas import (
    TccCommTaskState,
    TccFailureCode,
    TccSetpointStatus,
    _DhwIdT,
    _GatewayIdT,
    _TaskIdT,
)
from tests.const import URL_BASE_V1

from .vendor import DHW_ID, GWY_ID, ZON_ID

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient as EvohomeClientV1
    from evohomeasync.schemas import (
        TccCommTaskResponseT,
        TccFailureResponseT,
        TccTaskResponseT,
    )
    from tests.tests.aioresponses import AioResponses


TASK_ID: Final = 1234567890

TASK: Final[TccTaskResponseT] = {"id": _TaskIdT(TASK_ID)}

URL_TASK: Final = f"{URL_BASE_V1}/commTasks?commTaskId={TASK_ID}"


def _state(
    state: TccCommTaskState,
) -> TccCommTaskResponseT:
    """Return the vendor's state of the task under test (here, of a DHW's PUT).

    provenance: the old tests_rf/common.py (its docstring, of 2026-09-22) (redacted)
    """

    task: TccCommTaskResponseT = {
        "state": state,
        "started": "2026-09-22T20:08:04.053",
        "macId": "00D02DEE0000",
        "gatewayId": _GatewayIdT(GWY_ID),
        "deviceId": _DhwIdT(DHW_ID),
        "activityId": "0187be9d-1f3c-41e7-abd6-28f5442feddd",
    }
    if state in (TccCommTaskState.SUCCEEDED, TccCommTaskState.FAILED):
        task["finished"] = "2026-09-22T20:08:07.13"
    return task


async def test_from_put(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """A PUT is a 201 (Created), with the id of its comm task (an int)."""

    url = f"devices/{ZON_ID}/thermostat/changeableValues/heatSetpoint"
    mock.put(f"{URL_BASE_V1}/{url}", status=HTTPStatus.CREATED, payload=TASK)

    task = await CommTask.from_put(
        ec1.auth, url, {"status": TccSetpointStatus.SCHEDULED}
    )

    mock.assert_called_once_with(
        f"{URL_BASE_V1}/{url}", HTTPMethod.PUT, json={"status": "Scheduled"}
    )
    assert task.id == str(TASK_ID)  # the client keeps it as a str


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(TccCommTaskState.CREATED, id="created"),
        pytest.param(TccCommTaskState.RUNNING, id="running"),
        pytest.param(TccCommTaskState.SUCCEEDED, id="succeeded"),
        pytest.param(TccCommTaskState.FAILED, id="failed"),
    ],
)
async def test_get_state(
    ec1: EvohomeClientV1,
    mock: AioResponses,
    state: TccCommTaskState,
) -> None:
    """The state of a task is a 200 (without the task's id)."""

    mock.get(URL_TASK, payload=_state(state))

    result = await CommTask(ec1.auth, str(TASK_ID)).get_state()

    mock.assert_called_once_with(URL_TASK, HTTPMethod.GET, json=None)
    assert result is state


async def test_wait_succeeds(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """wait() polls the task's state until it has succeeded."""

    states = (TccCommTaskState.RUNNING, TccCommTaskState.SUCCEEDED)
    for state in states:
        mock.get(URL_TASK, payload=_state(state))

    await CommTask(ec1.auth, str(TASK_ID)).wait(interval=0)

    assert len(mock.requests[(HTTPMethod.GET, URL_TASK)]) == len(states)


async def test_wait_fails(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """wait() raises a CommTaskFailedError if the task fails."""

    for state in (TccCommTaskState.RUNNING, TccCommTaskState.FAILED):
        mock.get(URL_TASK, payload=_state(state))

    with pytest.raises(CommTaskFailedError):
        await CommTask(ec1.auth, str(TASK_ID)).wait(interval=0)


@pytest.mark.parametrize(
    ("task_id", "status", "code", "message"),
    [
        pytest.param(  # of no task, or of an old one
            "12345678",
            HTTPStatus.NOT_FOUND,
            TccFailureCode.COMM_TASK_NOT_FOUND,
            "...",  # not recorded
            id="not_found",
        ),
        pytest.param(  # so an id beyond 2147483647 is not valid either
            "ABC",
            HTTPStatus.BAD_REQUEST,
            TccFailureCode.INVALID_INPUT,
            "The value 'ABC' is not valid for Int32.",
            id="not_numeric",
        ),
        pytest.param(  # not a ParameterIsMissing (as is v2's)
            "",
            HTTPStatus.BAD_REQUEST,
            TccFailureCode.INVALID_INPUT,
            "...",  # not recorded
            id="empty",
        ),
    ],
)
async def test_get_state_of_bad_id(
    *,  # keyword-only, as pytest passes them by name
    ec1: EvohomeClientV1,
    mock: AioResponses,
    task_id: str,
    status: HTTPStatus,
    code: TccFailureCode,
    message: str,
) -> None:
    """An id that is not of a (recent) task is a 404 (or a 400, if not an Int32)."""

    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.get(
        f"{URL_BASE_V1}/commTasks?commTaskId={task_id}", status=status, payload=body
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await CommTask(ec1.auth, task_id).get_state()

    assert err.value.status == status
    assert err.value.details == {"code": code}


async def test_get_without_id(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """No commTaskId at all is a 404, as JSON (a dict, without a code)."""

    mock.get(
        f"{URL_BASE_V1}/commTasks",
        status=HTTPStatus.NOT_FOUND,
        payload={
            "message": "No HTTP resource was found that matches the request URI "
            f"'{URL_BASE_V1}/commTasks'."
        },
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec1.auth.request(HTTPMethod.GET, "commTasks")

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.details == {}
