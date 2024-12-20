"""evohome-async - validate the handling of vendor APIs (URLs) for Authentication.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

import random
import socket
import string
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import aiohttp
import pytest

from evohomeasync2.auth import _APPLICATION_ID
from evohomeasync2.schemas import (
    TCC_ERROR_RESPONSE,
    TCC_GET_USR_ACCOUNT,
    TCC_POST_OAUTH_TOKEN,
    TCC_STATUS_RESPONSE,
)
from tests.const import (
    _DBG_USE_REAL_AIOHTTP,
    URL_AUTH_V2 as URL_AUTH,
    URL_BASE_V2 as URL_BASE,
)

if TYPE_CHECKING:
    from evohomeasync2.schemas import (
        TccErrorResponseT,
        TccFailureResponseT,
        TccOAuthTokenResponseT,
        TccUsrAccountResponseT,
    )

HEADERS_AUTH = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",  # data=
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
    "Authorization": "Basic " + _APPLICATION_ID,
}
HEADERS_BASE = {
    "Accept": "application/json",
    "Content-Type": "application/json",  # json=
    "Authorization": "Bearer ...",  # "Bearer " + access_token
}


async def handle_too_many_requests(rsp: aiohttp.ClientResponse) -> None:
    assert rsp.status == HTTPStatus.TOO_MANY_REQUESTS  # 429

    response: TccErrorResponseT = await rsp.json()

    # the expected response for TOO_MANY_REQUESTS
    """
        {"error": "attempt_limit_exceeded"}
    """

    assert response["error"] == "attempt_limit_exceeded"
    TCC_ERROR_RESPONSE(response)

    pytest.skip("Too many requests")


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def _test_url_auth_bad0(  # invalid server certificate
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with invalid server certificate."""

    #
    # TEST 0: invalid certificate -> HTTPStatus.UNAUTHORIZED
    parsed_url = urlparse(URL_AUTH)
    ip_address = socket.gethostbyname(parsed_url.hostname)  # type: ignore[arg-type]
    url = f"{parsed_url.scheme}://{ip_address}{parsed_url.path}"  # path[:1] == "/"

    # aiohttp.client_exceptions.ClientConnectorCertificateError:
    # Cannot connect to host 135.224.164.118:443 ssl:True
    # [SSLCertVerificationError: ... certificate is not valid for ...]

    with pytest.raises(aiohttp.ClientConnectorCertificateError):
        async with client_session.post(url, headers=HEADERS_AUTH, data={}) as rsp:
            rsp.raise_for_status()  # raises ClientResponseError


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad1(  # invalid/unknown credentials
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with invalid credentials."""

    #
    # TEST 1: invalid credentials -> HTTPStatus.UNAUTHORIZED
    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # EMEA-V1-Get-Current-User-Account",
        "Username": random.choice(string.ascii_letters),  # noqa: S311
        "Password": "",
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.BAD_REQUEST  # 400

        response: TccErrorResponseT = await rsp.json()

        # the expected response for bad credentials
        """
            {"error": "invalid_grant"}
        """

    assert response["error"] == "invalid_grant"
    TCC_ERROR_RESPONSE(response)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad2(  # invalid/expired access token
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with an invalid access token."""

    # pre-requisite data
    access_token = "invalid access token " + random.choice(string.ascii_letters)  # noqa: S311

    #
    # TEST 2: invalid/expired access token -> HTTPStatus.UNAUTHORIZED
    url = f"{URL_BASE}/userAccount"
    headers = HEADERS_BASE | {"Authorization": "Bearer " + access_token}

    async with client_session.get(url, headers=headers) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.UNAUTHORIZED  # 401

        response: list[TccFailureResponseT] = await rsp.json()

        # the expected response for bad access tokens
        """
            [{
                "code": "Unauthorized",
                "message": "Unauthorized."
            }]
        """

    assert isinstance(response, list) and response[0]["code"] == "Unauthorized"  # noqa: PT018
    TCC_STATUS_RESPONSE(response)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad3(  # invalid/expired refresh token
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with an invalid refresh token."""

    # pre-requisite data
    refresh_token = "invalid refresh token " + random.choice(string.ascii_letters)  # noqa: S311
    #

    # TEST 3: invalid/expired refresh token -> HTTPStatus.UNAUTHORIZED
    data = {
        "grant_type": "refresh_token",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "refresh_token": refresh_token,
    }

    async with client_session.get(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.BAD_REQUEST  # 400

        response: TccErrorResponseT = await rsp.json()

        # the expected response for bad refresh tokens
        """
            {"error": "invalid_grant"}
        """

    assert response["error"] == "invalid_grant"
    TCC_ERROR_RESPONSE(response)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_good(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    # TEST 1: valid credentials (username/password) -> HTTPStatus.OK
    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # EMEA-V1-Get-Current-User-Account",
        "Username": credentials[0],
        "Password": credentials[1],
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.OK  # 200 (400 is bad credentials)

        user_auth: TccOAuthTokenResponseT = await rsp.json()

        # the expected response for good credentials
        """
            {
                "access_token": "HojUMRvmn...",
                "token_type": "bearer",
                "expires_in": 1799,
                "refresh_token": "vdBdHjxK...",
                # "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # optional
            }
        """

    #
    TCC_POST_OAUTH_TOKEN(user_auth)

    # #################################################################################

    # Check the access token by accessing a resource...
    access_token = user_auth["access_token"]
    #

    # TEST 2: valid access token -> HTTPStatus.OK  # 200 (401 is bad token)
    url = f"{URL_BASE}/userAccount"
    headers = HEADERS_BASE | {"Authorization": "Bearer " + access_token}

    async with client_session.get(url, headers=headers) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.OK  # 200

        response: TccUsrAccountResponseT = await rsp.json()

        # the expected response for good access token
        """
            {
                "userId": "1234567",
                "username": "username@email.com",
                "firstname": "David",
                "lastname": "Smith",
                "streetAddress": "1 Main Street",
                "city": "London",
                "postcode": "E1 1AA",
                "country": "UnitedKingdom",
                "language": "enGB"
            }
        """

    assert response["username"] == credentials[0]
    TCC_GET_USR_ACCOUNT(response)

    # #################################################################################

    # Check the refresh token by requesting another access token...
    refresh_token = user_auth["refresh_token"]
    #

    # TEST 3: valid credentials (refresh token)-> HTTPStatus.OK
    data = {
        "grant_type": "refresh_token",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
        "refresh_token": refresh_token,
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:  # 429
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.OK  # 200

        user_auth = await rsp.json()  # TccOAuthTokenResponseT

        # the expected response for good refresh tokens
        """
            {
                "access_token": "HojUMRvmn...",
                "token_type": "bearer",
                "expires_in": 1799,
                "refresh_token": "vdBdHjxK...",
                # "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # optional
            }
        """

    #
    TCC_POST_OAUTH_TOKEN(user_auth)
