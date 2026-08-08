"""Schema for the vendor's TCC v0 API.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the voluptuous
schemas, which can be used to validate/coerce the vendor's responses.

A key is vol.Required only if this library references it: any key we do not need is
vol.Optional, so that a response missing it will still validate. So vol.Optional here
does not imply the vendor may omit the key - only that we can carry on if it does. The
Tcc*T typed dicts remain the record of the vendor's API, and the few vol.Optionals that
the vendor genuinely may omit are tagged `# is NotRequired` to match them.

Two exceptions are vol.Required despite not being referenced. Entity ids are always
required, as they are the foreign keys of the data model: user (and location owner),
location, gateway, control system (domainID), zone, DHW and device. And username, as
it is the account's identity.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "sessionId", "thermostatModelType")
- PascalCase for JSON values that are enum strings (e.g. "AutoWithEco", "DayOff")
- SCREAMING_SNAKE_CASE for a few type values (e.g. "EMEA_ZONE", "DOMESTIC_HOT_WATER")

The convention is not applied consistently: the user id is "userID" as a JSON key, but
"userId" as a URL param (see SZ_USER_ID).
"""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import TYPE_CHECKING, Any, Final, NewType, NotRequired, TypedDict

import voluptuous as vol

from _evohome.helpers import (
    TCC_DTM_STRFTIME as TCC_DTM_STRFTIME,  # noqa: PLC0414
    noop,
    redact,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# TCC identifiers (Usr, Loc, Gwy, Sys, Zon|Dhw)
_DhwIdT = NewType("_DhwIdT", int)
_GatewayIdT = NewType("_GatewayIdT", int)
_LocationIdT = NewType("_LocationIdT", int)
_SystemIdT = NewType("_SystemIdT", int)  # domainId ??
_UserIdT = NewType("_UserIdT", int)
_ZoneIdT = NewType("_ZoneIdT", int)

# TCC other
_TaskIdT = NewType("_TaskIdT", str)  # TODO: int or str?


#
SZ_ALLOWED_MODES: Final = "allowedModes"
SZ_CHANGEABLE_VALUES: Final = "changeableValues"
SZ_CITY: Final = "city"
SZ_COUNTRY: Final = "country"

SZ_DEVICE_COUNT: Final = "deviceCount"
SZ_DEVICE_ID: Final = "deviceID"  # is ID, not Id
SZ_DEVICES: Final = "devices"
SZ_DOMAIN_ID: Final = "domainID"  # is ID, not Id

SZ_FIRSTNAME: Final = "firstname"
SZ_GATEWAY_ID: Final = "gatewayId"
SZ_INDOOR_TEMPERATURE: Final = "indoorTemperature"
SZ_INDOOR_TEMPERATURE_STATUS: Final = "indoorTemperatureStatus"
SZ_INSTANCE: Final = "instance"
SZ_IS_ACTIVATED: Final = "isActivated"

SZ_LASTNAME: Final = "lastname"
SZ_LATEST_EULA_ACCEPTED: Final = "latestEulaAccepted"
SZ_LOCATION_ID: Final = "locationID"  # is ID, not Id

SZ_MAC_ID: Final = "macID"  # is ID, not Id
SZ_MAX_HEAT_SETPOINT: Final = "maxHeatSetpoint"
SZ_MIN_HEAT_SETPOINT: Final = "minHeatSetpoint"

SZ_NAME: Final = "name"

SZ_SESSION_ID: Final = "sessionId"
SZ_STATE: Final = "state"
SZ_STREET_ADDRESS: Final = "streetAddress"
SZ_TELEPHONE: Final = "telephone"
SZ_THERMOSTAT: Final = "thermostat"
SZ_THERMOSTAT_MODEL_TYPE: Final = "thermostatModelType"

SZ_USER_ID: Final = "userID"  # is ID, not Id
SZ_USER_INFO: Final = "userInfo"
SZ_USER_LANGUAGE: Final = "userLanguage"
SZ_USERNAME: Final = "username"

SZ_WEATHER: Final = "weather"

SZ_ZIPCODE: Final = "zipcode"


"""
    [
        {
            "locationID": l["locationID"],
            "devices": [
                {
                    k: v
                    for k, v in d.items()
                    if k[-2:].lower() == "id" or k in ("instance", "name")
                }
                for d in l["devices"]
            ],
        }
        for l in config
    ]
"""


def factory_failure_response(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the code/message response schema."""

    entry = vol.Schema(
        {
            vol.Required(fnc("code")): str,
            vol.Required(fnc("message")): str,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(vol.All([entry], vol.Length(min=1)))


# GET api/accountInfo -> userAccountInfoResponse
def factory_user_account_info_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to GET api/accountInfo."""

    # username: an email address
    # country:  ISO 3166-1 alpha-2 format (e.g. GB)

    return vol.Schema(
        {
            vol.Required(fnc(SZ_USER_ID)): int,
            vol.Required(fnc(SZ_USERNAME)): vol.All(str, vol.Length(min=1), redact),
            vol.Optional(fnc(SZ_FIRSTNAME)): vol.All(str, redact),
            vol.Optional(fnc(SZ_LASTNAME)): vol.All(str, redact),
            vol.Optional(fnc(SZ_STREET_ADDRESS)): vol.All(str, redact),
            vol.Optional(fnc(SZ_CITY)): vol.All(str, redact),
            # l.Optional(fnc(SZ_STATE)): str,  # truly absent
            vol.Optional(fnc(SZ_ZIPCODE)): vol.All(str, redact),
            vol.Optional(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),
            vol.Optional(fnc(SZ_TELEPHONE)): vol.All(str, redact),
            vol.Optional(fnc(SZ_USER_LANGUAGE)): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


# POST api/session -> sessionResponse
def factory_session_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to POST api/session."""

    # securityQuestionX: usu. "notUsed", a sentinel value
    SCH_SECURITY_QUESTION = vol.Any("notUsed", vol.All(str, redact))

    SCH_USER_ACCOUNT_RESPONSE = factory_user_account_info_response(fnc).extend(
        {
            vol.Optional(fnc(SZ_IS_ACTIVATED)): bool,
            vol.Optional(fnc(SZ_DEVICE_COUNT)): int,
            vol.Optional(fnc("tenantID")): int,
            vol.Optional(fnc("securityQuestion1")): SCH_SECURITY_QUESTION,
            vol.Optional(fnc("securityQuestion2")): SCH_SECURITY_QUESTION,
            vol.Optional(fnc("securityQuestion3")): SCH_SECURITY_QUESTION,
            vol.Optional(fnc(SZ_LATEST_EULA_ACCEPTED)): bool,  # via dict.get() only
        },
        extra=vol.ALLOW_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SESSION_ID)): vol.All(str, redact),
            vol.Required(fnc(SZ_USER_INFO)): SCH_USER_ACCOUNT_RESPONSE,
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_thermostat_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the thermostat schema of a location's device."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_INDOOR_TEMPERATURE)): float,
            vol.Required(fnc(SZ_INDOOR_TEMPERATURE_STATUS)): str,  # Measured, etc.
            vol.Required(fnc(SZ_ALLOWED_MODES)): [str],  # ThermostatMode
            vol.Required(fnc(SZ_MAX_HEAT_SETPOINT)): float,
            vol.Required(fnc(SZ_MIN_HEAT_SETPOINT)): float,
            vol.Optional(fnc("units")): str,
            vol.Optional(fnc("outdoorTemperature")): float,
            vol.Optional(fnc("outdoorTemperatureAvailable")): bool,
            vol.Optional(fnc("outdoorHumidity")): float,
            vol.Optional(fnc("outdootHumidityAvailable")): bool,  # NOTE: not a typo
            vol.Optional(fnc("indoorHumidity")): float,
            vol.Optional(fnc("indoorHumidityStatus")): str,
            vol.Optional(fnc("outdoorTemperatureStatus")): str,
            vol.Optional(fnc("outdoorHumidityStatus")): str,
            vol.Optional(fnc("isCommercial")): bool,
            vol.Optional(fnc("deadband")): float,
            vol.Optional(fnc("minCoolSetpoint")): float,
            vol.Optional(fnc("maxCoolSetpoint")): float,
            vol.Optional(fnc("coolRate")): float,  # is NotRequired
            vol.Optional(fnc("heatRate")): float,  # is NotRequired
            vol.Optional(fnc("isPreCoolCapable")): bool,
            vol.Optional(fnc(SZ_CHANGEABLE_VALUES)): {str: object},
            vol.Optional(fnc("equipmentOutputStatus")): str,
            vol.Optional(fnc("scheduleCapable")): bool,
            vol.Optional(fnc("vacationHoldChangeable")): bool,
            vol.Optional(fnc("vacationHoldCancelable")): bool,
            vol.Optional(fnc("scheduleHeatSp")): float,
            vol.Optional(fnc("scheduleCoolSp")): float,
            vol.Optional(fnc("serialNumber")): str,
            vol.Optional(fnc("pcbNumber")): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_device_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the schema of one of a location's devices (a DHW or a zone)."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_DEVICE_ID)): int,  # is ID, not Id
            vol.Required(fnc(SZ_GATEWAY_ID)): int,
            # NOTE: is an int for the Honeywell TH9320WF3003 (c.f. DOMESTIC_HOT_WATER)
            vol.Required(fnc(SZ_THERMOSTAT_MODEL_TYPE)): vol.Any(str, int),
            vol.Required(fnc(SZ_NAME)): str,  # is "" for DHW
            vol.Required(fnc(SZ_INSTANCE)): int,  # is the zone idx
            vol.Required(fnc(SZ_MAC_ID)): str,  # is ID, not Id
            vol.Required(fnc(SZ_THERMOSTAT)): _factory_thermostat_response(fnc),
            vol.Optional(fnc("deviceType")): int,
            vol.Optional(fnc("scheduleCapable")): bool,
            vol.Optional(fnc("holdUntilCapable")): bool,
            vol.Optional(fnc("humidifier")): {str: object},
            vol.Optional(fnc("dehumidifier")): {str: object},
            vol.Optional(fnc("fan")): {str: object},
            vol.Optional(fnc("schedule")): {str: object},
            vol.Optional(fnc("alertSettings")): {str: object},
            vol.Optional(fnc("isUpgrading")): bool,
            vol.Optional(fnc("isAlive")): bool,
            vol.Optional(fnc("thermostatVersion")): str,
            vol.Required(fnc(SZ_LOCATION_ID)): int,
            vol.Required(fnc(SZ_DOMAIN_ID)): int,  # is the control system's id
            vol.Optional(fnc("serialNumber")): str,
            vol.Optional(fnc("pcbNumber")): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_location_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the user's location schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_LOCATION_ID)): int,  # is ID, not Id
            vol.Required(fnc(SZ_NAME)): vol.All(str, vol.Length(min=1)),
            vol.Optional(fnc(SZ_STREET_ADDRESS)): str,
            vol.Optional(fnc(SZ_CITY)): str,
            vol.Optional(fnc(SZ_STATE)): str,
            vol.Required(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),  # GB
            vol.Optional(fnc(SZ_ZIPCODE)): str,
            vol.Optional(fnc("type")): vol.In(["Commercial", "Residential"]),
            vol.Optional(fnc("hasStation")): bool,
            vol.Required(fnc(SZ_DEVICES)): [_factory_device_response(fnc)],
            vol.Optional(fnc("oneTouchButtons")): list,
            vol.Optional(fnc(SZ_WEATHER)): {str: object},  # is NotRequired
            vol.Required(fnc("daylightSavingTimeEnabled")): bool,
            vol.Required(fnc("timeZone")): {str: object},  # TimeZoneResponse
            vol.Optional(fnc("oneTouchActionsSuspended")): bool,
            vol.Optional(fnc("isLocationOwner")): bool,
            vol.Required(fnc("locationOwnerID")): int,
            vol.Optional(fnc("locationOwnerName")): str,
            vol.Optional(fnc("locationOwnerUserName")): vol.All(str, vol.Length(min=1)),
            vol.Optional(fnc("canSearchForContractors")): bool,
            vol.Optional(fnc("contractor")): {str: dict},  # is NotRequired
            # NOTE: these two are per-device keys (c.f. _factory_device_response); they
            # are here only because EvoTcsInfoDictT claims them, and are in no fixture
            vol.Optional(fnc(SZ_DOMAIN_ID)): int,
            vol.Optional(fnc("thermostatVersion")): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


# GET api/locations?userId={userId}&allData=True -> list[locationResponse]
def factory_location_response_list(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to GET api/locations?userId={userId}&allData=True."""

    return vol.Schema(
        vol.All([_factory_location_response(fnc)], vol.Length(min=0)),
        extra=vol.ALLOW_EXTRA,
    )


#######################################################################################


TCC_FAILURE_RESPONSE: Final = factory_failure_response()
TCC_GET_USR_INFO: Final = factory_user_account_info_response()
TCC_GET_USR_LOCS: Final = factory_location_response_list()
TCC_POST_USR_SESSION: Final = factory_session_response()


# schema keys (start with a lower case letter)
SZ_COOL_SETPOINT: Final = "coolSetpoint"
SZ_HEAT_SETPOINT: Final = "heatSetpoint"

SZ_ID: Final = "id"  # is id, not Id/ID
SZ_MODE: Final = "mode"
SZ_NEXT_TIME: Final = "NextTime"
SZ_QUICK_ACTION: Final = "QuickAction"
SZ_QUICK_ACTION_NEXT_TIME: Final = "QuickActionNextTime"
SZ_SETPOINT: Final = "setpoint"
SZ_SPECIAL_MODES: Final = "SpecialModes"
SZ_STATUS: Final = "status"
SZ_TEMP: Final = "temp"
SZ_VALUE: Final = "value"


# schema values (start with an upper case letter)
@verify(EnumCheck.UNIQUE)
class TccSystemMode(StrEnum):
    AUTO = "Auto"
    AUTO_WITH_ECO = "AutoWithEco"
    AWAY = "Away"
    CUSTOM = "Custom"
    DAY_OFF = "DayOff"
    HEATING_OFF = "HeatingOff"


#
SZ_DHW_OFF: Final = "DHWOff"
SZ_DHW_ON: Final = "DHWOn"
#
SZ_DOMESTIC_HOT_WATER: Final = "DOMESTIC_HOT_WATER"
SZ_EMEA_ZONE: Final = "EMEA_ZONE"
#
SZ_HOLD: Final = "Hold"
SZ_SCHEDULED: Final = "Scheduled"
SZ_TEMPORARY: Final = "Temporary"
#
SZ_HEAT: Final = "Heat"
SZ_OFF: Final = "Off"


#######################################################################################
# These the responses via the vendor's API; they have camelCase keys...


class TccFailureResponseT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    code: str
    message: str


class TccSessionResponseT(TypedDict):
    """POST api/session"""

    sessionId: str
    userInfo: TccUserAccountResponseT


class TccUserAccountInfoResponseT(TypedDict):  # NOTE: is not TccUserAccountResponseT
    """GET api/accountInfo"""

    userID: _UserIdT
    username: str  # email address
    firstname: str
    lastname: str
    streetAddress: str
    city: str
    # state: str  # missing?
    zipcode: str
    country: str  # GB
    telephone: str
    userLanguage: str


class TccUserAccountResponseT(TccUserAccountInfoResponseT):
    """GET api/userAccounts?userId={userId}"""

    isActivated: bool
    deviceCount: int  # NotRequired?
    tenantID: int  # NotRequired?
    securityQuestion1: str  # NotRequired?
    securityQuestion2: str  # NotRequired?
    securityQuestion3: str  # NotRequired?
    latestEulaAccepted: bool  # NotRequired?


class TccLocationResponseT(TypedDict):
    """GET api/locations?locationId={locationId}&allData=True"""

    locationID: _LocationIdT  # is ID, not Id
    name: str
    streetAddress: str
    city: str
    state: str
    country: str
    zipcode: str
    type: str  # LocationType: "Commercial" | "Residential"
    hasStation: bool
    devices: list[TccDeviceResponseT]
    weather: NotRequired[TccWeatherResponseT]  # WeatherResponse, if hasStation is True
    daylightSavingTimeEnabled: bool
    timeZone: TccTimeZoneResponseT
    oneTouchActionsSuspended: bool
    oneTouchButtons: list[str]  # is [] in all known responses
    isLocationOwner: bool
    locationOwnerID: int  # TODO: check is ID, not Id
    locationOwnerName: str
    locationOwnerUserName: str
    canSearchForContractors: bool
    contractor: NotRequired[dict[str, Any]]  # ContractorResponse


class TccDeviceResponseT(TypedDict):
    deviceID: _DhwIdT | _ZoneIdT  # is ID, not Id
    gatewayId: _GatewayIdT
    # is an int only for the Honeywell TH9320WF3003 (deviceType 48), which sends 36
    thermostatModelType: str | int  # DOMESTIC_HOT_WATER or a zone
    deviceType: int
    name: str
    scheduleCapable: bool
    holdUntilCapable: bool
    thermostat: TccThermostatResponseT
    humidifier: NotRequired[dict[str, Any]]  # HumidifierResponse
    dehumidifier: NotRequired[dict[str, Any]]  # DehumidifierResponse
    fan: NotRequired[dict[str, Any]]  # FanResponse
    schedule: NotRequired[dict[str, Any]]  # ScheduleResponse
    alertSettings: NotRequired[dict[str, Any]]  # AlertSettingsResponse
    isUpgrading: NotRequired[bool]
    isAlive: bool
    thermostatVersion: str
    macID: str  # is ID, not Id
    locationID: _LocationIdT  # is ID, not Id
    domainID: int  # is ID, not Id
    instance: int
    serialNumber: NotRequired[str]
    pcbNumber: NotRequired[str]
    drEvents: NotRequired[list[Any]]
    systemConfiguration: NotRequired[dict[str, Any]]


class TccThermostatResponseT(TypedDict):
    units: str  # displayedUnits: Fahrenheit or Celsius
    indoorTemperature: float
    outdoorTemperature: float
    outdoorTemperatureAvailable: bool
    outdoorHumidity: float
    outdootHumidityAvailable: bool  # NOTE: not a typo
    indoorHumidity: float
    indoorTemperatureStatus: str  # Measured|NotAvailable|SensorError|SensorFault
    indoorHumidityStatus: str
    outdoorTemperatureStatus: str
    outdoorHumidityStatus: str
    isCommercial: bool
    allowedModes: list[str]  # ThermostatMode
    deadband: float
    minHeatSetpoint: float
    maxHeatSetpoint: float
    minCoolSetpoint: float
    maxCoolSetpoint: float
    coolRate: NotRequired[float]
    heatRate: NotRequired[float]
    isPreCoolCapable: NotRequired[bool]
    changeableValues: TccThermostatChangeableValues
    equipmentOutputStatus: NotRequired[str]  # Off | Heating | Cooling
    scheduleCapable: bool
    vacationHoldChangeable: bool
    vacationHoldCancelable: bool
    scheduleHeatSp: float
    scheduleCoolSp: float
    serialNumber: NotRequired[str]
    pcbNumber: NotRequired[str]


class TccThermostatChangeableValues(TypedDict):
    """
    "changeableValues": {
        "mode": "Off",
        "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
        "vacationHoldDays": 0,
    },
    """

    mode: str  # Off
    heatSetpoint: _TccSetpointDict
    vacationHoldDays: int


class TccThermostatChangeableValuesDhw(TypedDict):
    mode: str  # Off
    status: str


class _TccSetpointDict(TypedDict):
    value: float
    status: str  # Scheduled, Temporary, Hold, VacationHold


class TccWeatherResponseT(TypedDict):
    condition: str  # an enum
    temperature: float
    units: str  # Fahrenheit (precision 1.0) or Celsius (0.5)
    humidity: int
    phrase: str


class TccTimeZoneResponseT(TypedDict):
    id: str
    displayName: str
    offsetMinutes: int
    currentOffsetMinutes: int
    usingDaylightSavingTime: bool
