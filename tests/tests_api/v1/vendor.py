"""The vendor's v1 API: its endpoints, its conventions, and recorded responses.

The base URL is https://tccna.resideo.com/WebAPI/api (URL_BASE_V1), and all the
endpoints below are relative to it (the session's too). Its certificate is for the
hostname only (so not valid for its IP address).

  Entity    Method    Endpoint                                                   Tests
  --------  --------  ---------------------------------------------------------  ---------------
  session   POST      /session                                                   test_auth
  user      GET       /accountInfo                                               test_get
  location  GET       /locations?userId={usr_id}&allData=True                    test_get
            GET       /locations?locationId={loc_id}&allData=True                test_get_device
  gateway   GET       /gateways?locationId={loc_id}[&allData=True]               test_get_device
  device    GET       /devices?locationId={loc_id}[&allData=True]                test_get_device
            GET       /devices/{dev_id}                                          test_get_device
            GET       /devices/{dev_id}/thermostat                               test_get_device
            GET, PUT  /devices/{dev_id}/thermostat/changeableValues              test_get_device,
                                                                                 test_dhw_put,
                                                                                 test_zone_put
            PUT       /devices/{zon_id}/thermostat/changeableValues/heatSetpoint test_zone_put
  TCS       PUT       /evoTouchSystems?locationId={loc_id}  (removed: a 404)     test_tcs_put
  task      GET       /commTasks?commTaskId={tsk_id}                             test_comm_task

Zones and DHW are both devices, distinguished by thermostatModelType (e.g. EMEA_ZONE,
or DOMESTIC_HOT_WATER), and so share the same URLs, except that only a zone has
.../heatSetpoint (a shortcut to the heatSetpoint of its changeableValues). There is no
longer any v1 URL to change a TCS's mode (the vendor removed evoTouchSystems).

The API is regular:
- allData=True adds an entity's children: a location's devices and oneTouchButtons
  (and its weather, and contractor, if it has them), a gateway's devices, and a
  device's thermostat and alertSettings
- an entity's own URL returns the same object as is nested within its parent's (but
  locations?locationId= returns a dict, not a list of one), except that a device's
  thermostat excludes its changeableValues, and that a GET of changeableValues adds the
  source of each change (e.g. {"modeChangeSource": {"partnerName": "EMEA", "changeTag":
  ""}}, and heatSetpointChangeSource for a zone), which is absent for a lost device
- a GET is 200 (OK), and a PUT is 201 (Created), with the id of a comm task (an int,
  unlike the v2 API's str)
- the response's keys are camelCase, but its ids are cased inconsistently: userID,
  locationID, deviceID, and gatewayID (of a gateway), but gatewayId (of a device), and
  locationId (of a gateway); the ids are ints; and one key is misspelt by the vendor:
  outdootHumidityAvailable
- the path & query keys of a URL, and the keys & enum values of a request, are
  case-insensitive (the older, non-async client sent PascalCase keys, e.g. "Status",
  and this library camelCase, e.g. "status")
- its datetimes are the location's local time, not UTC: a nextTime is returned without
  a Z, and the Z of one that is sent is ignored

And its errors are regular:
- a failed request is answered with a list of errors, each with a code and a message,
  e.g. [{"code": "DeviceIsLost", "message": "Device is lost."}]
- an id that is not the user's is a 401 (Unauthorized); an id that is not numeric is a
  400; a bad session id is a 401 too: [{"code": "Unauthorized", "message":
  "Unauthorized"}] (without the full stop of the v2 API's)
- an unknown path is a 404 whose body is HTML, as is a GET of a PUT-only URL (not a
  405, unlike the v2 API), and a PUT of a GET-only URL (e.g. locations); a known path
  without its required query key (e.g. userId) is a 404 whose body is JSON:
    {"message": "No HTTP resource was found that matches the request URI '...'."}

The responses below are typed as the schema module's Tcc*T TypedDicts, so that mypy
checks this record against them (an enum value is given as its Tcc* StrEnum, which is
the same on the wire). Their ids, names and addresses are redacted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from evohomeasync.schemas import (
    TccDhwMode,
    TccLocationType,
    TccSensorStatus,
    TccSetpointStatus,
    TccThermostatMode,
    TccThermostatModelType,
    _DhwIdT,
    _GatewayIdT,
    _LocationIdT,
    _UserIdT,
    _ZoneIdT,
)

if TYPE_CHECKING:
    from evohomeasync.schemas import (
        TccLocationResponseT,
        TccSessionResponseT,
        TccUserAccountInfoResponseT,
    )


# the body of a 404 (Not Found) of an unknown path: it is HTML (from IIS), not JSON
# provenance: the old tests_rf (its comments), abridged
HTML_NOT_FOUND: Final = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" ...>'
    "<html><head><title>404 - File or directory not found.</title></head>"
    "<body>...</body></html>"
)


# the ids of the (redacted) user and their entities (as are sent: ints)
USR_ID: Final = 2000001
LOC_ID: Final = 2000010
GWY_ID: Final = 2000020
ZON_ID: Final = 2000041  # the first zone: the one under test (is alive)
ZON_ID_2: Final = 2000042  # a lost zone (is not alive)
DHW_ID: Final = 2000050

# an id that is not the user's
NOT_THE_USERS_ID: Final = 123456


# POST /session (its sessionId is a GUID)
# provenance: the USER_DATA of the old tests_rf/test_v1_urls_auth.py, and the old
# tests_rf/test_v1_urls_cred.py (its comments) (redacted)
SESSION: Final[TccSessionResponseT] = {
    "sessionId": "BE5F40A6-1234-1234-1234-A708947D6399",
    "userInfo": {
        "userID": _UserIdT(USR_ID),
        "username": "username@email.com",
        "firstname": "John",
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
}


# GET /accountInfo
# provenance: tests/tests/fixtures_v1/default/user_info.json (its userInfo) (redacted)
USR_INFO: Final[TccUserAccountInfoResponseT] = {
    "userID": _UserIdT(USR_ID),
    "username": "username@email.com",
    "firstname": "John",
    "lastname": "Smith",
    "streetAddress": "1 Main Street",
    "city": "London",
    "zipcode": "E1 1AA",
    "country": "GB",
    "telephone": "",
    "userLanguage": "en-GB",
}


# GET /locations?userId={USR_ID}&allData=True
# provenance: tests/tests/fixtures_v1/default/user_locs.json (with its 9 zones cut to 2,
# and its alertSettings dropped), and the FULL_DATA of tests_rf/test_v1_urls_auth.py
# (for its contractor) (redacted)
USR_LOCS: Final[list[TccLocationResponseT]] = [
    {
        "locationID": _LocationIdT(LOC_ID),
        "name": "My Home",
        "streetAddress": "1 Main Street",
        "city": "London",
        "state": "",
        "country": "GB",
        "zipcode": "E1 1AA",
        "type": TccLocationType.RESIDENTIAL,
        "hasStation": True,
        "devices": [
            {
                "gatewayId": _GatewayIdT(GWY_ID),
                "deviceID": _DhwIdT(DHW_ID),
                "thermostatModelType": TccThermostatModelType.DOMESTIC_HOT_WATER,
                "deviceType": 128,
                "name": "",
                "scheduleCapable": False,
                "holdUntilCapable": False,
                "thermostat": {
                    "units": "Celsius",
                    "indoorTemperature": 38.91,
                    "outdoorTemperature": 128.0,
                    "outdoorTemperatureAvailable": False,
                    "outdoorHumidity": 128.0,
                    "outdootHumidityAvailable": False,
                    "indoorHumidity": 128.0,
                    "indoorTemperatureStatus": TccSensorStatus.MEASURED,
                    "indoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorTemperatureStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "isCommercial": False,
                    "allowedModes": [TccDhwMode.DHW_ON, TccDhwMode.DHW_OFF],
                    "deadband": 0.0,
                    "minHeatSetpoint": 5.0,
                    "maxHeatSetpoint": 30.0,
                    "minCoolSetpoint": 50.0,
                    "maxCoolSetpoint": 90.0,
                    "changeableValues": {
                        "mode": TccDhwMode.DHW_OFF,
                        "status": TccSetpointStatus.SCHEDULED,
                    },
                    "scheduleCapable": False,
                    "vacationHoldChangeable": False,
                    "vacationHoldCancelable": False,
                    "scheduleHeatSp": 0.0,
                    "scheduleCoolSp": 0.0,
                },
                "isUpgrading": False,
                "isAlive": True,
                "thermostatVersion": "02.00.19.33",
                "macID": "00D02DEE0000",
                "locationID": _LocationIdT(LOC_ID),
                "domainID": 20054,
                "instance": 250,
            },
            {
                "gatewayId": _GatewayIdT(GWY_ID),
                "deviceID": _ZoneIdT(ZON_ID),
                "thermostatModelType": TccThermostatModelType.EMEA_ZONE,
                "deviceType": 128,
                "name": "Main Room",
                "scheduleCapable": False,
                "holdUntilCapable": False,
                "thermostat": {
                    "units": "Celsius",
                    "indoorTemperature": 16.78,
                    "outdoorTemperature": 128.0,
                    "outdoorTemperatureAvailable": False,
                    "outdoorHumidity": 128.0,
                    "outdootHumidityAvailable": False,
                    "indoorHumidity": 128.0,
                    "indoorTemperatureStatus": TccSensorStatus.MEASURED,
                    "indoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorTemperatureStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "isCommercial": False,
                    "allowedModes": [TccThermostatMode.HEAT, TccThermostatMode.OFF],
                    "deadband": 0.0,
                    "minHeatSetpoint": 5.0,
                    "maxHeatSetpoint": 35.0,
                    "minCoolSetpoint": 50.0,
                    "maxCoolSetpoint": 90.0,
                    "changeableValues": {
                        "mode": TccThermostatMode.OFF,
                        "heatSetpoint": {
                            "value": 19.5,
                            "status": TccSetpointStatus.SCHEDULED,
                        },
                        "vacationHoldDays": 0,
                    },
                    "scheduleCapable": False,
                    "vacationHoldChangeable": False,
                    "vacationHoldCancelable": False,
                    "scheduleHeatSp": 0.0,
                    "scheduleCoolSp": 0.0,
                },
                "isUpgrading": False,
                "isAlive": True,
                "thermostatVersion": "02.00.19.33",
                "macID": "00D02DEE0000",
                "locationID": _LocationIdT(LOC_ID),
                "domainID": 20054,
                "instance": 1,
            },
            {
                "gatewayId": _GatewayIdT(GWY_ID),
                "deviceID": _ZoneIdT(ZON_ID_2),
                "thermostatModelType": TccThermostatModelType.EMEA_ZONE,
                "deviceType": 128,
                "name": "Front Room",
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
                    "indoorTemperatureStatus": TccSensorStatus.NOT_AVAILABLE,
                    "indoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorTemperatureStatus": TccSensorStatus.NOT_AVAILABLE,
                    "outdoorHumidityStatus": TccSensorStatus.NOT_AVAILABLE,
                    "isCommercial": False,
                    "allowedModes": [TccThermostatMode.HEAT, TccThermostatMode.OFF],
                    "deadband": 0.0,
                    "minHeatSetpoint": 5.0,
                    "maxHeatSetpoint": 35.0,
                    "minCoolSetpoint": 50.0,
                    "maxCoolSetpoint": 90.0,
                    "changeableValues": {
                        "mode": TccThermostatMode.OFF,
                        "heatSetpoint": {
                            "value": 21.5,
                            "status": TccSetpointStatus.TEMPORARY,
                            "nextTime": "2026-11-13T18:00:00",
                        },
                        "vacationHoldDays": 0,
                    },
                    "scheduleCapable": False,
                    "vacationHoldChangeable": False,
                    "vacationHoldCancelable": False,
                    "scheduleHeatSp": 0.0,
                    "scheduleCoolSp": 0.0,
                },
                "isUpgrading": False,
                "isAlive": False,
                "thermostatVersion": "02.00.19.33",
                "macID": "00D02DEE0000",
                "locationID": _LocationIdT(LOC_ID),
                "domainID": 20054,
                "instance": 2,
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
        "locationOwnerID": USR_ID,
        "locationOwnerName": "John Smith",
        "locationOwnerUserName": "username@email.com",
        "canSearchForContractors": True,
        "contractor": {
            "info": {"contractorID": 1839},
            "monitoring": {"levelOfAccess": "Partial", "contactPreferences": []},
        },
    }
]
