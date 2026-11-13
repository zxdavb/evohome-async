"""Test that a location's status is got again if the access token is rejected.

A 401 of a location's status is either because the location is no longer the user's
(a StaleConfigError), or because the access token was rejected (the userAccount URL,
which is open to all authenticated users, then tells them apart). If the token was
rejected, it is cleared (so another is fetched), and the status is got again (once).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync2 import exceptions as exc
from tests.common import get_loc

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    metafunc.parametrize(
        "fixture_folder", [Path(FIXTURES) / "default"], ids=["default"]
    )


URL_USR_ACCOUNT: Final = "userAccount"

BEARER: Final = "-- access token --"  # the token the client holds


@pytest.fixture(autouse=True)
def valid_token(
    ec2: EvohomeClient,
) -> None:
    """Give the client a valid access token (so it is the one sent, and maybe rejected)."""

    ec2.token_manager.import_access_token(
        {
            "access_token": BEARER,
            "access_token_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
            "refresh_token": "",
        }
    )


def _unauthorized(url: str) -> exc.ApiCallFailedError:
    return exc.ApiCallFailedError(
        f"GET {url}: 401 Unauthorized", status=HTTPStatus.UNAUTHORIZED
    )


def _responses(*responses: tuple[str, object]) -> AsyncMock:
    """Return a mock of Auth.get() that gives each response in turn (for its URL).

    A response is returned, or raised if it is an exception, or called (and then so).
    """

    queue = list(responses)

    async def get(url: str, schema: object) -> object:
        expected_url, response = queue.pop(0)
        assert url.startswith(expected_url), url
        if callable(response):
            response = response()
        if isinstance(response, Exception):
            raise response
        return response

    return AsyncMock(side_effect=get)


async def test_token_rejected(
    ec2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the access token is rejected, it is cleared, and the status got again."""

    loc = get_loc(ec2)
    url = f"location/{loc.id}/status"
    status = await loc._get_status(_update=False)

    get = _responses(
        (url, _unauthorized(url)),
        (URL_USR_ACCOUNT, _unauthorized(URL_USR_ACCOUNT)),  # i.e. the token is rejected
        (url, status),
    )

    with (
        patch("evohomeasync2.auth.Auth.get", get),
        caplog.at_level(logging.WARNING),
    ):
        assert await loc.get_status() == status

    assert [c.args[0].split("?")[0] for c in get.await_args_list] == [
        url,
        URL_USR_ACCOUNT,
        url,
    ]
    assert ec2.token_manager.access_token == ""  # cleared (so another is fetched)
    assert "The access_token has been rejected" in caplog.text


async def test_token_rejected_twice(
    ec2: EvohomeClient,
) -> None:
    """If a new access token is rejected too, the 401 is raised (it is retried once)."""

    loc = get_loc(ec2)
    url = f"location/{loc.id}/status"

    responses = (
        (url, _unauthorized(url)),
        (URL_USR_ACCOUNT, _unauthorized(URL_USR_ACCOUNT)),
        (url, _unauthorized(url)),
        (URL_USR_ACCOUNT, _unauthorized(URL_USR_ACCOUNT)),
    )
    get = _responses(*responses)

    with (
        patch("evohomeasync2.auth.Auth.get", get),
        pytest.raises(exc.ApiCallFailedError) as err,
    ):
        await loc.get_status()

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert get.await_count == len(responses)


async def test_location_inaccessible(
    ec2: EvohomeClient,
) -> None:
    """If the access token is accepted, the location is no longer the user's."""

    loc = get_loc(ec2)
    url = f"location/{loc.id}/status"
    get = _responses(
        (url, _unauthorized(url)),
        (URL_USR_ACCOUNT, {"user_id": ec2.user_id}),  # i.e. the token is accepted
    )

    with (
        patch("evohomeasync2.auth.Auth.get", get),
        pytest.raises(exc.StaleConfigError) as err,
    ):
        await loc.get_status()

    assert err.value.reason is exc.ClientStateErrorReason.LOCATION_INACCESSIBLE
    assert ec2.token_manager.access_token == BEARER  # not cleared


async def test_token_unsure(
    ec2: EvohomeClient,
) -> None:
    """If it can't be told why (e.g. userAccount is a 5xx), the 401 is raised."""

    loc = get_loc(ec2)
    url = f"location/{loc.id}/status"
    get = _responses(
        (url, _unauthorized(url)),
        (
            URL_USR_ACCOUNT,
            exc.ApiCallFailedError(
                "GET userAccount: 503", status=HTTPStatus.SERVICE_UNAVAILABLE
            ),
        ),
    )

    with (
        patch("evohomeasync2.auth.Auth.get", get),
        pytest.raises(exc.ApiCallFailedError) as err,
    ):
        await loc.get_status()

    assert err.value.status == HTTPStatus.UNAUTHORIZED  # the original error
    assert ec2.token_manager.access_token == BEARER  # not cleared


async def test_token_refreshed_meanwhile(
    ec2: EvohomeClient,
) -> None:
    """A rejected access token is not cleared if another task has since refreshed it."""

    loc = get_loc(ec2)
    url = f"location/{loc.id}/status"
    status = await loc._get_status(_update=False)
    refreshed = "-- refreshed --"

    def refresh_then_reject() -> exc.ApiCallFailedError:
        ec2.token_manager._access_token = refreshed  # by another task, meanwhile
        return _unauthorized(url)

    get = _responses(
        (url, refresh_then_reject),
        (URL_USR_ACCOUNT, _unauthorized(URL_USR_ACCOUNT)),
        (url, status),
    )

    with patch("evohomeasync2.auth.Auth.get", get):
        await loc.get_status()

    assert ec2.token_manager.access_token == refreshed  # not cleared
