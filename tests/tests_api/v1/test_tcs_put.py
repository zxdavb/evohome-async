"""Test the v1 PUT of a TCS's mode: the vendor has removed its URL.

  PUT /evoTouchSystems?locationId={loc_id}
    {"quickAction": "Away", "quickActionNextTime": "2026-07-01T22:00:00"}

This once set the mode of the location's TCS (the older, non-async, client sent
{"QuickAction": mode, "QuickActionNextTime": None | until}), but it is now a 404 (Not
Found, whose body is HTML, from IIS), for a GET or a PUT: so there is no longer any way
to set a TCS's mode via the v1 API (use the v2 API).

So ControlSystem.set_mode() (and set_auto(), set_away(), etc.) always fail, with an
ApiCallRejectedError (status 404). Its body is as before: a quickActionNextTime (if
any) is the location's local time, without a Z.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync import ApiCallErrorReason, ApiCallRejectedError
from evohomeasync.schemas import TccSystemMode
from tests.const import URL_BASE_V1

from .vendor import HTML_NOT_FOUND, LOC_ID

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from evohomeasync import ControlSystem
    from tests.tests.aioresponses import AioResponses


URL_TCS_MODE: Final = f"{URL_BASE_V1}/evoTouchSystems?locationId={LOC_ID}"

# the location is in GMT Standard Time (i.e. Europe/London): in July, that is BST
_UNTIL_IN_BST: Final = dt(2026, 7, 1, 21, tzinfo=UTC)  # i.e. 22:00 local


@pytest.mark.parametrize(
    ("call", "body"),
    [
        pytest.param(
            lambda tcs: tcs.set_auto(),
            {"quickAction": "Auto"},
            id="set_auto",
        ),
        pytest.param(  # the quickActionNextTime is local time (BST), without a Z
            lambda tcs: tcs.set_away(until=_UNTIL_IN_BST),
            {"quickAction": "Away", "quickActionNextTime": "2026-07-01T22:00:00"},
            id="set_away_until",
        ),
        pytest.param(
            lambda tcs: tcs.set_mode(TccSystemMode.HEATING_OFF),
            {"quickAction": "HeatingOff"},
            id="set_mode",
        ),
    ],
)
async def test_set_mode(
    tcs: ControlSystem,
    mock: AioResponses,
    call: Callable[[ControlSystem], Awaitable[object]],
    body: dict[str, object],
) -> None:
    """Every PUT of a mode is a 404 (HTML): its URL was removed by the vendor."""

    mock.put(
        URL_TCS_MODE,
        status=HTTPStatus.NOT_FOUND,
        body=HTML_NOT_FOUND,
        content_type="text/html",
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await call(tcs)

    mock.assert_called_once_with(URL_TCS_MODE, HTTPMethod.PUT, json=body)

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.reason is ApiCallErrorReason.REQUEST_REJECTED
    assert err.value.details == {}  # there is no code, as there is no JSON


async def test_get(
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """A GET of the URL is a 404 (HTML) too."""

    mock.get(
        URL_TCS_MODE,
        status=HTTPStatus.NOT_FOUND,
        body=HTML_NOT_FOUND,
        content_type="text/html",
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await tcs._auth.request(HTTPMethod.GET, f"evoTouchSystems?locationId={LOC_ID}")

    assert err.value.status == HTTPStatus.NOT_FOUND
