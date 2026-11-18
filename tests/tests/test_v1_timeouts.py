"""Test that a timeout is raised as one of the client's exceptions (not a TimeoutError).

A total timeout of an aiohttp request (e.g. ClientTimeout(total=...)) is a TimeoutError
that is not an aiohttp.ClientError (unlike its socket timeouts, ServerTimeoutError), so
it was raised as is. It is a failure to get a reply, like a ClientConnectionError.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest

from evohomeasync import exceptions as exc
from evohomeasync.auth import Auth

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import TokenCacheManager


URL: Final = "accountInfo"


@pytest.fixture
def cache_path(
    tmp_path: Path,
) -> Path:
    """Return the path to a token cache of the test's own (it starts empty)."""
    return tmp_path / ".evo-cache.tst"


async def test_timeout_of_authentication(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test a timeout of the session POST is an AuthConnectionFailedError.

    So it is both an AuthenticationFailedError and an ApiConnectionFailedError.
    """

    timeout = TimeoutError()

    with (
        patch(
            "_evohome.credentials.CredentialsManagerBase._request",
            side_effect=timeout,
        ),
        pytest.raises(exc.AuthenticationFailedError) as err,
    ):
        await credentials_manager.fetch_session_id()

    assert type(err.value) is exc.AuthConnectionFailedError
    assert isinstance(err.value, exc.ApiConnectionFailedError)
    assert err.value.reason is exc.ApiCallErrorReason.CONNECTION_FAILED
    assert err.value.status is None  # there was no response
    assert err.value.__cause__ is timeout
    assert str(err.value).endswith(": TimeoutError")  # str(TimeoutError()) is ''


async def test_timeout_of_api_call(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
) -> None:
    """Test a timeout of a GET (with a valid session) is an ApiConnectionFailedError."""

    credentials_manager.import_session_id(
        {
            "session_id": "-- session id --",
            "session_id_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
        }
    )
    auth = Auth(credentials_manager, client_session)

    timeout = TimeoutError()

    with (
        patch("_evohome.auth.AbstractAuth._request", side_effect=timeout),
        pytest.raises(exc.ApiCallFailedError) as err,
    ):
        await auth.request(HTTPMethod.GET, URL)

    # it is not an AuthenticationFailedError (the credential was valid)
    assert type(err.value) is exc.ApiConnectionFailedError
    assert err.value.reason is exc.ApiCallErrorReason.CONNECTION_FAILED
    assert err.value.status is None  # there was no response
    assert err.value.__cause__ is timeout
    assert str(err.value).endswith(": TimeoutError")
