"""The vendor's v2 API: its endpoints, its conventions, and recorded responses.

The base URL is https://tccna.resideo.com/WebAPI/emea/api/v1 (URL_BASE_V2), and all
the endpoints below are relative to it, except the token's, which is off the host:
https://tccna.resideo.com/Auth/OAuth/Token (URL_CRED_V2). Both certificates are for
the hostname only (so not valid for its IP address).

  Entity    Method    Endpoint                                                       Tests
  --------  --------  -------------------------------------------------------------  ---------------
  token     POST      /Auth/OAuth/Token  (off the base URL)                          test_auth
  user      GET       /userAccount                                                   test_get
  location  GET       /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
                                                                                     test_get
            GET       /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True
                                                                                     test_get_entity
            GET       /location/{loc_id}/status?includeTemperatureControlSystems=True
                                                                                     test_get
  gateway   GET       /gateway/{gwy_id}/installationInfo?includeTemperatureControlSystems=True
                                                                                     test_get_entity
            GET       /gateway/{gwy_id}/status?includeTemperatureControlSystems=True test_get_entity
  TCS       GET       /temperatureControlSystem/{tcs_id}/installationInfo            test_get_entity
            GET       /temperatureControlSystem/{tcs_id}/status                      test_get_entity
            PUT       /temperatureControlSystem/{tcs_id}/mode                        test_tcs_put
  zone      GET       /temperatureZone/{zon_id}/installationInfo                     test_get_entity
            GET       /temperatureZone/{zon_id}/status                               test_get_entity
            PUT       /temperatureZone/{zon_id}/heatSetpoint                         test_zone_put
            GET, PUT  /temperatureZone/{zon_id}/schedule                             test_schedule
  DHW       GET       /domesticHotWater/{dhw_id}/installationInfo                    test_get_entity
            GET       /domesticHotWater/{dhw_id}/status                              test_get_entity
            PUT       /domesticHotWater/{dhw_id}/state                               test_dhw_put
            GET, PUT  /domesticHotWater/{dhw_id}/schedule                            test_schedule
  task      GET       /commTasks?commTaskId={tsk_id}                                 test_comm_task

The API is regular:
- every entity has an installationInfo endpoint (its config) and a status endpoint (its
  state); those of a TCS always include those of its zones (and DHW), but those of a
  location or gateway include those of its TCSs if (and only if)
  includeTemperatureControlSystems=True
- each entity's installationInfo (or status) is the same object as is nested within that
  of its parent (e.g. a TCS's is as found within its gateway's)
- a GET is 200 (OK), and a PUT is 201 (Created), with the id of a comm task
- the response's keys are camelCase, but the path & query keys of a URL, and the keys &
  enum values of a request, are case-insensitive (but not snake_case: e.g. the enum
  value "permanentoverride" is accepted, "permanent_override" is not)

And its errors are regular:
- a failed request is answered with a list of errors, each with a code and a message
  (and sometimes a parameterName), e.g.:
    [{"code": "Unauthorized", "message": "You are not allowed to perform this action."}]
- an id that is not the user's (whether or not it exists, e.g. a deleted zone's) is a
  401 (Unauthorized), for every URL, GET or PUT; an id that is the user's, but of
  another type of entity, is a 400 (e.g. DHWNotFound); an id that is not numeric is a
  400 (InvalidInput, "Request was bad formatted or cannot find required ID parameter in
  the URL.")
- a bad (or expired) access token is a 401 too, but with a different message:
    [{"code": "Unauthorized", "message": "Unauthorized."}]
- an unknown path is a 404 whose body is HTML, not JSON; a known path without its
  required query key (e.g. userId) is a 404 whose body is JSON:
    {"message": "No HTTP resource was found that matches the request URI '...'."}
- a GET of a PUT-only URL is a 405 (Method Not Allowed), whose body is JSON:
    {"message": "The requested resource does not support http method 'GET'."}
  except for a zone's heatSetpoint, which is a 404 (HTML), as if it does not exist

The responses below are typed as the schema modules' Tcc*T TypedDicts, so that mypy
checks this record against them (an enum value is given as its Tcc* StrEnum, which is
the same on the wire). Their ids, names and addresses are redacted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from evohomeasync2.schemas.const import (
    TccDayOfWeek,
    TccDhwState,
    TccFaultType,
    TccLocationType,
    TccSystemMode,
    TccTcsModelType,
    TccTimingMode,
    TccZoneMode,
    TccZoneModelType,
    TccZoneType,
)

if TYPE_CHECKING:
    from evohomeasync2.schemas.account import (
        TccOAuthTokenResponseT,
        TccUsrAccountResponseT,
    )
    from evohomeasync2.schemas.config import TccLocConfigResponseT
    from evohomeasync2.schemas.schedule import (
        TccDhwDailySchedulesT,
        TccZonDailySchedulesT,
    )
    from evohomeasync2.schemas.status import TccLocStatusResponseT


# the body of a 404 (Not Found) of an unknown path: it is HTML (from IIS), not JSON
# provenance: the old tests_rf (its comments), abridged
HTML_NOT_FOUND: Final = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" ...>'
    "<html><head><title>404 - File or directory not found.</title></head>"
    "<body>...</body></html>"
)


# the ids of the (redacted) user and their entities
USR_ID: Final = "2000001"
LOC_ID: Final = "2000010"
GWY_ID: Final = "2000020"
TCS_ID: Final = "2000030"
ZON_ID: Final = "2000041"  # the first zone: the one under test
ZON_ID_2: Final = "2000042"
DHW_ID: Final = "2000050"

# an id that is not the user's (the vendor does not say if it exists: either is a 401)
NOT_THE_USERS_ID: Final = "1234567"


# GET /userAccount
# provenance: tests/tests/fixtures_v2/default/user_account.json (redacted)
USR_ACCOUNT: Final[TccUsrAccountResponseT] = {
    "userId": USR_ID,
    "username": "username@email.com",
    "firstname": "John",
    "lastname": "Smith",
    "streetAddress": "1 Main Street",
    "city": "London",
    "postcode": "E1 1AA",
    "country": "UnitedKingdom",
    "language": "enGB",
}


# GET /location/installationInfo?userId={USR_ID}&includeTemperatureControlSystems=True
# provenance: tests_rf/faked_server/const.py (MOCK_FULL_CONFIG, of the test system, with
# its 9 zones cut to 2), and tests/tests/fixtures_v2/default (for its DHW) (redacted)
USR_LOCATIONS: Final[list[TccLocConfigResponseT]] = [
    {
        "locationInfo": {
            "locationId": LOC_ID,
            "name": "My Home",
            "streetAddress": "1 Main Street",
            "city": "London",
            "country": "UnitedKingdom",
            "postcode": "E1 1AA",
            "locationType": TccLocationType.RESIDENTIAL,
            "useDaylightSaveSwitching": True,
            "timeZone": {
                "timeZoneId": "GMTStandardTime",
                "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
                "offsetMinutes": 0,
                "currentOffsetMinutes": 0,
                "supportsDaylightSaving": True,
            },
            "locationOwner": {
                "userId": USR_ID,
                "username": "username@email.com",
                "firstname": "John",
                "lastname": "Smith",
            },
        },
        "gateways": [
            {
                "gatewayInfo": {
                    "gatewayId": GWY_ID,
                    "mac": "00D02DEE0000",
                    "crc": "0000",
                    "isWiFi": False,
                },
                "temperatureControlSystems": [
                    {
                        "systemId": TCS_ID,
                        "modelType": TccTcsModelType.EVO_TOUCH,
                        "zones": [
                            {
                                "zoneId": ZON_ID,
                                "modelType": TccZoneModelType.HEATING_ZONE,
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        TccZoneMode.PERMANENT_OVERRIDE,
                                        TccZoneMode.FOLLOW_SCHEDULE,
                                        TccZoneMode.TEMPORARY_OVERRIDE,
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Main Room",
                                "zoneType": TccZoneType.RADIATOR_ZONE,
                            },
                            {
                                "zoneId": ZON_ID_2,
                                "modelType": TccZoneModelType.HEATING_ZONE,
                                "setpointCapabilities": {
                                    "maxHeatSetpoint": 35.0,
                                    "minHeatSetpoint": 5.0,
                                    "valueResolution": 0.5,
                                    "canControlHeat": True,
                                    "canControlCool": False,
                                    "allowedSetpointModes": [
                                        TccZoneMode.PERMANENT_OVERRIDE,
                                        TccZoneMode.FOLLOW_SCHEDULE,
                                        TccZoneMode.TEMPORARY_OVERRIDE,
                                    ],
                                    "maxDuration": "1.00:00:00",
                                    "timingResolution": "00:10:00",
                                },
                                "scheduleCapabilities": {
                                    "maxSwitchpointsPerDay": 6,
                                    "minSwitchpointsPerDay": 1,
                                    "timingResolution": "00:10:00",
                                    "setpointValueResolution": 0.5,
                                },
                                "name": "Front Room",
                                "zoneType": TccZoneType.RADIATOR_ZONE,
                            },
                        ],
                        "dhw": {
                            "dhwId": DHW_ID,
                            "dhwStateCapabilitiesResponse": {
                                "allowedStates": [TccDhwState.ON, TccDhwState.OFF],
                                "allowedModes": [
                                    TccZoneMode.FOLLOW_SCHEDULE,
                                    TccZoneMode.PERMANENT_OVERRIDE,
                                    TccZoneMode.TEMPORARY_OVERRIDE,
                                ],
                                "maxDuration": "1.00:00:00",
                                "timingResolution": "00:10:00",
                            },
                            "scheduleCapabilitiesResponse": {
                                "maxSwitchpointsPerDay": 6,
                                "minSwitchpointsPerDay": 1,
                                "timingResolution": "00:10:00",
                            },
                        },
                        "allowedSystemModes": [
                            {
                                "systemMode": TccSystemMode.AUTO,
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": TccSystemMode.AUTO_WITH_ECO,
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "1.00:00:00",
                                "timingResolution": "01:00:00",
                                "timingMode": TccTimingMode.DURATION,
                            },
                            {
                                "systemMode": TccSystemMode.AUTO_WITH_RESET,
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": TccSystemMode.AWAY,
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": TccTimingMode.PERIOD,
                            },
                            {
                                "systemMode": TccSystemMode.DAY_OFF,
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": TccTimingMode.PERIOD,
                            },
                            {
                                "systemMode": TccSystemMode.HEATING_OFF,
                                "canBePermanent": True,
                                "canBeTemporary": False,
                            },
                            {
                                "systemMode": TccSystemMode.CUSTOM,
                                "canBePermanent": True,
                                "canBeTemporary": True,
                                "maxDuration": "99.00:00:00",
                                "timingResolution": "1.00:00:00",
                                "timingMode": TccTimingMode.PERIOD,
                            },
                        ],
                    }
                ],
            }
        ],
    }
]


# GET /location/{LOC_ID}/status?includeTemperatureControlSystems=True
# provenance: tests_rf/faked_server/const.py (MOCK_LOCN_STATUS, with its 9 zones cut to
# 2), and tests/tests/fixtures_v2/default/status_2738909.json (for its DHW) (redacted)
LOC_STATUS: Final[TccLocStatusResponseT] = {
    "locationId": LOC_ID,
    "gateways": [
        {
            "gatewayId": GWY_ID,
            "temperatureControlSystems": [
                {
                    "systemId": TCS_ID,
                    "zones": [
                        {
                            "zoneId": ZON_ID,
                            "temperatureStatus": {
                                "temperature": 19.5,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 17.0,
                                "setpointMode": TccZoneMode.FOLLOW_SCHEDULE,
                            },
                            "name": "Main Room",
                        },
                        {
                            "zoneId": ZON_ID_2,
                            "temperatureStatus": {"isAvailable": False},
                            "activeFaults": [
                                {
                                    "faultType": TccFaultType.ZON_S_CL,
                                    "since": "2023-10-09T01:45:04",
                                }
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 21.5,
                                "setpointMode": TccZoneMode.TEMPORARY_OVERRIDE,
                                "until": "2026-11-13T18:00:00Z",
                            },
                            "name": "Front Room",
                        },
                    ],
                    "dhw": {
                        "dhwId": DHW_ID,
                        "temperatureStatus": {"temperature": 55.0, "isAvailable": True},
                        "stateStatus": {
                            "state": TccDhwState.OFF,
                            "mode": TccZoneMode.FOLLOW_SCHEDULE,
                        },
                        "activeFaults": [],
                    },
                    "activeFaults": [],
                    "systemModeStatus": {
                        "mode": TccSystemMode.AUTO,
                        "isPermanent": True,
                    },
                }
            ],
            "activeFaults": [],
        }
    ],
}


# GET /location/{LOC_ID}/status?includeTemperatureControlSystems=True (another time)
# provenance: as LOC_STATUS, but with each entity overridden (the TCS until midnight, a
# zone permanently, the DHW temporarily), and a gateway fault as seen by the old
# tests_rf/test_v2_urls.py (its since is fractional and TZ-naive) (redacted)
LOC_STATUS_OVERRIDDEN: Final[TccLocStatusResponseT] = {
    "locationId": LOC_ID,
    "gateways": [
        {
            "gatewayId": GWY_ID,
            "temperatureControlSystems": [
                {
                    "systemId": TCS_ID,
                    "zones": [
                        {
                            "zoneId": ZON_ID,
                            "temperatureStatus": {
                                "temperature": 20.5,
                                "isAvailable": True,
                            },
                            "activeFaults": [],
                            "setpointStatus": {
                                "targetHeatTemperature": 21.0,
                                "setpointMode": TccZoneMode.PERMANENT_OVERRIDE,
                            },
                            "name": "Main Room",
                        },
                        {
                            "zoneId": ZON_ID_2,
                            "temperatureStatus": {"isAvailable": False},
                            "activeFaults": [
                                {
                                    "faultType": TccFaultType.ZON_S_CL,
                                    "since": "2023-10-09T01:45:04",
                                }
                            ],
                            "setpointStatus": {
                                "targetHeatTemperature": 17.0,
                                "setpointMode": TccZoneMode.FOLLOW_SCHEDULE,
                            },
                            "name": "Front Room",
                        },
                    ],
                    "dhw": {
                        "dhwId": DHW_ID,
                        "temperatureStatus": {"temperature": 55.0, "isAvailable": True},
                        "stateStatus": {
                            "state": TccDhwState.ON,
                            "mode": TccZoneMode.TEMPORARY_OVERRIDE,
                            "until": "2026-11-13T18:00:00Z",
                        },
                        "activeFaults": [],
                    },
                    "activeFaults": [],
                    "systemModeStatus": {
                        "mode": TccSystemMode.AWAY,
                        "isPermanent": False,
                        "timeUntil": "2026-11-15T00:00:00Z",
                    },
                }
            ],
            "activeFaults": [
                {
                    "faultType": TccFaultType.GWY_X_CL,
                    "since": "2025-02-23T22:34:25.04",
                }
            ],
        }
    ],
}


# The installationInfo (and status) of each entity is the same object as is nested
# within that of its parent: so these are taken from the location's (see above)

# GET /location/{LOC_ID}/installationInfo?includeTemperatureControlSystems=True
LOC_CONFIG: Final = USR_LOCATIONS[0]

# GET /gateway/{GWY_ID}/installationInfo?includeTemperatureControlSystems=True
GWY_CONFIG: Final = LOC_CONFIG["gateways"][0]

# GET /gateway/{GWY_ID}/status?includeTemperatureControlSystems=True
GWY_STATUS: Final = LOC_STATUS["gateways"][0]

# GET /temperatureControlSystem/{TCS_ID}/installationInfo (it always has its zones)
TCS_CONFIG: Final = GWY_CONFIG["temperatureControlSystems"][0]

# GET /temperatureControlSystem/{TCS_ID}/status (it always has its zones)
TCS_STATUS: Final = GWY_STATUS["temperatureControlSystems"][0]

# GET /temperatureZone/{ZON_ID}/installationInfo
ZON_CONFIG: Final = TCS_CONFIG["zones"][0]

# GET /temperatureZone/{ZON_ID}/status
ZON_STATUS: Final = TCS_STATUS["zones"][0]

# GET /domesticHotWater/{DHW_ID}/installationInfo
DHW_CONFIG: Final = TCS_CONFIG["dhw"]

# GET /domesticHotWater/{DHW_ID}/status
DHW_STATUS: Final = TCS_STATUS["dhw"]


# Without includeTemperatureControlSystems=True, a location's (or a gateway's)
# installationInfo and status omit its TCSs (there is no TypedDict for these)
# provenance: the old tests_rf/test_v2_urls.py (which asserted their keys)

# GET /gateway/{GWY_ID}/installationInfo (its only key is gatewayInfo)
GWY_CONFIG_SANS_TCSS: Final[dict[str, object]] = {
    "gatewayInfo": GWY_CONFIG["gatewayInfo"],
}

# GET /gateway/{GWY_ID}/status (its only keys are gatewayId and activeFaults)
GWY_STATUS_SANS_TCSS: Final[dict[str, object]] = {
    "gatewayId": GWY_ID,
    "activeFaults": [],
}

# GET /location/{LOC_ID}/installationInfo
LOC_CONFIG_SANS_TCSS: Final[dict[str, object]] = {
    "locationInfo": LOC_CONFIG["locationInfo"],
    "gateways": [GWY_CONFIG_SANS_TCSS],
}

# GET /location/{LOC_ID}/status
LOC_STATUS_SANS_TCSS: Final[dict[str, object]] = {
    "locationId": LOC_ID,
    "gateways": [GWY_STATUS_SANS_TCSS],
}


# GET /temperatureZone/{ZON_ID}/schedule
# provenance: tests_rf/faked_server/const.py (MOCK_SCHEDULE_ZONE)
ZON_SCHEDULE: Final[TccZonDailySchedulesT] = {
    "dailySchedules": [
        {
            "dayOfWeek": TccDayOfWeek.MONDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.TUESDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.WEDNESDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.THURSDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.FRIDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "06:30:00"},
                {"heatSetpoint": 18.0, "timeOfDay": "08:00:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "17:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.SATURDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "07:30:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "11:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.SUNDAY,
            "switchpoints": [
                {"heatSetpoint": 19.0, "timeOfDay": "07:30:00"},
                {"heatSetpoint": 18.5, "timeOfDay": "11:00:00"},
                {"heatSetpoint": 14.9, "timeOfDay": "21:30:00"},
            ],
        },
    ]
}


# GET /domesticHotWater/{DHW_ID}/schedule
# provenance: tests_rf/faked_server/const.py (MOCK_SCHEDULE_DHW, with 6 switchpoints a
# day cut to 4)
DHW_SCHEDULE: Final[TccDhwDailySchedulesT] = {
    "dailySchedules": [
        {
            "dayOfWeek": TccDayOfWeek.MONDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "08:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "22:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.TUESDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "08:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "22:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.WEDNESDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "08:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "22:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.THURSDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "08:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "22:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.FRIDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "08:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "22:30:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.SATURDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "09:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "23:00:00"},
            ],
        },
        {
            "dayOfWeek": TccDayOfWeek.SUNDAY,
            "switchpoints": [
                {"dhwState": TccDhwState.ON, "timeOfDay": "06:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "09:30:00"},
                {"dhwState": TccDhwState.ON, "timeOfDay": "16:30:00"},
                {"dhwState": TccDhwState.OFF, "timeOfDay": "23:00:00"},
            ],
        },
    ]
}


# provenance: the old tests_rf/test_v2_urls_cred.py (probed 2024-ish; scope is optional)
TOKEN: Final[TccOAuthTokenResponseT] = {
    "access_token": "HojUMRvmn...",
    "token_type": "bearer",
    "expires_in": 1799,
    "refresh_token": "vdBdHjxK...",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
}
