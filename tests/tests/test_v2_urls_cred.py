"""evohome-async - validate the v2 API authentication flow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohome_cli.auth import TokenCacheManager
from evohomeasync2 import EvohomeClient, exceptions as exc
from tests.const import (
    HEADERS_BASE,
    HEADERS_CRED_V2,
    TEST_PASSWORD,
    TEST_USERNAME,
    URL_CRED_V2,
)

from .aioresponses import aioresponses
from .const import (
    LOG_01,
    LOG_02,
    LOG_03,
    LOG_04,
    LOG_20,
    LOG_28,
    LOG_29,
    LOG_90,
    LOG_99,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from freezegun.api import FrozenDateTimeFactory

    from evohome_cli.auth import TokenCacheManager


URL_BASE_V2 = "https://tccna.resideo.com/WebAPI/emea/api/v1"

_TEST_ACCESS_TOKEN = "-- access token --"  # noqa: S105
_TEST_REFRESH_TOKEN = "-- refresh token --"  # noqa: S105


POST_CREDS = (
    "https://tccna.resideo.com/Auth/OAuth/Token",
    HTTPMethod.POST,
    {
        "headers": HEADERS_CRED_V2,
        "data": {
            "grant_type": "password",
            "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
            "Username": TEST_USERNAME,
            "Password": TEST_PASSWORD,
        },
    },
)

POST_REFRESH = (
    "https://tccna.resideo.com/Auth/OAuth/Token",
    HTTPMethod.POST,
    {
        "headers": HEADERS_CRED_V2,
        "data": {
            "grant_type": "refresh_token",
            "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
            "refresh_token": _TEST_REFRESH_TOKEN,
        },
    },
)

GET_ACCOUNT = (
    "https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount",
    HTTPMethod.GET,
    {
        "headers": HEADERS_BASE | {"Authorization": f"bearer {_TEST_ACCESS_TOKEN}"},
    },
)


@pytest.fixture(scope="module")
def cache_path(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Return the path to the token cache."""
    return tmp_path_factory.mktemp(__name__) / ".evo-cache.tst"


# NOTE: using fixture_folder will break these tests; we don't want evo.update() either
@pytest.fixture
async def evohome_v2(
    credentials_manager: TokenCacheManager,
) -> AsyncGenerator[EvohomeClient]:
    """Yield a client with an vailla credentials manager."""

    evo = EvohomeClient(credentials_manager)

    try:
        yield evo
    finally:
        pass


async def test_bad1(  # bad credentials (client_id/secret)
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with bad credentials (client_id/secret)."""

    # pre-requisite data (no session_id)
    assert evohome_v2._token_manager.is_token_valid() is False

    # TEST 1: bad credentials (client_id/secret) -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.BAD_REQUEST,
            payload={"error": "invalid_grant"},
        )

        with pytest.raises(exc.BadUserCredentialsError) as err:
            await evohome_v2.update()

        assert err.value.status == HTTPStatus.BAD_REQUEST
        assert caplog.record_tuples == [LOG_01, LOG_04, LOG_90]
        assert len(rsp.requests) == 1

        # response 0: Unauthorized (bad credentials)
        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert evohome_v2._token_manager.is_token_valid() is False


async def test_bad2(  # bad access token
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with an invalid/expired access token."""

    # pre-requisite data (a valid access token that will nonetheless be rejected)
    evohome_v2._token_manager._access_token = _TEST_ACCESS_TOKEN
    evohome_v2._token_manager._access_token_expires = dt.now(tz=UTC) + td(minutes=15)
    evohome_v2._token_manager._refresh_token = _TEST_REFRESH_TOKEN

    assert evohome_v2._token_manager.is_token_valid() is True

    # TEST 9: bad access token -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.get(
            "https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount",
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "Unauthorized", "message": "Unauthorized"}],
        )

        with pytest.raises(exc.AuthenticationFailedError) as err:
            await evohome_v2.update()

        assert err.value.status is None  # Connection refused
        assert caplog.record_tuples == [LOG_28, LOG_20, LOG_01, LOG_02, LOG_99]
        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Unauthorized (bad access token)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(POST_REFRESH[0], POST_REFRESH[1], **POST_REFRESH[2])

    assert evohome_v2._token_manager.is_token_valid() is False


async def test_bad3(  # bad credentials (refresh token)
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with invalid/unknown credentials (refresh token)."""

    # pre-requisite data (an expired access token, with a bad refresh token)
    evohome_v2._token_manager._access_token = _TEST_ACCESS_TOKEN
    evohome_v2._token_manager._access_token_expires = dt.now(tz=UTC) - td(minutes=15)
    evohome_v2._token_manager._refresh_token = _TEST_REFRESH_TOKEN

    assert evohome_v2._token_manager.is_token_valid() is False

    # TEST 9: bad session id -> HTTPStatus.BAD_REQUEST
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.BAD_REQUEST,
            payload={"error": "invalid_grant"},
        )

        with pytest.raises(exc.AuthenticationFailedError) as err:
            await evohome_v2.update()

        assert err.value.status is None  # Connection refused
        assert caplog.record_tuples == [LOG_01, LOG_02, LOG_03, LOG_04, LOG_99]
        assert len(rsp.requests) == 1

        # response 0: invalid_grant (bad refresh token)
        rsp.assert_any_call(POST_REFRESH[0], POST_REFRESH[1], **POST_REFRESH[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert evohome_v2._token_manager.is_token_valid() is False


@pytest.mark.parametrize(
    ("headers", "retry_after"),
    [
        (None, None),
        ({"Retry-After": "120"}, 120.0),  # as delay-seconds
        ({"Retry-After": "Wed, 01 Jan 2025 00:02:00 GMT"}, 120.0),  # as HTTP-date
        ({"Retry-After": "a while"}, None),
    ],
)
async def test_bad4(  # rate limit exceeded (authentication)
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
    headers: dict[str, str] | None,
    retry_after: float | None,
) -> None:
    """Test authentication flow when the vendor's rate limit is exceeded."""

    freezer.move_to("2025-01-01T00:00:00+00:00")

    # pre-requisite data (no access token)
    evohome_v2._token_manager.clear_access_token()

    assert evohome_v2._token_manager.is_token_valid() is False

    # TEST 4: too many authentications -> HTTPStatus.TOO_MANY_REQUESTS
    with aioresponses() as rsp:
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.TOO_MANY_REQUESTS,
            payload={"error": "attempt_limit_exceeded"},
            headers=headers,
        )

        with pytest.raises(exc.AuthRateLimitExceededError) as err:
            await evohome_v2.update()

        assert isinstance(err.value, exc.ApiRateLimitExceededError)
        assert isinstance(err.value, exc.AuthenticationFailedError)

        assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
        assert err.value.retry_after == retry_after
        assert len(rsp.requests) == 1

    assert evohome_v2._token_manager.is_token_valid() is False


async def test_bad5(  # rate limit exceeded (authorization)
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
) -> None:
    """Test authorization flow when the vendor's rate limit is exceeded."""

    retry_after = 60

    # pre-requisite data (a valid access token)
    evohome_v2._token_manager._access_token = _TEST_ACCESS_TOKEN
    evohome_v2._token_manager._access_token_expires = dt.now(tz=UTC) + td(minutes=15)
    evohome_v2._token_manager._refresh_token = _TEST_REFRESH_TOKEN

    assert evohome_v2._token_manager.is_token_valid() is True

    # TEST 5: too many requests -> HTTPStatus.TOO_MANY_REQUESTS
    with aioresponses() as rsp:
        rsp.get(
            "https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount",
            status=HTTPStatus.TOO_MANY_REQUESTS,
            payload=[{"code": "TooManyRequests", "message": "..."}],
            headers={"Retry-After": str(retry_after)},
        )

        with pytest.raises(exc.ApiRateLimitExceededError) as err:
            await evohome_v2.update()

        assert not isinstance(err.value, exc.AuthenticationFailedError)

        assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
        assert err.value.retry_after == retry_after
        assert len(rsp.requests) == 1

        # response 0: Too many requests (the access token is not rejected)
        rsp.assert_called_once_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

    assert evohome_v2._token_manager.is_token_valid() is True

    evohome_v2._token_manager.clear_access_token()  # is cached; don't leak to next test


@pytest.mark.parametrize(
    ("method", "status", "expected"),
    [
        (HTTPMethod.GET, HTTPStatus.BAD_REQUEST, exc.ApiCallRejectedError),
        (HTTPMethod.GET, HTTPStatus.FORBIDDEN, exc.ApiCallRejectedError),
        (HTTPMethod.GET, HTTPStatus.NOT_FOUND, exc.ApiCallRejectedError),
        (HTTPMethod.GET, HTTPStatus.UNAUTHORIZED, exc.ApiCallFailedError),
        (HTTPMethod.GET, HTTPStatus.INTERNAL_SERVER_ERROR, exc.ApiCallFailedError),
        (HTTPMethod.PUT, HTTPStatus.BAD_REQUEST, exc.ApiCallRejectedError),
        (HTTPMethod.PUT, HTTPStatus.NOT_FOUND, exc.ApiCallRejectedError),
        (HTTPMethod.PUT, HTTPStatus.UNAUTHORIZED, exc.ApiCallFailedError),
        (HTTPMethod.PUT, HTTPStatus.SERVICE_UNAVAILABLE, exc.ApiCallFailedError),
    ],
    ids=lambda v: str(v.value) if isinstance(v, HTTPStatus) else None,
)
async def test_rejected(  # the vendor rejects a request (a 4xx, but not a 401/429)
    evohome_v2: EvohomeClient,
    method: HTTPMethod,
    status: HTTPStatus,
    expected: type[exc.ApiCallFailedError],
) -> None:
    """Test a 4xx (other than a 401/429) is an ApiCallRejectedError, GET or PUT."""

    # pre-requisite data (a valid access token)
    evohome_v2._token_manager._access_token = _TEST_ACCESS_TOKEN
    evohome_v2._token_manager._access_token_expires = dt.now(tz=UTC) + td(minutes=15)
    evohome_v2._token_manager._refresh_token = _TEST_REFRESH_TOKEN

    url = "temperatureControlSystem/1234567/mode"
    payload = [{"code": "SystemModeChangeTimeUntilNotSet", "message": "..."}]

    with aioresponses() as rsp:
        if method == HTTPMethod.GET:
            rsp.get(f"{URL_BASE_V2}/{url}", status=status, payload=payload)
        else:
            rsp.put(f"{URL_BASE_V2}/{url}", status=status, payload=payload)

        with pytest.raises(exc.ApiCallFailedError) as err:
            await evohome_v2.auth.request(
                method,
                url,
                **(
                    {"json": {"systemMode": "Auto"}} if method == HTTPMethod.PUT else {}
                ),
            )

        assert type(err.value) is expected
        assert err.value.status == status
        assert len(rsp.requests) == 1

    evohome_v2._token_manager.clear_access_token()  # is cached; don't leak to next test


async def test_good(  # good credentials
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    # pre-requisite data (no session_id)
    assert evohome_v2._token_manager.is_token_valid() is False

    #
    # TEST 1: good credentials (client_id/secret) -> HTTPStatus.OK
    with aioresponses() as rsp, caplog.at_level(logging.WARNING):
        rsp.post(
            URL_CRED_V2,
            status=HTTPStatus.OK,
            payload={
                "access_token": _TEST_ACCESS_TOKEN,
                "token_type": "bearer",
                "expires_in": 1799,
                "refresh_token": _TEST_REFRESH_TOKEN,
                # "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # optional
            },
        )

        with pytest.raises(exc.ApiCallFailedError) as err:
            await evohome_v2.update()

        assert err.value.status is None  # Connection refused
        assert caplog.record_tuples == [LOG_29]
        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Successful authentication
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

    assert evohome_v2._token_manager.is_token_valid() is True
