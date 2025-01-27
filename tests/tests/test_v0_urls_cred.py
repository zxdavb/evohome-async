"""evohome-async - validate the v0 API authentication flow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest
from aioresponses import aioresponses

from evohome.const import HINT_CHECK_NETWORK
from evohomeasync import EvohomeClient, exceptions as exc
from evohomeasync.auth import _APPLICATION_ID
from tests.const import (
    HEADERS_BASE,
    HEADERS_CRED_V0,
    TEST_PASSWORD,
    TEST_USERNAME,
    URL_CRED_V0,
)

from .const import LOG_04, LOG_11, LOG_12, LOG_90, LOG_91

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from cli.auth import CredentialsManager


_TEST_SESSION_ID = "-- session id --"
#


POST_CREDS = (
    "https://tccna.resideo.com/WebAPI/api/session",
    HTTPMethod.POST,
    {
        "headers": HEADERS_CRED_V0,
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
def cache_file(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Return the path to the token cache."""
    return tmp_path_factory.mktemp(__name__) / ".evo-cache.tst"


# NOTE: using fixture_folder will break these tests; we don't want evo.update() either
@pytest.fixture
async def evohome_v0(
    credentials_manager: CredentialsManager,
) -> AsyncGenerator[EvohomeClient]:
    """Yield a client with an vailla credentials manager."""

    evo = EvohomeClient(credentials_manager)

    try:
        yield evo
    finally:
        pass


async def test_bad1(  # bad credentials (client_id/secret)
    credentials: tuple[str, str],
    evohome_v0: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with bad credentials (client_id/secret)."""

    # pre-requisite data (no session_id)
    assert evohome_v0._session_manager.is_session_valid() is False

    # TEST 1: bad credentials (client_id/secret) -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.post(
            URL_CRED_V0,
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "EmailOrPasswordIncorrect", "message": "..."}],
        )

        with pytest.raises(exc.BadUserCredentialsError) as err:
            await evohome_v0.update()

        assert err.value.status == HTTPStatus.UNAUTHORIZED

        assert caplog.record_tuples == [LOG_90, LOG_04, LOG_11]

        assert len(rsp.requests) == 1

        # response 0: EmailOrPasswordIncorrect
        rsp.assert_called_once_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert evohome_v0._session_manager.is_session_valid() is False


async def test_bad2(  # bad session id
    credentials: tuple[str, str],
    evohome_v0: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with an invalid/expired session id."""

    # pre-requisite data (a valid session_id that will be rejected by the server)
    evohome_v0._session_manager._session_id = _TEST_SESSION_ID
    evohome_v0._session_manager._session_id_expires = dt.now(tz=UTC) + td(minutes=15)

    assert evohome_v0._session_manager.is_session_valid() is True

    #
    # TEST 9: bad session id -> HTTPStatus.UNAUTHORIZED
    with aioresponses() as rsp, caplog.at_level(logging.DEBUG):
        rsp.get(
            "https://tccna.resideo.com/WebAPI/api/accountInfo",
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "Unauthorized", "message": "Unauthorized"}],
        )

        with pytest.raises(exc.AuthenticationFailedError) as err:
            await evohome_v0.update()

        assert err.value.status is None  # Connection refused

        assert caplog.record_tuples == [LOG_91, LOG_90, LOG_04, LOG_12]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Unauthorized (bad session id)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

    assert evohome_v0._session_manager.is_session_valid() is False


async def test_good(  # good credentials
    credentials: tuple[str, str],
    evohome_v0: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    # pre-requisite data (no session_id)
    assert evohome_v0._session_manager.is_session_valid() is False

    #
    # TEST 9: good session id -> HTTPStatus.OK
    with aioresponses() as rsp, caplog.at_level(logging.WARNING):  # NOTE: not .DEBUG
        rsp.post(
            URL_CRED_V0,
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
                    "latestEulaAccepted": False,
                },
            },
        )

        with pytest.raises(exc.ApiRequestFailedError) as err:
            await evohome_v0.update()

        assert err.value.status is None  # Connection refused

        assert caplog.record_tuples == [
            ("evohome.auth", logging.ERROR, HINT_CHECK_NETWORK),  # Connection refused
        ]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Successful authentication
        rsp.assert_called_with(POST_CREDS[0], POST_CREDS[1], **POST_CREDS[2])

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(GET_ACCOUNT[0], GET_ACCOUNT[1], **GET_ACCOUNT[2])

    assert evohome_v0._session_manager.is_session_valid() is True
