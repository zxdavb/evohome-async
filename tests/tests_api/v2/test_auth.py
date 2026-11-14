"""Test the vendor's v2 authentication: the token POST, and the bearer it gives.

  POST https://tccna.resideo.com/Auth/OAuth/Token  (off the base URL)

The POST is form-encoded (so its keys are as given, not camelCase), with a Basic
Authorization header (of the vendor's application id). Its scope is always
"EMEA-V1-Basic EMEA-V1-Anonymous". There are two grants:
  - password:       grant_type=password, scope, Username, Password
  - refresh token:  grant_type=refresh_token, scope, refresh_token

Either is answered 200 with a token, whose keys (unlike the rest of the API) are
snake_case, as per OAuth2:
  {"access_token": "...", "token_type": "bearer", "expires_in": 1799,
   "refresh_token": "...", "scope": "EMEA-V1-Basic EMEA-V1-Anonymous"}
(scope is not always present). The access token is then sent as the Authorization
header of every other request: "bearer {access_token}".

A failed POST is a 400 for bad credentials (a bad password, or a bad or expired
refresh token), and a 429 for too many attempts (without a Retry-After header), with
an OAuth2 error, e.g.:
  {"error": "invalid_grant"}, {"error": "attempt_limit_exceeded"}

Only these POSTs are rate-limited: GETs (e.g. of userAccount, with a valid token) were
not, at about 70 a second for 5,000 requests (probed 2026-11-13).

A bad (or expired) access token is a 401, whose message differs from that of a 401
for an id that is not the user's ("You are not allowed to perform this action."):
  [{"code": "Unauthorized", "message": "Unauthorized."}]

The client's handling of these (e.g. re-authenticating when a token is rejected, or
sharing one fetch between concurrent callers) is tested in tests/tests (see its
test_v2_auth_rejected.py, test_v2_urls_cred.py and test_v2_auth.py); these tests
document the wire contract.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from _evohome.const import DEFAULT_RETRY_AFTER
from evohomeasync2 import (
    ApiCallErrorReason,
    ApiCallFailedError,
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadUserCredentialsError,
)
from evohomeasync2.auth import Auth
from evohomeasync2.main import SCH_USR_ACCOUNT
from evohomeasync2.schemas.const import TccFailureCode, TccOAuthError
from tests.const import (
    HEADERS_BASE,
    HEADERS_CRED_V2,
    TEST_PASSWORD,
    TEST_USERNAME,
    URL_BASE_V2,
    URL_CRED_V2,
)

from .vendor import TOKEN, USR_ACCOUNT, USR_ID

if TYPE_CHECKING:
    import aiohttp
    from freezegun.api import FrozenDateTimeFactory

    from evohome_cli.auth import TokenCacheManager
    from evohomeasync2.schemas.account import (
        TccFailureResponseT,
        TccOAuthErrorResponseT,
    )
    from tests.tests.aioresponses import AioResponses


_NOW: Final = "2026-11-13T12:00:00+00:00"

_OLD_REFRESH: Final = "-- refresh token --"  # the one the client holds

_INVALID_GRANT: Final[TccOAuthErrorResponseT] = {"error": TccOAuthError.INVALID_GRANT}

_ATTEMPT_LIMIT_EXCEEDED: Final[TccOAuthErrorResponseT] = {
    "error": TccOAuthError.ATTEMPT_LIMIT_EXCEEDED
}

# the form of each grant, as POSTed
_PASSWORD_GRANT: Final = {
    "grant_type": "password",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
    "Username": TEST_USERNAME,
    "Password": TEST_PASSWORD,
}
_REFRESH_GRANT: Final = {
    "grant_type": "refresh_token",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
    "refresh_token": _OLD_REFRESH,
}


def _clear_tokens(
    manager: TokenCacheManager,
    *,
    refresh_token: str = "",
) -> None:
    """Expire the (cached) access token, and set (or clear) the refresh token."""

    manager.import_access_token(
        {
            "access_token": "",
            "access_token_expires": dt.min.replace(tzinfo=UTC).isoformat(),
            "refresh_token": refresh_token,
        }
    )


async def test_password_grant(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without a refresh token, the client POSTs the password grant (it is a 200)."""

    freezer.move_to(_NOW)
    _clear_tokens(credentials_manager)

    mock.post(URL_CRED_V2, payload=TOKEN)

    await credentials_manager.fetch_access_token()

    mock.assert_called_once_with(
        URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=_PASSWORD_GRANT
    )

    assert credentials_manager.access_token == TOKEN["access_token"]
    assert credentials_manager.refresh_token == TOKEN["refresh_token"]
    assert credentials_manager.access_token_expires == dt.fromisoformat(_NOW) + td(
        seconds=1799
    )


async def test_refresh_grant(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """With a refresh token, the client POSTs the refresh grant (it is a 200)."""

    _clear_tokens(credentials_manager, refresh_token=_OLD_REFRESH)

    mock.post(URL_CRED_V2, payload=TOKEN)

    await credentials_manager.fetch_access_token()

    mock.assert_called_once_with(
        URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=_REFRESH_GRANT
    )

    assert credentials_manager.access_token == TOKEN["access_token"]
    assert credentials_manager.refresh_token == TOKEN["refresh_token"]


async def test_refresh_grant_invalid(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """A bad (or expired) refresh token is a 400 (invalid_grant).

    The client then falls back to the password grant.
    """

    _clear_tokens(credentials_manager, refresh_token=_OLD_REFRESH)

    mock.post(URL_CRED_V2, status=HTTPStatus.BAD_REQUEST, payload=_INVALID_GRANT)
    mock.post(URL_CRED_V2, payload=TOKEN)

    await credentials_manager.fetch_access_token()

    assert mock.requests[(HTTPMethod.POST, URL_CRED_V2)] == [
        {"headers": HEADERS_CRED_V2, "data": _REFRESH_GRANT},
        {"headers": HEADERS_CRED_V2, "data": _PASSWORD_GRANT},
    ]
    assert credentials_manager.access_token == TOKEN["access_token"]


async def test_password_grant_invalid(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Bad user credentials are a 400 (invalid_grant): a BadUserCredentialsError."""

    _clear_tokens(credentials_manager)

    mock.post(URL_CRED_V2, status=HTTPStatus.BAD_REQUEST, payload=_INVALID_GRANT)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(BadUserCredentialsError) as err,
    ):
        await credentials_manager.fetch_access_token()

    mock.assert_called_once_with(
        URL_CRED_V2, HTTPMethod.POST, headers=HEADERS_CRED_V2, data=_PASSWORD_GRANT
    )

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.reason is ApiCallErrorReason.CREDENTIALS_INVALID
    assert err.value.details == {"code": TccOAuthError.INVALID_GRANT}
    assert credentials_manager.access_token == ""


async def test_password_grant_rate_limited(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """Too many attempts are a 429 (attempt_limit_exceeded), without a Retry-After.

    As probed (2026-11-13, with the user's real credentials), after a day of tests: its
    content type was "application/json;charset=UTF-8", and it had no Retry-After header
    (so the client cannot say when to try again). Half an hour later, the limit had
    lifted: 6 tokens were given (within 1.5s), and the 7th POST was a 429. Another 429
    (20:55Z) had lifted 15 minutes later (the client's default retry_after).
    """

    _clear_tokens(credentials_manager)

    mock.post(
        URL_CRED_V2,
        status=HTTPStatus.TOO_MANY_REQUESTS,
        payload=_ATTEMPT_LIMIT_EXCEEDED,
    )

    with pytest.raises(AuthRateLimitExceededError) as err:
        await credentials_manager.fetch_access_token()

    assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert err.value.reason is ApiCallErrorReason.RATE_LIMITED
    assert err.value.details == {"code": TccOAuthError.ATTEMPT_LIMIT_EXCEEDED}
    assert err.value.retry_after == DEFAULT_RETRY_AFTER  # as it had no header


async def test_bearer(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
    mock: AioResponses,
) -> None:
    """The access token is sent as the bearer of every (other) request.

    Auth.get() returns the response with its keys in snake_case (so its schema is the
    client's, not the vendor's).
    """

    auth = Auth(credentials_manager, client_session)

    mock.get(f"{URL_BASE_V2}/userAccount", payload=USR_ACCOUNT)

    result = await auth.get("userAccount", schema=SCH_USR_ACCOUNT)

    mock.assert_called_once_with(
        f"{URL_BASE_V2}/userAccount",
        HTTPMethod.GET,
        headers=HEADERS_BASE
        | {"Authorization": f"bearer {credentials_manager.access_token}"},
    )
    assert result["user_id"] == USR_ID


async def test_bearer_invalid(
    credentials_manager: TokenCacheManager,
    client_session: aiohttp.ClientSession,
    mock: AioResponses,
) -> None:
    """A bad (or expired) access token is a 401 (Unauthorized, 'Unauthorized.').

    The client then fetches another token (once), and makes the request again: if that
    is a 401 too, it is an ApiCallFailedError (not an AuthenticationFailedError).
    """

    auth = Auth(credentials_manager, client_session)
    old_bearer = credentials_manager.access_token

    body: list[TccFailureResponseT] = [
        {"code": TccFailureCode.UNAUTHORIZED, "message": "Unauthorized."}
    ]
    mock.get(f"{URL_BASE_V2}/userAccount", status=HTTPStatus.UNAUTHORIZED, payload=body)
    mock.post(URL_CRED_V2, payload=TOKEN)
    mock.get(f"{URL_BASE_V2}/userAccount", status=HTTPStatus.UNAUTHORIZED, payload=body)

    with pytest.raises(ApiCallFailedError) as err:
        await auth.get("userAccount", schema=SCH_USR_ACCOUNT)

    assert not isinstance(err.value, AuthenticationFailedError)
    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}

    gets = mock.requests[HTTPMethod.GET, f"{URL_BASE_V2}/userAccount"]
    assert [g["headers"]["Authorization"] for g in gets] == [
        f"bearer {old_bearer}",
        f"bearer {TOKEN['access_token']}",
    ]
