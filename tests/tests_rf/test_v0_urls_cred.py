"""Validate the handling of the vendor's v0 APIs (URLs) for Authentication.

This is used to:
a) document the RESTful API that is provided by the vendor
b) confirm the faked server (if any) is behaving as per a)

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

from evohomeasync.auth import _APPLICATION_ID
from evohomeasync.schemas import (
    TCC_FAILURE_RESPONSE,
    TCC_GET_USR_INFO,
    TCC_POST_USR_SESSION,
)
from tests.const import (
    _DBG_TEST_CRED_URLS,
    _DBG_USE_REAL_AIOHTTP,
    HEADERS_BASE,
    HEADERS_CRED_V0,
    URL_BASE_V0,
    URL_CRED_V0,
)

if TYPE_CHECKING:
    from evohomeasync.schemas import (
        TccFailureResponseT,
        TccSessionResponseT,
        TccUserAccountInfoResponseT,
    )


async def _skip_if_too_many_requests(rsp: aiohttp.ClientResponse) -> None:
    if rsp.status != HTTPStatus.TOO_MANY_REQUESTS:  # 429
        return

    response: list[TccFailureResponseT] = await rsp.json()

    # the expected response for TOO_MANY_REQUESTS
    """
        [{
            "code": "TooManyRequests",
            "message": "Request count limitation exceeded, please try again later."
        }]
    """

    assert response[0]["code"] == "TooManyRequests"
    TCC_FAILURE_RESPONSE(response)

    pytest.skip("Too many requests")


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def _test_bad0(  # invalid server certificate
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with an invalid server certificate."""

    #
    # TEST 0: invalid server certificate
    parsed_url = urlparse(URL_CRED_V0)
    ip_address = socket.gethostbyname(parsed_url.hostname)  # type: ignore[arg-type]
    url = f"{parsed_url.scheme}://{ip_address}{parsed_url.path}"  # path[:1] == "/"

    # aiohttp.client_exceptions.ClientConnectorCertificateError:
    # Cannot connect to host 135.224.164.118:443 ssl:True
    # [SSLCertVerificationError: ... certificate is not valid for ...]

    with pytest.raises(aiohttp.ClientConnectorCertificateError):
        await client_session.post(url, headers=HEADERS_CRED_V0, data={})


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_bad1(  # bad credentials (client_id/secret)
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with bad credentials (client_id/secret)."""

    #
    # TEST 1: bad credentials (client_id/secret) -> HTTPStatus.UNAUTHORIZED
    data = {
        "applicationId": _APPLICATION_ID,
        "username": random.choice(string.ascii_letters),  # noqa: S311
        "password": "",
    }

    async with client_session.post(
        URL_CRED_V0, headers=HEADERS_CRED_V0, data=data
    ) as rsp:
        await _skip_if_too_many_requests(rsp)
        assert rsp.status == HTTPStatus.UNAUTHORIZED  # 401

        response: list[TccFailureResponseT] = await rsp.json()

        # the expected response for bad credentials
        """
            [{
                "code": "EmailOrPasswordIncorrect",
                "message": "The email or password provided is incorrect."
            }]
        """

    assert response[0]["code"] == "EmailOrPasswordIncorrect"
    TCC_FAILURE_RESPONSE(response)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_bad2(  # bad session id
    client_session: aiohttp.ClientSession,
) -> None:
    """Test authentication flow with an invalid/expired session id."""

    # pre-requisite data
    session_id = "bad session id " + random.choice(string.ascii_letters)  # noqa: S311

    #
    # TEST 9: bad session id -> HTTPStatus.UNAUTHORIZED
    url = f"{URL_BASE_V0}/accountInfo"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        await _skip_if_too_many_requests(rsp)
        assert rsp.status == HTTPStatus.UNAUTHORIZED  # 401

        response: list[TccFailureResponseT] = await rsp.json()

        # the expected response for expired session id
        """
            [{
                "code": "Unauthorized",
                "message": "Unauthorized"
            }]
        """

    assert response[0]["code"] == "Unauthorized"
    TCC_FAILURE_RESPONSE(response)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
@pytest.mark.skipif(not _DBG_TEST_CRED_URLS, reason="may invalidate credentials cache")
async def test_good(  # good credentials
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """Test authentication flow (and authorization) with good credentials."""

    #
    # TEST 1: good credentials (client_id/secret) -> HTTPStatus.OK
    data = {
        "applicationId": _APPLICATION_ID,
        "username": credentials[0],
        "password": credentials[1],
    }

    async with client_session.post(
        URL_CRED_V0, headers=HEADERS_CRED_V0, data=data
    ) as rsp:
        await _skip_if_too_many_requests(rsp)
        assert rsp.status == HTTPStatus.OK  # 200

        user_auth: TccSessionResponseT = await rsp.json()

        # the expected response
        """
            {
                "sessionId": "A80FF794-C042-42BC-A63E-7A509C9AA6C9",
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
                    "latestEulaAccepted": False
                }
            }
        """

    assert user_auth["userInfo"]["username"] == credentials[0]
    TCC_POST_USR_SESSION(user_auth)

    # #################################################################################

    # Check the session id by accessing a resource...
    session_id = user_auth["sessionId"]

    #
    # TEST 9: good session id -> HTTPStatus.OK
    url = f"{URL_BASE_V0}/accountInfo"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        await _skip_if_too_many_requests(rsp)
        assert rsp.status == HTTPStatus.OK  # 200

        user_info: TccUserAccountInfoResponseT = await rsp.json()

        # the expected response
        """
            [
                {
                    "locationID": 1234567,
                    "name": "My Home",
                    "streetAddress": "1 Main Street",
                    "city": "London",
                    "state": "",
                    "country": "GB",
                    "zipcode": "E1 1AA",
                    "type": "Residential",
                    "hasStation": true,
                    "devices": [{}],  # list of ?DeviceResponse
                    "oneTouchButtons": [],
                    "weather": {
                        "condition": "Cloudy",
                        "temperature": 13.0,
                        "units": "Celsius",
                        "humidity": 96,
                        "phrase": "Cloudy"
                    },
                    "daylightSavingTimeEnabled": true,
                    "timeZone": {
                        "id": "GMT Standard Time",
                        "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
                        "offsetMinutes": 0,
                        "currentOffsetMinutes": 0,
                        "usingDaylightSavingTime": true
                    },
                    "oneTouchActionsSuspended": false,
                    "isLocationOwner": true,
                    "locationOwnerID": 1234568,
                    "locationOwnerName": "David Smith",
                    "locationOwnerUserName": "username@email.com",
                    "canSearchForContractors": true,
                    "contractor": {
                        "info": {
                            "contractorID": 1839
                        },
                        "monitoring": {
                            "levelOfAccess": "Partial",
                            "contactPreferences": []
                        }
                    }
                }
            ]
        """

    assert user_auth["userInfo"]["username"] == credentials[0]
    TCC_GET_USR_INFO(user_info)
