"""Test that Auth re-authenticates if the vendor rejects its session id (a 401).

A 401 is either because the session id was rejected, or because the request was not
allowed (e.g. an id that is not the user's). Auth tells them apart via accountInfo (a
URL open to any authenticated user): if that is a 401 too, the session id was
rejected, so it is cleared (another is fetched), and the request is made again (once).
So a 401 that Auth raises means that the request was not allowed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync import exceptions as exc
from evohomeasync.auth import Auth
from tests.const import URL_BASE_V1, URL_CRED_V1

from .aioresponses import aioresponses

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import TokenCacheManager


OLD_SESSION: Final = "-- old session id --"  # the one the vendor rejects
NEW_SESSION: Final = "-- new session id --"  # the one then fetched

URL_PROBE: Final = f"{URL_BASE_V1}/accountInfo"
URL_PUT: Final = f"{URL_BASE_V1}/devices/1234567/thermostat/changeableValues"

UNAUTHORIZED: Final = [{"code": "Unauthorized", "message": "Unauthorized"}]
NOT_ALLOWED: Final = [
    {"code": "Unauthorized", "message": "You are not allowed to perform this action."}
]
NEW_SESSION_RESPONSE: Final = {
    "sessionId": NEW_SESSION,
    "userInfo": {"userID": 2000001},
}


@pytest.fixture
def cache_path(
    tmp_path: Path,
) -> Path:
    """Return the path to a token cache of the test's own (it starts empty)."""
    return tmp_path / ".evo-cache.tst"


@pytest.fixture
def auth(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
) -> Auth:
    """Return an Auth with a valid session id (which the vendor may yet reject)."""

    credentials_manager.import_session_id(
        {
            "session_id": OLD_SESSION,
            "session_id_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
        }
    )
    return Auth(credentials_manager, client_session)


async def test_session_id_rejected(
    auth: Auth,
    credentials_manager: TokenCacheManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the session id is rejected, another is fetched, and the request made again."""

    with aioresponses() as rsp, caplog.at_level(logging.WARNING):
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.post(URL_CRED_V1, payload=NEW_SESSION_RESPONSE)
        rsp.put(URL_PUT, status=HTTPStatus.CREATED, payload={"id": 1234567890})

        result = await auth.put(
            "devices/1234567/thermostat/changeableValues", {"mode": "DHWOff"}
        )

        assert result == {"id": 1234567890}

        assert list(rsp.requests) == [  # in this order
            (HTTPMethod.PUT, URL_PUT),
            (HTTPMethod.GET, URL_PROBE),
            (HTTPMethod.POST, URL_CRED_V1),
        ]
        puts = rsp.requests[(HTTPMethod.PUT, URL_PUT)]
        assert [c["headers"]["sessionId"] for c in puts] == [OLD_SESSION, NEW_SESSION]

    assert credentials_manager.session_id == NEW_SESSION
    assert "The session_id has been rejected" in caplog.text


async def test_request_not_allowed(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """If the session id is accepted, the 401 is raised: the request was not allowed."""

    with aioresponses() as rsp:
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=NOT_ALLOWED)
        rsp.get(URL_PROBE, payload={"userID": 2000001})

        with pytest.raises(exc.ApiCallFailedError) as err:
            await auth.put("devices/1234567/thermostat/changeableValues", {})

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert credentials_manager.session_id == OLD_SESSION  # not cleared


async def test_probe_fails(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """If it can't be told why (e.g. accountInfo is a 5xx), that error is raised."""

    with aioresponses() as rsp:
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.get(URL_PROBE, status=HTTPStatus.SERVICE_UNAVAILABLE, payload={})

        with pytest.raises(exc.ApiCallFailedError) as err:
            await auth.put("devices/1234567/thermostat/changeableValues", {})

    assert err.value.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert credentials_manager.session_id == OLD_SESSION  # not cleared


async def test_session_id_refreshed_meanwhile(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """A rejected session id is not cleared if another task has since refreshed it."""

    refreshed = "-- refreshed --"
    unauthorized = exc.ApiCallFailedError("401", status=HTTPStatus.UNAUTHORIZED)

    async def make_request(method: HTTPMethod, url: str, **kwargs: object) -> object:
        if credentials_manager.session_id == OLD_SESSION:
            # while this request is in flight, another task refreshes the session id
            credentials_manager._session_id = refreshed
            raise unauthorized
        return {"userID": 2000001}

    with (
        patch.object(auth, "_make_request", AsyncMock(side_effect=make_request)) as req,
        patch.object(credentials_manager, "fetch_session_id") as fetch,
    ):
        await auth.request(HTTPMethod.GET, "accountInfo")

    assert [c.args[1] for c in req.await_args_list] == ["accountInfo"] * 2  # retried
    fetch.assert_not_awaited()
    assert credentials_manager.session_id == refreshed  # not cleared
