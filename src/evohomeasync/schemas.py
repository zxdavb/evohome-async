"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import TYPE_CHECKING, Any, Final, NewType, NotRequired, TypedDict

import voluptuous as vol

from _evohome.helpers import noop, redact

if TYPE_CHECKING:
    from collections.abc import Callable

# Datetime format used by the vendor's API
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"


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
SZ_IS_ACTIVATED: Final = "isActivated"

SZ_LASTNAME: Final = "lastname"
SZ_LATEST_EULA_ACCEPTED: Final = "latestEulaAccepted"
SZ_LOCATION_ID: Final = "locationID"  # is ID, not Id

SZ_NAME: Final = "name"

SZ_SESSION_ID: Final = "sessionId"
SZ_STATE: Final = "state"
SZ_STREET_ADDRESS: Final = "streetAddress"
SZ_TELEPHONE: Final = "telephone"

SZ_USER_ID: Final = "userID"  # is ID, not Id
SZ_USER_INFO: Final = "userInfo"
SZ_USER_LANGUAGE: Final = "userLanguage"
SZ_USERNAME: Final = "username"

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
            vol.Required(fnc(SZ_FIRSTNAME)): vol.All(str, redact),
            vol.Required(fnc(SZ_LASTNAME)): vol.All(str, redact),
            vol.Required(fnc(SZ_STREET_ADDRESS)): vol.All(str, redact),
            vol.Required(fnc(SZ_CITY)): vol.All(str, redact),
            # l.Optional(fnc(SZ_STATE)): str,  # missing?
            vol.Required(fnc(SZ_ZIPCODE)): vol.All(str, redact),
            vol.Required(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),
            vol.Required(fnc(SZ_TELEPHONE)): vol.All(str, redact),
            vol.Required(fnc(SZ_USER_LANGUAGE)): str,
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
            vol.Required(fnc(SZ_IS_ACTIVATED)): bool,
            vol.Optional(fnc(SZ_DEVICE_COUNT)): int,
            vol.Optional(fnc("tenantID")): int,
            vol.Optional(fnc("securityQuestion1")): SCH_SECURITY_QUESTION,
            vol.Optional(fnc("securityQuestion2")): SCH_SECURITY_QUESTION,
            vol.Optional(fnc("securityQuestion3")): SCH_SECURITY_QUESTION,
            vol.Required(fnc(SZ_LATEST_EULA_ACCEPTED)): bool,
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


def _factory_location_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the user's location schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_LOCATION_ID)): int,  # is ID, not Id
            vol.Required(fnc(SZ_NAME)): vol.All(str, vol.Length(min=1)),
            vol.Required(fnc(SZ_STREET_ADDRESS)): str,
            vol.Required(fnc(SZ_CITY)): str,
            vol.Optional(fnc(SZ_STATE)): str,  # Optional
            vol.Required(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),  # GB
            vol.Required(fnc(SZ_ZIPCODE)): str,
            vol.Required(fnc("type")): vol.In(["Commercial", "Residential"]),
            vol.Required(fnc("hasStation")): bool,
            vol.Required(fnc(SZ_DEVICES)): [dict],  # TODO: [DeviceResponse]
            vol.Required(fnc("oneTouchButtons")): list,
            vol.Required(fnc("weather")): {str: object},  # WeatherResponse
            vol.Required(fnc("daylightSavingTimeEnabled")): bool,
            vol.Required(fnc("timeZone")): {str: object},  # TimeZoneResponse
            vol.Required(fnc("oneTouchActionsSuspended")): bool,
            vol.Required(fnc("isLocationOwner")): bool,
            vol.Required(fnc("locationOwnerID")): int,  # ID, not Id
            vol.Required(fnc("locationOwnerName")): str,
            vol.Required(fnc("locationOwnerUserName")): vol.All(str, vol.Length(min=1)),
            vol.Required(fnc("canSearchForContractors")): bool,
            vol.Optional(fnc("contractor")): {str: dict},  # ContractorResponse,Optional
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
SZ_MAC_ID: Final = "macID"  # is ID, not Id
SZ_MODE: Final = "mode"
SZ_NEXT_TIME: Final = "NextTime"
SZ_QUICK_ACTION: Final = "QuickAction"
SZ_QUICK_ACTION_NEXT_TIME: Final = "QuickActionNextTime"
SZ_SETPOINT: Final = "setpoint"
SZ_SPECIAL_MODES: Final = "SpecialModes"
SZ_STATUS: Final = "status"
SZ_TEMP: Final = "temp"
SZ_THERMOSTAT: Final = "thermostat"
SZ_THERMOSTAT_MODEL_TYPE: Final = "thermostatModelType"
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
    tenantId: int  # NotRequired?
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
    weather: TccWeatherResponseT  # WeatherResponse
    daylightSavingTimeEnabled: bool
    timeZone: TccTimeZoneResponseT
    oneTouchActionsSuspended: bool
    isLocationOwner: bool
    locationOwnerID: int  # TODO: check is ID, not Id
    locationOwnerName: str
    locationOwnerUserName: str
    canSearchforcontractors: bool
    contractor: NotRequired[dict[str, Any]]  # ContractorResponse


class TccDeviceResponseT(TypedDict):
    deviceID: _DhwIdT | _ZoneIdT  # is ID, not Id
    gatewayId: _GatewayIdT
    thermostatModelType: str  # DOMESTIC_HOT_WATER or a zone
    deviceType: int
    name: str
    scheduleCapable: bool
    holdUntilCapable: bool
    thermostat: TccThermostatResponseT
    humidifier: dict[str, Any]  # HumidifierResponse
    dehumidifier: dict[str, Any]  # DehumidifierResponse
    fan: dict[str, Any]  # FanResponse
    schedule: dict[str, Any]  # ScheduleResponse
    alertSettings: dict[str, Any]  # AlertSettingsResponse
    isUpgrading: bool
    isAlive: bool
    thermostatVersion: str
    macID: str  # is ID, not Id
    locationID: _LocationIdT  # is ID, not Id
    domainID: int  # is ID, not Id
    instance: int
    serialNumber: str
    pcbNumber: str


class TccThermostatResponseT(TypedDict):
    units: str  # displayedUnits: Fahrenheit or Celsius
    indoorTemperature: float
    outdoorTemperature: float
    outdoorTemperatureAvailable: bool
    outdoorHumidity: float
    outdoorHumidityAvailable: bool
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
    coolRate: float
    heatRate: float
    is_pre_cool_capable: bool
    changeable_values: TccThermostatChangeableValues
    equipment_outputStatus: str  # Off | Heating | Cooling
    schedule_capable: bool
    vacationHoldChangeable: bool
    vacationHoldCancelable: bool
    scheduleHeatSp: float
    scheduleCoolSp: float
    serialNumber: str
    pcbNumber: str


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
