"""evohome-async - validate the v2 API authentication flow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest
from aioresponses import aioresponses
from cli.auth import CredentialsManager

from evohome.auth import _HINT_BAD_CREDS, _HINT_CHECK_NETWORK
from evohomeasync2 import EvohomeClient, exceptions as exc
from tests.const import HEADERS_CRED_V2, URL_CRED_V2

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from cli.auth import CredentialsManager


MSG_INVALID_TOKEN: Final = (
    "The access_token has been rejected (will re-authenticate): "  # noqa: S105
    "GET https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount: "
    '401 Unauthorized, response=[{"code": "Unauthorized", "message": "Unauthorized"}]'
)

_TEST_ACCESS_TOKEN = "-- access token --"  # noqa: S105
_TEST_REFRESH_TOKEN = "-- refresh token --"  # noqa: S105


@pytest.fixture(scope="module")
def cache_file(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Return the path to the token cache."""
    return tmp_path_factory.mktemp(__name__) / ".evo-cache.tst"


# NOTE: using fixture_folder will break these tests, and we don't want .update() either
@pytest.fixture
async def evohome_v2(
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
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow with bad credentials (client_id/secret)."""

    # pre-requisite data (no session_id)
    assert evohome_v2._token_manager.is_access_token_valid() is False

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

        assert caplog.record_tuples == [
            (
                "evohome.auth",
                logging.DEBUG,
                "Null/Expired/Invalid access_token",
            ),
            ("evohome.auth", logging.DEBUG, " - authenticating with client_id/secret"),
            ("evohome.auth", logging.ERROR, _HINT_BAD_CREDS),
        ]

        assert len(rsp.requests) == 1

        # response 0: Unauthorized (bad credentials)
        rsp.assert_called_once_with(
            "https://tccna.resideo.com/Auth/OAuth/Token",
            HTTPMethod.POST,
            headers=HEADERS_CRED_V2,
            data={
                "grant_type": "password",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "Username": credentials[0],
                "Password": credentials[1],
            },
        )

    assert evohome_v2._token_manager.is_access_token_valid() is False


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

    assert evohome_v2._token_manager.is_access_token_valid() is True

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

        assert caplog.record_tuples == [
            ("evohomeasync2", logging.WARNING, MSG_INVALID_TOKEN),
            (
                "evohome.auth",
                logging.DEBUG,
                "Null/Expired/Invalid access_token",
            ),
            ("evohome.auth", logging.DEBUG, " - authenticating with the refresh_token"),
            ("evohome.auth", logging.ERROR, _HINT_CHECK_NETWORK),  # Connection refused
        ]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Unauthorized (bad access token)
        rsp.assert_called_with(
            "https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount",
            HTTPMethod.GET,
            headers={
                "Accept": "application/json",
                "Connection": "Keep-Alive",
                "Authorization": f"bearer {_TEST_ACCESS_TOKEN}",
            },
        )

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(
            "https://tccna.resideo.com/Auth/OAuth/Token",
            HTTPMethod.POST,
            headers=HEADERS_CRED_V2,
            data={
                "grant_type": "refresh_token",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "refresh_token": _TEST_REFRESH_TOKEN,
            },
        )

    assert evohome_v2._token_manager.is_access_token_valid() is False


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

    assert evohome_v2._token_manager.is_access_token_valid() is False

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

        assert caplog.record_tuples == [
            (
                "evohome.auth",
                logging.DEBUG,
                "Null/Expired/Invalid access_token",
            ),
            ("evohome.auth", logging.DEBUG, " - authenticating with the refresh_token"),
            ("evohome.auth", logging.DEBUG, "Expired/invalid refresh_token"),
            ("evohome.auth", logging.DEBUG, " - authenticating with client_id/secret"),
            ("evohome.auth", logging.ERROR, _HINT_CHECK_NETWORK),  # Connection refused
        ]

        assert len(rsp.requests) == 1

        # response 0: invalid_grant (bad refresh token)
        rsp.assert_any_call(
            "https://tccna.resideo.com/Auth/OAuth/Token",
            HTTPMethod.POST,
            headers=HEADERS_CRED_V2,
            data={
                "grant_type": "refresh_token",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "refresh_token": _TEST_REFRESH_TOKEN,
            },
        )

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(
            "https://tccna.resideo.com/Auth/OAuth/Token",
            HTTPMethod.POST,
            headers=HEADERS_CRED_V2,
            data={
                "grant_type": "password",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "Username": credentials[0],
                "Password": credentials[1],
            },
        )

    assert evohome_v2._token_manager.is_access_token_valid() is False


async def test_good(  # good credentials
    credentials: tuple[str, str],
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    # pre-requisite data (no session_id)
    assert evohome_v2._token_manager.is_access_token_valid() is False

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

        with pytest.raises(exc.ApiRequestFailedError) as err:
            await evohome_v2.update()

        assert err.value.status is None  # Connection refused

        assert caplog.record_tuples == [
            ("evohomeasync2", logging.ERROR, _HINT_CHECK_NETWORK),  # Connection refused
        ]

        assert len(rsp.requests) == 2  # noqa: PLR2004

        # response 0: Successful authentication
        rsp.assert_called_with(
            "https://tccna.resideo.com/Auth/OAuth/Token",
            HTTPMethod.POST,
            headers=HEADERS_CRED_V2,
            data={
                "grant_type": "password",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "Username": credentials[0],
                "Password": credentials[1],
            },
        )

        # response 1: Connection refused (as no response provided by us)
        rsp.assert_called_with(
            "https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount",
            HTTPMethod.GET,
            headers={
                "Accept": "application/json",
                "Connection": "Keep-Alive",
                "Authorization": f"bearer {_TEST_ACCESS_TOKEN}",
            },
        )

    assert evohome_v2._token_manager.is_access_token_valid() is True
