"""Test that the v1 locations are got again if the session id is rejected.

The URL is of the user's own locations, so a 401 can only be because the session id was
rejected: it is then cleared (so another is fetched), and the locations got again (once).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest

from evohomeasync import exceptions as exc

from .conftest import FIXTURES_V1 as FIXTURES

if TYPE_CHECKING:
    from collections.abc import Callable

    from evohomeasync import EvohomeClient


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    metafunc.parametrize(
        "fixture_folder", [Path(FIXTURES) / "default"], ids=["default"]
    )


SESSION: Final = "-- session id --"  # the session id the client holds


@pytest.fixture(autouse=True)
def valid_session_id(
    ec1: EvohomeClient,
) -> None:
    """Give the client a valid session id (so it is the one sent, and maybe rejected)."""

    ec1._session_manager.import_session_id(
        {
            "session_id": SESSION,
            "session_id_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
        }
    )


def _unauthorized() -> exc.ApiCallFailedError:
    return exc.ApiCallFailedError(
        "GET locations: 401 Unauthorized", status=HTTPStatus.UNAUTHORIZED
    )


async def test_session_id_rejected(
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the session id is rejected, it is cleared, and the locations got again."""

    user_locs = ec1._user_locs
    responses = [_unauthorized(), user_locs]
    get = AsyncMock(side_effect=responses.copy())

    with (
        patch("evohomeasync.auth.Auth.get", get),
        caplog.at_level(logging.WARNING),
    ):
        assert await ec1.get_status() == user_locs

    assert get.await_count == len(responses)  # i.e. the GET was retried
    assert ec1._session_manager.session_id == ""  # cleared (so another is fetched)
    assert "The session_id has been rejected" in caplog.text


async def test_session_id_rejected_twice(
    ec1: EvohomeClient,
) -> None:
    """If a new session id is rejected too, the 401 is raised (it is retried once)."""

    get = AsyncMock(side_effect=[_unauthorized(), _unauthorized()])

    with (
        patch("evohomeasync.auth.Auth.get", get),
        pytest.raises(exc.ApiCallFailedError) as err,
    ):
        await ec1.get_status()

    assert err.value.status == HTTPStatus.UNAUTHORIZED


async def test_session_id_refreshed_meanwhile(
    ec1: EvohomeClient,
) -> None:
    """A rejected session id is not cleared if another task has since refreshed it."""

    session_manager = ec1._session_manager
    refreshed = "-- refreshed --"

    def refresh_then_reject() -> list[object]:
        session_manager._session_id = refreshed  # by another task, meanwhile
        raise _unauthorized()

    def then_accept() -> list[object]:
        return list(ec1._user_locs or [])

    responses: list[Callable[[], list[object]]] = [refresh_then_reject, then_accept]

    async def side_effect(url: str, schema: object) -> object:
        return responses.pop(0)()

    get = AsyncMock(side_effect=side_effect)

    with patch("evohomeasync.auth.Auth.get", get):
        await ec1.get_status()

    assert session_manager.session_id == refreshed  # not cleared
