#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the handling of vendor APIs (URLs)."""
from __future__ import annotations

from http import HTTPMethod, HTTPStatus

import pytest
import pytest_asyncio

import evohomeasync as evo
from evohomeasync.broker import URL_HOST

# FIXME: need v1 schemas
from evohomeasync2.schema import vol  # type: ignore[import-untyped]

from . import _DEBUG_USE_REAL_AIOHTTP, _DISABLE_STRICT_ASSERTS
from .helpers import (
    aiohttp,  # aiohttp may be mocked
    client_session as _client_session,
    user_credentials as _user_credentials,
)

URL_BASE = f"{URL_HOST}/WebAPI/api"


_global_user_data: dict | None = None


@pytest.fixture()
def user_credentials():
    return _user_credentials()


@pytest_asyncio.fixture
async def session():
    client_session = _client_session()
    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(autouse=True)
def patches_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("evohomeasync.client.aiohttp", aiohttp)


async def instantiate_client(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_user_data

    # refresh_token, access_token, access_token_expires = _global_user_data

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        user_data=_global_user_data,
    )

    # Authentication
    await client._populate_user_data()
    _global_user_data = client.user_data

    return client


async def should_work(  # type: ignore[no-any-unimported]
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    schema: vol.Schema | None = None,
) -> dict | list:
    """Make a request that is expected to succeed."""

    response: aiohttp.ClientResponse

    response = await client._do_request(method, f"{URL_BASE}/{url}", data=json)

    response.raise_for_status()

    assert True or response.content_type == content_type

    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

    if schema:
        return schema(content)
    return content


async def should_fail(
    client: evo.EvohomeClient,
    method: HTTPMethod,
    url: str,
    json: dict | None = None,
    content_type: str | None = "application/json",
    status: HTTPStatus | None = None,
) -> aiohttp.ClientResponse:
    """Make a request that is expected to fail."""

    response: aiohttp.ClientResponse

    response = await client._do_request(method, f"{URL_BASE}/{url}", data=json)

    try:
        response.raise_for_status()
    except aiohttp.ClientResponseError as exc:
        assert exc.status == status
    else:
        assert False, response.status

    if _DISABLE_STRICT_ASSERTS:
        return response

    assert True or response.content_type == content_type

    if response.content_type == "application/json":
        content = await response.json()
    else:
        content = await response.text()

    if isinstance(content, dict):
        assert True or "message" in content
    elif isinstance(content, list):
        assert True or "message" in content[0]

    return content


async def _test_url_locations(
    username: str, password: str, session: aiohttp.ClientSession | None = None
) -> None:
    client = await instantiate_client(username, password, session=session)

    client._headers["sessionId"] = client.user_data["sessionId"]
    user_id: int = client.user_data["userInfo"]["userID"]

    url = f"/locations?userId={user_id}&allData=True"
    _ = await should_work(client, HTTPMethod.GET, url)
    _ = await should_fail(
        client, HTTPMethod.PUT, url, status=HTTPStatus.METHOD_NOT_ALLOWED
    )

    url = f"/locations?userId={user_id}"
    _ = await should_work(client, HTTPMethod.GET, url)

    url = "/locations?userId=123456"
    _ = await should_fail(client, HTTPMethod.GET, url)

    url = "/locations?userId='123456'"
    _ = await should_fail(client, HTTPMethod.GET, url)

    url = "xxxxxxx"  # NOTE: is a general test, and not a test specific to this URL
    _ = await should_fail(
        client,
        HTTPMethod.GET,
        url,
        status=HTTPStatus.NOT_FOUND,
        content_type="text/html",  # exception to usual content-type
    )


async def _test_client_apis(
    username: str,
    password: str,
    session: aiohttp.ClientSession | None = None,
):
    """Instantiate a client, and logon to the vendor API."""

    global _global_user_data

    # Instantiation, NOTE: No API calls invoked during instantiation
    client = evo.EvohomeClient(
        username,
        password,
        session=session,
        user_data=_global_user_data,
    )

    user_data = await client._populate_user_data()
    assert user_data  # aka client.user_data

    _global_user_data = client.user_data

    await client._populate_full_data()
    assert client.full_data

    temps = await client.temperatures()
    assert temps


@pytest.mark.asyncio
async def _test_locations(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test /locations"""

    if not _DEBUG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented")

    try:
        await _test_url_locations(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        pytest.skip("Unable to authenticate")


@pytest.mark.asyncio
async def test_client_apis(
    user_credentials: tuple[str, str], session: aiohttp.ClientSession
) -> None:
    """Test _populate_user_data() & _populate_full_data()"""

    if not _DEBUG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented")

    try:
        await _test_client_apis(*user_credentials, session=session)
    except evo.AuthenticationFailed:
        pytest.skip("Unable to authenticate")


USER_DATA = {
    "sessionId": "BE5F40A6-1234-1234-1234-A708947D638B",
    "userInfo": {
        "userID": 2263181,
        "username": "null@gmail.com",
        "firstname": "David",
        "lastname": "Smith",
        "streetAddress": "1 Main Street",
        "city": "London",
        "zipcode": "NW1 1AA",
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
}

FULL_DATA = {
    "locationID": 2738909,
    "name": "My Home",
    "streetAddress": "1 Main Street",
    "city": "London",
    "state": "",
    "country": "GB",
    "zipcode": "NW1 1AA",
    "type": "Residential",
    "hasStation": True,
    "devices": [
        {
            "gatewayId": 2499896,
            "deviceID": 3933910,
            "thermostatModelType": "DOMESTIC_HOT_WATER",
            "deviceType": 128,
            "name": "",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 22.77,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["DHWOn", "DHWOff"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 30.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {"mode": "DHWOff", "status": "Scheduled"},
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3933910,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 250,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432579,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Bathroom Dn",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.79,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432579,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 4,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3449740,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Bathroom Up",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.26,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 19.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3449740,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 7,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432521,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Dead Zone",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 5.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432521,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 0,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333958,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Eh",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333958,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 11,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432577,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Front Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 19.83,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 20.5, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432577,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 2,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3449703,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Kids Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 19.53,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3449703,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 6,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432578,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Kitchen",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.43,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432578,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 3,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432580,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Main Bedroom",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.72,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432580,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 5,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3432576,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Main Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 20.14,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 15.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3432576,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 1,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 3450733,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Spare Room",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 18.81,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "Measured",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 16.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 3450733,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 8,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333957,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "UFH",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333957,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 10,
        },
        {
            "gatewayId": 2499896,
            "deviceID": 5333955,
            "thermostatModelType": "EMEA_ZONE",
            "deviceType": 128,
            "name": "Zv",
            "scheduleCapable": False,
            "holdUntilCapable": False,
            "thermostat": {
                "units": "Celsius",
                "indoorTemperature": 128.0,
                "outdoorTemperature": 128.0,
                "outdoorTemperatureAvailable": False,
                "outdoorHumidity": 128.0,
                "outdootHumidityAvailable": False,
                "indoorHumidity": 128.0,
                "indoorTemperatureStatus": "NotAvailable",
                "indoorHumidityStatus": "NotAvailable",
                "outdoorTemperatureStatus": "NotAvailable",
                "outdoorHumidityStatus": "NotAvailable",
                "isCommercial": False,
                "allowedModes": ["Heat", "Off"],
                "deadband": 0.0,
                "minHeatSetpoint": 5.0,
                "maxHeatSetpoint": 35.0,
                "minCoolSetpoint": 50.0,
                "maxCoolSetpoint": 90.0,
                "changeableValues": {
                    "mode": "Off",
                    "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
                    "vacationHoldDays": 0,
                },
                "scheduleCapable": False,
                "vacationHoldChangeable": False,
                "vacationHoldCancelable": False,
                "scheduleHeatSp": 0.0,
                "scheduleCoolSp": 0.0,
            },
            "alertSettings": {
                "deviceID": 5333955,
                "tempHigherThanActive": True,
                "tempHigherThan": 30.0,
                "tempHigherThanMinutes": 0,
                "tempLowerThanActive": True,
                "tempLowerThan": 5.0,
                "tempLowerThanMinutes": 0,
                "faultConditionExistsActive": False,
                "faultConditionExistsHours": 0,
                "normalConditionsActive": True,
                "communicationLostActive": False,
                "communicationLostHours": 0,
                "communicationFailureActive": True,
                "communicationFailureMinutes": 15,
                "deviceLostActive": False,
                "deviceLostHours": 0,
            },
            "isUpgrading": False,
            "isAlive": True,
            "thermostatVersion": "02.00.19.33",
            "macID": "00D02DEE4E56",
            "locationID": 2738909,
            "domainID": 20054,
            "instance": 9,
        },
    ],
    "oneTouchButtons": [],
    "weather": {
        "condition": "NightClear",
        "temperature": 9.0,
        "units": "Celsius",
        "humidity": 87,
        "phrase": "Clear",
    },
    "daylightSavingTimeEnabled": True,
    "timeZone": {
        "id": "GMT Standard Time",
        "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
        "offsetMinutes": 0,
        "currentOffsetMinutes": 0,
        "usingDaylightSavingTime": True,
    },
    "oneTouchActionsSuspended": False,
    "isLocationOwner": True,
    "locationOwnerID": 2263181,
    "locationOwnerName": "David Smith",
    "locationOwnerUserName": "null@gmail.com",
    "canSearchForContractors": True,
    "contractor": {
        "info": {"contractorID": 1839},
        "monitoring": {"levelOfAccess": "Partial", "contactPreferences": []},
    },
}
