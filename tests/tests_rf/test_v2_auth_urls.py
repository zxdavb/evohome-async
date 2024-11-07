#!/usr/bin/env python3
"""evohome-async - validate authentication with the vendor's v2 API."""

from __future__ import annotations

import random
import string
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohomeasync2.auth import _APPLICATION_ID, HOSTNAME, SCH_OAUTH_TOKEN
from evohomeasync2.schema import SCH_USER_ACCOUNT

from .conftest import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    import aiohttp


URL_AUTH = f"https://{HOSTNAME}/Auth/OAuth/Token"
URL_BASE = f"https://{HOSTNAME}/WebAPI/emea/api/v1/"

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
    "Authorization": None,  # "Bearer " + access_token
}


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="is not using the real aiohttp")
async def test_url_auth_bad1(  # invalid/unknown credentials
    client_session: aiohttp.ClientSession,
) -> None:
    """Test the authentication flow with bad credentials."""

    # invalid credentials -> HTTPStatus.UNAUTHORIZED
    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # EMEA-V1-Get-Current-User-Account",
        "Username": random.choice(string.ascii_letters),  # noqa: S311
        "Password": "",
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        assert rsp.status == HTTPStatus.BAD_REQUEST

        response: dict = await rsp.json()

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert response["error"] == "attempt_limit_exceeded"
            pytest.skip("Too many requests")

        """
            {'error': 'invalid_grant'}
        """

    assert response["error"] == "invalid_grant"


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="is not using the real aiohttp")
async def test_url_auth_bad2(  # invalid/expired access token
    client_session: aiohttp.ClientSession,
) -> None:
    """Test the authentication flow with an invalid session id,"""

    # pre-requisite data
    access_token = "bad/expired acesss token " + random.choice(string.ascii_letters)  # noqa: S311
    #

    # invalid/expired session id -> HTTPStatus.UNAUTHORIZED
    url = URL_BASE + "userAccount"
    headers = HEADERS_BASE | {"Authorization": "Bearer " + access_token}

    async with client_session.get(url, headers=headers) as rsp:
        assert rsp.status == HTTPStatus.UNAUTHORIZED

        response: dict = await rsp.json()

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert response["error"] == "attempt_limit_exceeded"
            pytest.skip("Too many requests")

        """
            [{
                'code': 'Unauthorized',
                'message': 'Unauthorized.'
            }]
        """

    assert response[0]["code"] == "Unauthorized"
    assert response[0]["message"] and isinstance(response[0]["message"], str)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="is not using the real aiohttp")
async def test_url_auth_good(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """Test the authentication flow (and authorization) with good credentials."""

    # valid credentials -> HTTPStatus.OK
    data = {
        "grant_type": "password",
        "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",  # EMEA-V1-Get-Current-User-Account",
        "Username": credentials[0],
        "Password": credentials[1],
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        assert rsp.status in [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]

        response: dict = await rsp.json()

        """
            {'error': 'attempt_limit_exceeded'}
        """

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert response["error"] == "attempt_limit_exceeded"
            pytest.skip("Too many requests")

        """
            {
                'access_token': 'HojUMRvmn...",
                'token_type': 'bearer',
                'expires_in': 1799,
                'refresh_token': 'vdBdHjxK...",
                # 'scope': 'EMEA-V1-Basic EMEA-V1-Anonymous'  # optional
            }
        """

    assert response["access_token"] and isinstance(response["access_token"], str)
    assert response["expires_in"] <= 1800

    assert SCH_OAUTH_TOKEN(response), response

    # #################################################################################

    # Check the access token by accessing a resource...
    access_token = response["access_token"]
    #

    # valid access token -> HTTPStatus.OK
    url = URL_BASE + "userAccount"
    headers = HEADERS_BASE | {"Authorization": "Bearer " + access_token}

    async with client_session.get(url, headers=headers) as rsp:
        assert rsp.status in [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]

        response: dict = await rsp.json()

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert response["error"] == "attempt_limit_exceeded"
            pytest.skip("Too many requests")

        """
            {
                'userId': '1234567',
                'username': 'username@email.com',
                'firstname': 'David',
                'lastname': 'Smith',
                'streetAddress': '1 Main Street',
                'city': 'London',
                'postcode': 'E1 1AA',
                'country': 'UnitedKingdom',
                'language': 'enGB'
            }
        """

    assert response["userId"] and isinstance(response["userId"], str)
    assert response["username"] and response["username"] == credentials[0]

    assert SCH_USER_ACCOUNT(response), response
