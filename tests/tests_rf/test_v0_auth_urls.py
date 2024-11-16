#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs).

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
from evohomeasync.schema import SCH_LOCATION_RESPONSE, SCH_USER_ACCOUNT_RESPONSE

from ..const import URL_AUTH_V0 as URL_AUTH, URL_BASE_V0 as URL_BASE
from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    import aiohttp

    from evohomeasync.schema import ErrorResponse


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


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_url_auth_bad1(  # invalid/unknown credentials
    client_session: aiohttp.ClientSession,
) -> None:
    """Test the authentication flow with bad credentials."""

    # invalid credentials -> HTTPStatus.UNAUTHORIZED
    data = {
        "applicationId": _APPLICATION_ID,
        "username": random.choice(string.ascii_letters),  # noqa: S311
        "password": "",
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        assert rsp.status == HTTPStatus.UNAUTHORIZED

        response: list[ErrorResponse] = await rsp.json()

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
    user_id = 1234567

    # invalid/expired session id -> HTTPStatus.UNAUTHORIZED
    url = URL_BASE + f"locations?userId={user_id}&allData=True"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        assert rsp.status == HTTPStatus.UNAUTHORIZED

        response: list[ErrorResponse] = await rsp.json()

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

    # valid credentials -> HTTPStatus.OK
    data = {
        "applicationId": _APPLICATION_ID,
        "username": credentials[0],
        "password": credentials[1],
    }

    async with client_session.post(URL_AUTH, headers=HEADERS_AUTH, data=data) as rsp:
        assert rsp.status in [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]

        user_auth: dict | list = await rsp.json()

        """
            [{
                "code": "TooManyRequests",
                "message": "Request count limitation exceeded, please try again later."
            }]
        """

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert isinstance(user_auth, list)  # mypy hint
            assert user_auth[0]["code"] == "TooManyRequests"
            assert user_auth[0]["message"] and isinstance(user_auth[0]["message"], str)
            pytest.skip("Too many requests")

        assert isinstance(user_auth, dict)  # mypy hint

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

    assert user_auth["sessionId"] and isinstance(user_auth["sessionId"], str)
    assert user_auth["userInfo"]["username"] == credentials[0]

    assert SCH_USER_ACCOUNT_RESPONSE(user_auth["userInfo"]), user_auth["userInfo"]

    # #################################################################################

    # Check the session id by accessing a resource...
    session_id = user_auth["sessionId"]
    user_id = user_auth["userInfo"]["userID"]

    # valid session id -> HTTPStatus.OK
    url = URL_BASE + f"locations?userId={user_id}&allData=True"
    headers = HEADERS_BASE | {"sessionId": session_id}

    async with client_session.get(url, headers=headers) as rsp:
        assert rsp.status in [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]

        response: list = await rsp.json()

        if rsp.status == HTTPStatus.TOO_MANY_REQUESTS:
            assert response[0]["code"] == "TooManyRequests"
            assert response[0]["message"] and isinstance(response[0]["message"], str)
            pytest.skip("Too many requests")

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

    assert response[0]["locationID"] and isinstance(response[0]["locationID"], int)
    assert response[0]["devices"] and isinstance(response[0]["devices"], list)

    assert SCH_LOCATION_RESPONSE(response[0]), response[0]
