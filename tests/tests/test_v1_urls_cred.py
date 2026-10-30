"""Test the v1 authentication flow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, patch

import pytest

from evohomeasync import EvohomeClient, exceptions as exc
from evohomeasync.auth import _APPLICATION_ID
from tests.const import (
    HEADERS_BASE,
    HEADERS_CRED_V1,
    TEST_PASSWORD,
    TEST_USERNAME,
    URL_CRED_V1,
)

from .aioresponses import aioresponses
from .const import LOG_00, LOG_08, LOG_09, LOG_21, LOG_24, LOG_90, LOG_99

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from evohome_cli.auth import TokenCacheManager


_TEST_SESSION_ID = "-- session ID --"
#


POST_CREDS = (
    "https://tccna.resideo.com/WebAPI/api/session",
    HTTPMethod.POST,
    {
        "headers": HEADERS_CRED_V1,
        "data": {
            "applicationId": _APPLICATION_ID,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        },
    },
)

GET_ACCOUNT = (
    "https://tccna.resideo.com/WebAPI/api/accountInfo",
    HTTPMethod.GET,
    {"headers": HEADERS_BASE | {"sessionId": _TEST_SESSION_ID}},
)


@pytest.fixture(scope="module")
def cache_path(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Return the path to the token cache."""
    return tmp_path_factory.mktemp(__name__) / ".evo-cache.tst"


# NOTE: using fixture_folder will break these tests; we don't want ec1.update() either
@pytest.fixture
async def ec1(
    credentials_manager: TokenCacheManager,
) -> AsyncGenerator[EvohomeClient]:
    """Yield a client with an vailla credentials manager."""

    ec1 = EvohomeClient(credentials_manager)

    try:
        yield ec1
    finally:
        pass


async def test_bad1(  # bad credentials (client_id/secret)
    credentials: tuple[str, str],
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with bad credentials (client_id/secret)."""

    # pre-requisite data (no session_id)
    assert ec1._session_manager.is_session_valid() is False

    # TEST 1: bad credentials (client_id/secret) -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.post(
            URL_CRED_V1,
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "EmailOrPasswordIncorrect", "message": "..."}],
        )

        with pytest.raises(exc.BadUserCredentialsError) as err:
            await ec1.get_status()

        assert err.value.status == HTTPStatus.UNAUTHORIZED

        assert caplog.record_tuples == [LOG_21, LOG_24, LOG_90]

        assert len(rsp.requests) == 1

        # response 0: EmailOrPasswordIncorrect
        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert ec1._session_manager.is_session_valid() is False


async def test_bad2(  # bad session ID
    credentials: tuple[str, str],
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with an invalid/expired session ID."""

    # pre-requisite data (a valid session_id that will be rejected by the server)
    ec1._session_manager._session_id = _TEST_SESSION_ID
    ec1._session_manager._session_id_expires = dt.now(tz=UTC) + td(minutes=15)

    assert ec1._session_manager.is_session_valid() is True

    #
    # TEST 9: bad session ID -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.get(
            "https://tccna.resideo.com/WebAPI/api/accountInfo",
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "Unauthorized", "message": "Unauthorized"}],
        )

        with pytest.raises(exc.AuthenticationFailedError) as err:
            await ec1.get_status()

        assert err.value.status is None  # Connection refused

        assert caplog.record_tuples == [LOG_08, LOG_00, LOG_21, LOG_24, LOG_99]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Unauthorized (bad session ID)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert ec1._session_manager.is_session_valid() is False


async def test_bad3(  # rate limit exceeded (authentication)
    credentials: tuple[str, str],
    ec1: EvohomeClient,
) -> None:
    """Test authentication flow when the vendor's rate limit is exceeded."""

    retry_after = 120

    # pre-requisite data (no session_id)
    ec1._session_manager.clear_session_id()

    assert ec1._session_manager.is_session_valid() is False

    # TEST 3: too many authentications -> HTTPStatus.TOO_MANY_REQUESTS
    with aioresponses() as rsp:
        rsp.post(
            URL_CRED_V1,
            status=HTTPStatus.TOO_MANY_REQUESTS,
            payload=[{"code": "TooManyRequests", "message": "..."}],
            headers={"Retry-After": str(retry_after)},
        )

        with pytest.raises(exc.AuthRateLimitExceededError) as err:
            await ec1.get_status()

        assert isinstance(err.value, exc.ApiRateLimitExceededError)
        assert isinstance(err.value, exc.AuthenticationFailedError)

        assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
        assert err.value.retry_after == retry_after
        assert len(rsp.requests) == 1

        # response 0: Too many requests
        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert ec1._session_manager.is_session_valid() is False


async def test_good(  # good credentials
    credentials: tuple[str, str],
    ec1: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    # pre-requisite data (no session_id)
    assert ec1._session_manager.is_session_valid() is False

    #
    # TEST 9: good session ID -> HTTPStatus.OK
    with aioresponses() as rsp, caplog.at_level(logging.WARNING):  # NOTE: not .DEBUG
        rsp.post(
            URL_CRED_V1,
            status=HTTPStatus.OK,
            payload={
                "sessionId": _TEST_SESSION_ID,
                "userInfo": {
                    "userID": 2263181,
                    "username": "username@email.com",
                    "firstname": "David",
                    "lastname": "Smith",
                    "streetAddress": "1 Main Street",
                    "city": "London",
                    "zipcode": "E1 1AA",
                    "country": "GB",
                    "telephone": "",
                    "userLanguage": "en-GB",
                    "isActivated": True,
                    "deviceCount": 0,
                    "tenantID": 5,
                    "securityQuestion1": "NotUsed",
                    "securityQuestion2": "NotUsed",
                    "securityQuestion3": "NotUsed",
                    "latestEulaAccepted": True,
                },
            },
        )

        with pytest.raises(exc.ApiCallFailedError) as err:
            await ec1.get_status()

        assert err.value.status is None  # Connection refused

        assert caplog.record_tuples == [LOG_09]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Successful authentication (initially)
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

        # response 1: Connection refused (as no subsequent response)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

    assert ec1._session_manager.is_session_valid() is True


async def test_rejected_session_id_refreshed_meanwhile(
    ec1: EvohomeClient,
) -> None:
    """Test a 401 doesn't clear a session ID that another task has since refreshed."""

    session_manager = ec1._session_manager

    # pre-requisite data (a valid session_id that will nonetheless be rejected)
    session_manager._session_id = _TEST_SESSION_ID
    session_manager._session_id_expires = dt.now(tz=UTC) + td(minutes=15)

    new_session_id = "-- new session ID --"
    rejected = False

    def get(url: str, schema: object) -> object:
        nonlocal rejected
        if rejected:
            return {"user_id": 1234567} if url == "accountInfo" else []

        # while this request is in flight, another task refreshes the session ID
        session_manager._session_id = new_session_id
        rejected = True
        raise exc.ApiCallFailedError(
            "GET accountInfo: 401 Unauthorized", status=HTTPStatus.UNAUTHORIZED
        )

    with (
        patch("evohomeasync.auth.Auth.get", AsyncMock(side_effect=get)) as req,
        patch.object(session_manager, "fetch_session_id") as fetch,
    ):
        await ec1._get_config()

    req.assert_any_await("accountInfo", schema=ANY)
    fetch.assert_not_awaited()
    assert session_manager.session_id == new_session_id
