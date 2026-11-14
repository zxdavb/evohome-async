"""Test the vendor's v1 authentication: the session POST, and the id it gives.

  POST /session  (https://tccna.resideo.com/WebAPI/api/session)

The POST is form-encoded (so its keys are as given): applicationId (the vendor's id of
this application), username and password. It is answered 200 with a session id (a
GUID), and the user's account:
  {"sessionId": "BE5F40A6-...", "userInfo": {"userID": 2263181, ...}}

The session id is then sent as the sessionId header of every other request. Only the
POST is rate-limited: GETs (e.g. of accountInfo) were not, at about 35 a second for 600
requests (probed 2026-11-13). Its
lifetime is not documented, but has been seen to be 15 minutes (the client assumes so).

A failed POST is a 401 for bad credentials, and a 429 for too many attempts (e.g. a 5th
within a second; without a Retry-After header), each with a list of errors (unlike the
v2 API's OAuth2 error), e.g.:
  [{"code": "EmailOrPasswordIncorrect",
    "message": "The email or password provided is incorrect."}]
  [{"code": "TooManyRequests",
    "message": "Request count limitation exceeded, please try again later."}]

A bad (or expired) session id is a 401 (without the full stop of the v2 API's):
  [{"code": "Unauthorized", "message": "Unauthorized"}]

The client's handling of these (e.g. re-authenticating when a session id is rejected)
is tested in tests/tests (see its test_v1_auth_rejected.py, test_v1_urls_cred.py and
test_v1_auth.py); these tests document the wire contract.
"""

from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from _evohome.const import DEFAULT_RETRY_AFTER
from evohomeasync import (
    ApiCallErrorReason,
    ApiCallFailedError,
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadUserCredentialsError,
)
from evohomeasync.auth import _APPLICATION_ID, SESSION_ID_LIFETIME, Auth
from evohomeasync.main import SCH_GET_ACCOUNT_INFO
from evohomeasync.schemas import TccFailureCode
from tests.const import (
    HEADERS_BASE,
    HEADERS_CRED_V1,
    TEST_PASSWORD,
    TEST_USERNAME,
    URL_BASE_V1,
    URL_CRED_V1,
)

from .vendor import SESSION, USR_ID, USR_INFO

if TYPE_CHECKING:
    import aiohttp
    from freezegun.api import FrozenDateTimeFactory

    from evohome_cli.auth import TokenCacheManager
    from evohomeasync.schemas import TccFailureResponseT
    from tests.tests.aioresponses import AioResponses


_NOW: Final = "2026-11-13T12:00:00+00:00"

# the form of the POST
_CREDENTIALS: Final = {
    "applicationId": _APPLICATION_ID,
    "username": TEST_USERNAME,
    "password": TEST_PASSWORD,
}


async def test_session(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The POST of good credentials is a 200, with a session id (and userInfo)."""

    freezer.move_to(_NOW)
    credentials_manager.clear_session_id()

    mock.post(URL_CRED_V1, payload=SESSION)

    await credentials_manager.fetch_session_id()

    mock.assert_called_once_with(
        URL_CRED_V1, HTTPMethod.POST, headers=HEADERS_CRED_V1, data=_CREDENTIALS
    )

    assert credentials_manager.session_id == SESSION["sessionId"]
    assert credentials_manager.session_id_expires == (
        dt.fromisoformat(_NOW) + SESSION_ID_LIFETIME
    )


async def test_session_invalid(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Bad user credentials are a 401 (EmailOrPasswordIncorrect)."""

    credentials_manager.clear_session_id()

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.EMAIL_OR_PASSWORD_INCORRECT,
            "message": "The email or password provided is incorrect.",
        }
    ]
    mock.post(URL_CRED_V1, status=HTTPStatus.UNAUTHORIZED, payload=body)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(BadUserCredentialsError) as err,
    ):
        await credentials_manager.fetch_session_id()

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.CREDENTIALS_INVALID
    assert err.value.details == {"code": TccFailureCode.EMAIL_OR_PASSWORD_INCORRECT}
    assert credentials_manager.session_id == ""


async def test_session_rate_limited(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """Too many attempts are a 429 (TooManyRequests), without a Retry-After.

    As probed (2026-11-13, with the user's real credentials): 4 sessions were given, and
    the 5th POST (all within a second) was a 429, without a Retry-After header. Half an
    hour later, the limit had lifted: 6 were given, and the 7th was a 429. Another
    429 (20:55Z) had lifted 15 minutes later (the client's default retry_after).
    """

    credentials_manager.clear_session_id()

    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.TOO_MANY_REQUESTS,
            "message": "Request count limitation exceeded, please try again later.",
        }
    ]
    mock.post(URL_CRED_V1, status=HTTPStatus.TOO_MANY_REQUESTS, payload=body)

    with pytest.raises(AuthRateLimitExceededError) as err:
        await credentials_manager.fetch_session_id()

    assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert err.value.reason is ApiCallErrorReason.RATE_LIMITED
    assert err.value.details == {"code": TccFailureCode.TOO_MANY_REQUESTS}
    assert err.value.retry_after == DEFAULT_RETRY_AFTER  # as it had no header


async def test_session_id(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
    mock: AioResponses,
) -> None:
    """The session id is sent as the sessionId header of every (other) request."""

    auth = Auth(credentials_manager, client_session)

    mock.get(f"{URL_BASE_V1}/accountInfo", payload=USR_INFO)

    result = await auth.get("accountInfo", schema=SCH_GET_ACCOUNT_INFO)

    mock.assert_called_once_with(
        f"{URL_BASE_V1}/accountInfo",
        HTTPMethod.GET,
        headers=HEADERS_BASE | {"sessionId": credentials_manager.session_id},
    )
    assert result["user_id"] == USR_ID


async def test_session_id_invalid(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
    mock: AioResponses,
) -> None:
    """A bad (or expired) session id is a 401 (Unauthorized, 'Unauthorized').

    The client then fetches another session id (once), and makes the request again: if
    that is a 401 too, it is an ApiCallFailedError (not an AuthenticationFailedError).
    """

    auth = Auth(credentials_manager, client_session)
    old_session_id = credentials_manager.session_id

    body: list[TccFailureResponseT] = [
        {"code": TccFailureCode.UNAUTHORIZED, "message": "Unauthorized"}
    ]
    mock.get(f"{URL_BASE_V1}/accountInfo", status=HTTPStatus.UNAUTHORIZED, payload=body)
    mock.post(URL_CRED_V1, payload=SESSION)
    mock.get(f"{URL_BASE_V1}/accountInfo", status=HTTPStatus.UNAUTHORIZED, payload=body)

    with pytest.raises(ApiCallFailedError) as err:
        await auth.get("accountInfo", schema=SCH_GET_ACCOUNT_INFO)

    gets = mock.requests[HTTPMethod.GET, f"{URL_BASE_V1}/accountInfo"]
    assert [g["headers"]["sessionId"] for g in gets] == [
        old_session_id,
        SESSION["sessionId"],
    ]

    assert not isinstance(err.value, AuthenticationFailedError)
    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}
