"""Test that an ApiCallFailedError has all the errors of the vendor's response.

A failed request's response may list several errors, each naming its field only in
its message, e.g. a PUT of {} to a zone's heatSetpoint (probed 2026-11-14):
  [{"code": "ParameterIsMissing", "message": "'Value' is required."},
   {"code": "ParameterIsMissing", "message": "'Status' is required."}, ...]

So `errors` is all of them (in order), and `details["code"]` is the code of the first.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync import exceptions as exc
from evohomeasync.auth import Auth
from tests.const import URL_BASE_V1, URL_CRED_V1

from .aioresponses import aioresponses

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import TokenCacheManager


URL: Final = "devices/1234567/thermostat/changeableValues/heatSetpoint"

# provenance: probed 2026-11-14 (a PUT of {})
PARAMETERS_ARE_MISSING: Final = [
    {"code": "ParameterIsMissing", "message": "'Value' is required."},
    {"code": "ParameterIsMissing", "message": "'Status' is required."},
    {"code": "ParameterIsMissing", "message": "'NextTime' is required."},
    {"code": "ValueOutOfRange", "message": "Value of field Value is out of range."},
]

EMAIL_OR_PASSWORD_INCORRECT: Final = [
    {
        "code": "EmailOrPasswordIncorrect",
        "message": "The email or password provided is incorrect.",
    }
]

TOO_MANY_REQUESTS: Final = [
    {
        "code": "TooManyRequests",
        "message": "Request count limitation exceeded, please try again later.",
    }
]


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
    """Return an Auth with a valid session id."""

    credentials_manager.import_session_id(
        {
            "session_id": "-- session id --",
            "session_id_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
        }
    )
    return Auth(credentials_manager, client_session)


async def test_errors_of_a_rejected_request(
    auth: Auth,
) -> None:
    """Test the errors of a 400 are all of the vendor's (none has a parameter name)."""

    with aioresponses() as rsp:
        rsp.put(
            f"{URL_BASE_V1}/{URL}",
            status=HTTPStatus.BAD_REQUEST,
            payload=PARAMETERS_ARE_MISSING,
        )

        with pytest.raises(exc.ApiCallRejectedError) as err:
            await auth.put(URL, {})

    assert err.value.errors == tuple(PARAMETERS_ARE_MISSING)
    assert err.value.details == {"code": "ParameterIsMissing"}  # of the first


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        pytest.param(
            HTTPStatus.UNAUTHORIZED,
            EMAIL_OR_PASSWORD_INCORRECT,
            exc.BadUserCredentialsError,
            id="bad_credentials",
        ),
        pytest.param(
            HTTPStatus.TOO_MANY_REQUESTS,
            TOO_MANY_REQUESTS,
            exc.AuthRateLimitExceededError,
            id="rate_limited",
        ),
    ],
)
async def test_errors_of_a_failed_session_request(
    credentials_manager: TokenCacheManager,
    status: HTTPStatus,
    body: list[dict[str, str]],
    error: type[exc.AuthenticationFailedError],
) -> None:
    """Test a failed session POST has the vendor's errors."""

    with aioresponses() as rsp:
        rsp.post(URL_CRED_V1, status=status, payload=body)

        with pytest.raises(error) as err:
            await credentials_manager.fetch_session_id()

    assert err.value.errors == tuple(body)
    assert err.value.details == {"code": body[0]["code"]}
