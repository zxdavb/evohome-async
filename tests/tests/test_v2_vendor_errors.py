"""Test that an ApiCallFailedError has all the errors of the vendor's response.

A failed request's response may list several errors, e.g. a PUT of {} to a TCS's mode
(probed 2026-11-14), each of whose parameterName is the parameter:
  [{"code": "ParameterIsMissing", "parameterName": "SystemMode", "message": ...},
   {"code": "ParameterIsMissing", "parameterName": "Permanent", "message": ...}]

So `errors` is all of them (in snake_case, in order), and `details["code"]` is the code
of the first one. An OAuth error (e.g. {"error": "invalid_grant"}) is not a list.
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import exceptions as exc
from evohomeasync2.auth import Auth
from tests.const import URL_BASE_V2, URL_CRED_V2

from .aioresponses import aioresponses

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp

    from evohome_cli.auth import TokenCacheManager


URL: Final = "temperatureControlSystem/1234567/mode"

PARAMETERS_ARE_MISSING: Final = [
    {
        "code": "ParameterIsMissing",
        "parameterName": "SystemMode",
        "message": "Parameter is missing.",
    },
    {
        "code": "ParameterIsMissing",
        "parameterName": "Permanent",
        "message": "Parameter is missing.",
    },
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
    """Return an Auth with a valid access token."""

    credentials_manager.import_access_token(
        {
            "access_token": "-- access token --",
            "access_token_expires": (dt.now(tz=UTC) + td(minutes=15)).isoformat(),
            "refresh_token": "",
        }
    )
    return Auth(credentials_manager, client_session)


async def test_errors_of_a_rejected_request(
    auth: Auth,
) -> None:
    """Test the errors of a 400 are all of the vendor's, with their parameter names."""

    with aioresponses() as rsp:
        rsp.put(
            f"{URL_BASE_V2}/{URL}",
            status=HTTPStatus.BAD_REQUEST,
            payload=PARAMETERS_ARE_MISSING,
        )

        with pytest.raises(exc.ApiCallRejectedError) as err:
            await auth.put(URL, {})

    assert err.value.errors == (
        {
            "code": "ParameterIsMissing",
            "message": "Parameter is missing.",
            "parameter_name": "SystemMode",
        },
        {
            "code": "ParameterIsMissing",
            "message": "Parameter is missing.",
            "parameter_name": "Permanent",
        },
    )
    assert err.value.details == {"code": "ParameterIsMissing"}  # of the first


async def test_errors_of_a_non_list_response(
    auth: Auth,
) -> None:
    """Test a response that is not a list (e.g. a 404 of an unknown URL) has none."""

    with aioresponses() as rsp:
        rsp.put(
            f"{URL_BASE_V2}/{URL}",
            status=HTTPStatus.NOT_FOUND,
            payload={"message": "No HTTP resource was found that matches the request."},
        )

        with pytest.raises(exc.ApiCallRejectedError) as err:
            await auth.put(URL, {})

    assert err.value.errors == ()
    assert err.value.details == {}


async def test_errors_of_bad_credentials(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test an OAuth error (a dict, not a list) has no errors, but has its code."""

    with aioresponses() as rsp:
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.BAD_REQUEST,
            payload={"error": "invalid_grant"},
        )

        with pytest.raises(exc.BadUserCredentialsError) as err:
            await credentials_manager.fetch_access_token()

    assert err.value.errors == ()
    assert err.value.details == {"code": "invalid_grant"}
