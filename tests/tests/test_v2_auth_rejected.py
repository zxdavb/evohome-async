"""Test that Auth re-authenticates if the vendor rejects its access token (a 401).

A 401 is either because the access token was rejected, or because the request was not
allowed (e.g. an id that is not the user's). Auth tells them apart via userAccount (a
URL open to any authenticated user): if that is a 401 too, the token was rejected, so
it is cleared (another is fetched), and the request is made again (once). So a 401
that Auth raises means that the request was not allowed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync2 import exceptions as exc
from evohomeasync2.auth import Auth
from tests.const import URL_BASE_V2, URL_CRED_V2

from .aioresponses import aioresponses

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import TokenCacheManager


OLD_BEARER: Final = "-- old access token --"  # the one the vendor rejects
NEW_BEARER: Final = "-- new access token --"  # the one then fetched

URL_PROBE: Final = f"{URL_BASE_V2}/userAccount"
URL_PUT: Final = f"{URL_BASE_V2}/temperatureZone/1234567/heatSetpoint"

UNAUTHORIZED: Final = [{"code": "Unauthorized", "message": "Unauthorized."}]
NOT_ALLOWED: Final = [
    {"code": "Unauthorized", "message": "You are not allowed to perform this action."}
]
NEW_TOKEN: Final = {
    "access_token": NEW_BEARER,
    "token_type": "bearer",
    "expires_in": 1799,
    "refresh_token": "-- new refresh token --",
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
    """Return an Auth with a valid access token (which the vendor may yet reject)."""

    credentials_manager.import_access_token(
        {
            "access_token": OLD_BEARER,
            "access_token_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
            "refresh_token": "",
        }
    )
    return Auth(credentials_manager, client_session)


def _bearers(calls: list[dict[str, dict[str, str]]]) -> list[str]:
    """Return the access token that was sent with each request."""
    return [c["headers"]["Authorization"].removeprefix("bearer ") for c in calls]


async def test_token_rejected(
    auth: Auth,
    credentials_manager: TokenCacheManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the token is rejected, another is fetched, and the request made again."""

    with aioresponses() as rsp, caplog.at_level(logging.WARNING):
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.post(URL_CRED_V2, payload=NEW_TOKEN)
        rsp.put(URL_PUT, status=HTTPStatus.CREATED, payload={"id": "1234567890"})

        result = await auth.put(
            "temperatureZone/1234567/heatSetpoint", {"setpoint_mode": "FollowSchedule"}
        )

        assert result == {"id": "1234567890"}

        assert list(rsp.requests) == [  # in this order
            (HTTPMethod.PUT, URL_PUT),
            (HTTPMethod.GET, URL_PROBE),
            (HTTPMethod.POST, URL_CRED_V2),
        ]
        puts = rsp.requests[(HTTPMethod.PUT, URL_PUT)]
        assert _bearers(puts) == [OLD_BEARER, NEW_BEARER]
        assert puts[0]["json"] == puts[1]["json"] == {"setpointMode": "FollowSchedule"}

    assert credentials_manager.access_token == NEW_BEARER
    assert "The access_token has been rejected" in caplog.text


async def test_probe_url_rejected(
    auth: Auth,
) -> None:
    """A 401 of userAccount itself can only be of the token (so it is not probed)."""

    with aioresponses() as rsp:
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.post(URL_CRED_V2, payload=NEW_TOKEN)
        rsp.get(URL_PROBE, payload={"userId": "2000001"})

        result = await auth.request(HTTPMethod.GET, "userAccount")

        assert result == {"user_id": "2000001"}
        assert _bearers(rsp.requests[(HTTPMethod.GET, URL_PROBE)]) == [
            OLD_BEARER,
            NEW_BEARER,
        ]


async def test_token_rejected_twice(
    auth: Auth,
) -> None:
    """If the new token is rejected too, the 401 is raised (it is retried only once)."""

    with aioresponses() as rsp:
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.post(URL_CRED_V2, payload=NEW_TOKEN)
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)

        with pytest.raises(exc.ApiCallFailedError) as err:
            await auth.request(HTTPMethod.GET, "userAccount")

    assert err.value.status == HTTPStatus.UNAUTHORIZED


async def test_request_not_allowed(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """If the token is accepted, the 401 is raised: the request was not allowed."""

    with aioresponses() as rsp:
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=NOT_ALLOWED)
        rsp.get(URL_PROBE, payload={"userId": "2000001"})

        with pytest.raises(exc.ApiCallFailedError) as err:
            await auth.put("temperatureZone/1234567/heatSetpoint", {})

        assert list(rsp.requests) == [
            (HTTPMethod.PUT, URL_PUT),
            (HTTPMethod.GET, URL_PROBE),
        ]

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.details == {"code": "Unauthorized"}
    assert credentials_manager.access_token == OLD_BEARER  # not cleared


async def test_probe_fails(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """If it can't be told why (e.g. userAccount is a 5xx), that error is raised.

    Not the 401, as that would mean that the request was not allowed.
    """

    with aioresponses() as rsp:
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.get(URL_PROBE, status=HTTPStatus.SERVICE_UNAVAILABLE, payload={})

        with pytest.raises(exc.ApiCallFailedError) as err:
            await auth.put("temperatureZone/1234567/heatSetpoint", {})

    assert err.value.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert credentials_manager.access_token == OLD_BEARER  # not cleared


async def test_unable_to_reauthenticate(
    auth: Auth,
) -> None:
    """If another token can't be fetched (e.g. a 429), that error is raised."""

    with aioresponses() as rsp:
        rsp.put(URL_PUT, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.get(URL_PROBE, status=HTTPStatus.UNAUTHORIZED, payload=UNAUTHORIZED)
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.TOO_MANY_REQUESTS,
            payload={"error": "attempt_limit_exceeded"},
        )

        with pytest.raises(exc.AuthRateLimitExceededError):
            await auth.put("temperatureZone/1234567/heatSetpoint", {})


async def test_token_refreshed_meanwhile(
    auth: Auth,
    credentials_manager: TokenCacheManager,
) -> None:
    """A rejected token is not cleared if another task has since refreshed it."""

    refreshed = "-- refreshed --"
    unauthorized = exc.ApiCallFailedError("401", status=HTTPStatus.UNAUTHORIZED)

    async def make_request(method: HTTPMethod, url: str, **kwargs: object) -> object:
        if credentials_manager.access_token == OLD_BEARER:
            # while this request is in flight, another task refreshes the token
            credentials_manager._access_token = refreshed
            raise unauthorized
        return {"userId": "2000001"}

    with (
        patch.object(auth, "_make_request", AsyncMock(side_effect=make_request)) as req,
        patch.object(credentials_manager, "fetch_access_token") as fetch,
    ):
        await auth.request(HTTPMethod.GET, "userAccount")

    assert [c.args[1] for c in req.await_args_list] == ["userAccount"] * 2  # retried
    fetch.assert_not_awaited()
    assert credentials_manager.access_token == refreshed  # not cleared
