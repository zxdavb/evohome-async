#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs) for Authentication.

This is used to:
  a) document the RESTful API that is provided by the vendor
  b) confirm the faked server is behaving as per a)

Testing is at HTTP request layer (e.g. GET).
Everything to/from the RESTful API is in camelCase (so those schemas are used).
"""

from __future__ import annotations

import random
import string
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohomeasync.auth import _APPLICATION_ID
from evohomeasync.schemas import (
    SCH_USER_ACCOUNT_INFO_RESPONSE,
    SCH_USER_SESSION_RESPONSE,
)

from ..const import (
    _DBG_USE_REAL_AIOHTTP,
    URL_AUTH_V0 as URL_AUTH,
    URL_BASE_V0 as URL_BASE,
)

if TYPE_CHECKING:
    import aiohttp

    from evohomeasync.schemas import TccErrorResponseT


HEADERS_AUTH = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",  # data=
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
    # _APPLICATION_ID is in the data
}
HEADERS_BASE = {
    "Accept": "application/json",
    "Content-Type": "application/json",  # json=
    "SessionId": None,  # "e163b069-1234-..."
}


async def handle_too_many_requests(rsp: aiohttp.ClientResponse) -> None:
    assert rsp.status == HTTPStatus.TOO_MANY_REQUESTS

    response: list[TccErrorResponseT] = await rsp.json()

    # the expected response for TOO_MANY_REQUESTS
    """
        [{
            "code": "TooManyRequests",
            "message": "Request count limitation exceeded, please try again later."
        }]
    """

    assert response[0]["code"] == "TooManyRequests"
    assert response[0]["message"] and isinstance(response[0]["message"], str)

    pytest.skip("Too many requests")


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad1(  # invalid/unknown credentials
    client_session: aiohttp.ClientSession,
) -> None:
    """Test the authentication flow with bad credentials."""

    #
    # TEST 1: invalid credentials -> HTTPStatus.UNAUTHORIZED
    data = {
        "applicationId": _APPLICATION_ID,
        "username": random.choice(string.ascii_letters),  # noqa: S311
        "password": "",
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        response: list[TccErrorResponseT] = await rsp.json()

        assert rsp.status == HTTPStatus.UNAUTHORIZED

        # the expected response for bad credentials
        """
            [{
                "code": "EmailOrPasswordIncorrect",
                "message": "The email or password provided is incorrect."
            }]
        """

    assert response[0]["code"] == "EmailOrPasswordIncorrect"
    assert response[0]["message"] and isinstance(response[0]["message"], str)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad2(  # invalid/expired session id
    client_session: aiohttp.ClientSession,
) -> None:
    """Test the authentication flow with an invalid session id,"""

    # pre-requisite data
    session_id = "bad/expired session id " + random.choice(string.ascii_letters)  # noqa: S311

    #
    # TEST 2: invalid/expired session id -> HTTPStatus.UNAUTHORIZED
    url = URL_BASE + "accountInfo"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        assert rsp.status == HTTPStatus.UNAUTHORIZED

        response: list[TccErrorResponseT] = await rsp.json()

        # the expected response for expired session id
        """
            [{
                "code": "Unauthorized",
                "message": "Unauthorized"
            }]
        """

    assert response[0]["code"] == "Unauthorized"
    assert response[0]["message"] and isinstance(response[0]["message"], str)


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_good(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> None:
    """Test the authentication flow (and authorization) with good credentials."""

    # TEST 1: valid credentials -> HTTPStatus.OK
    data = {
        "applicationId": _APPLICATION_ID,
        "username": credentials[0],
        "password": credentials[1],
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.OK

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

        user_auth: dict = await rsp.json()

    assert SCH_USER_SESSION_RESPONSE(user_auth), user_auth
    assert user_auth["userInfo"]["username"] == credentials[0]

    #
    # Check the session id by accessing a resource...
    session_id = user_auth["sessionId"]

    # TEST 2: valid session id -> HTTPStatus.OK
    url = URL_BASE + "accountInfo"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            await handle_too_many_requests(rsp)

        assert rsp.status == HTTPStatus.OK

        user_info: dict = await rsp.json()

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

    assert SCH_USER_ACCOUNT_INFO_RESPONSE(user_info), user_info
