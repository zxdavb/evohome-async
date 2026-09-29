"""Schema for the vendor's TCC v1 API.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the probatio
schemas, which can be used to validate/coerce the vendor's responses.

A key is vol.Required only if this library references it: any key we do not need is
vol.Optional, so that a response missing it will still validate. So vol.Optional here
does not imply the vendor may omit the key - only that we can carry on if it does. The
Tcc*T typed dicts remain the record of the vendor's API, and the few vol.Optionals that
the vendor genuinely may omit are tagged `# is NotRequired` to match them.

Two exceptions are vol.Required despite not being referenced. Entity ids are always
required, as they are the foreign keys of the data model: user (and location owner),
location, gateway, zone, DHW and device. And username, as it is the account's identity.

domainID is the one id that is not: it is sent with every device, but which entity it
identifies is unknown - it is not the control system, as it matches no id in the v2
API (in particular, it is not systemId), nor is it tenantID.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "sessionId", "thermostatModelType")
- PascalCase for JSON values that are enum strings (e.g. "AutoWithEco", "DayOff")
- SCREAMING_SNAKE_CASE for a few type values (e.g. "EMEA_ZONE", "DOMESTIC_HOT_WATER")

The convention is not applied consistently: the user id is "userID" as a JSON key, but
"userId" as a URL param (see S1_USER_ID).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import EnumCheck, StrEnum, verify
from typing import TYPE_CHECKING, Any, Final, NewType, NotRequired, TypedDict

import probatio as vol

from _evohome.helpers import (
    TCC_DTM_STRFTIME as TCC_DTM_STRFTIME,  # noqa: PLC0414
    noop,
    redact,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from _evohome.helpers import Validator

# TCC identifiers (Usr, Loc, Gwy, Sys, Zon|Dhw)
_DhwIdT = NewType("_DhwIdT", int)
_GatewayIdT = NewType("_GatewayIdT", int)
_LocationIdT = NewType("_LocationIdT", int)
_SystemIdT = NewType("_SystemIdT", int)
_UserIdT = NewType("_UserIdT", int)
_ZoneIdT = NewType("_ZoneIdT", int)

# TCC other
_TaskIdT = NewType("_TaskIdT", int)  # an int, unlike the v2 API (where it is a str)


#
S1_ALERT_SETTINGS: Final = "alertSettings"
S1_ALLOWED_MODES: Final = "allowedModes"

S1_CAN_SEARCH_FOR_CONTRACTORS: Final = "canSearchForContractors"
S1_CHANGEABLE_VALUES: Final = "changeableValues"
S1_CITY: Final = "city"
S1_CODE: Final = "code"
S1_CONTRACTOR: Final = "contractor"
S1_COOL_RATE: Final = "coolRate"
S1_COOL_SETPOINT: Final = "coolSetpoint"
S1_COUNTRY: Final = "country"

S1_DAYLIGHT_SAVING_TIME_ENABLED: Final = "daylightSavingTimeEnabled"
S1_DEADBAND: Final = "deadband"
S1_DEHUMIDIFIER: Final = "dehumidifier"
S1_DEVICE_COUNT: Final = "deviceCount"
S1_DEVICE_ID: Final = "deviceID"  # is ID, not Id
S1_DEVICE_TYPE: Final = "deviceType"
S1_DEVICES: Final = "devices"
S1_DOMAIN_ID: Final = "domainID"  # is ID, not Id
S1_DR_EVENTS: Final = "drEvents"

S1_EQUIPMENT_OUTPUT_STATUS: Final = "equipmentOutputStatus"

S1_FAN: Final = "fan"
S1_FIRSTNAME: Final = "firstname"

S1_GATEWAY_ID: Final = "gatewayId"

S1_HAS_STATION: Final = "hasStation"
S1_HEAT_RATE: Final = "heatRate"
S1_HEAT_SETPOINT: Final = "heatSetpoint"
S1_HOLD_UNTIL_CAPABLE: Final = "holdUntilCapable"
S1_HUMIDIFIER: Final = "humidifier"
S1_ID: Final = "id"

S1_INDOOR_HUMIDITY: Final = "indoorHumidity"
S1_INDOOR_HUMIDITY_STATUS: Final = "indoorHumidityStatus"
S1_INDOOR_TEMPERATURE: Final = "indoorTemperature"
S1_INDOOR_TEMPERATURE_STATUS: Final = "indoorTemperatureStatus"
S1_INSTANCE: Final = "instance"
S1_IS_ACTIVATED: Final = "isActivated"
S1_IS_ALIVE: Final = "isAlive"
S1_IS_COMMERCIAL: Final = "isCommercial"
S1_IS_LOCATION_OWNER: Final = "isLocationOwner"
S1_IS_PRE_COOL_CAPABLE: Final = "isPreCoolCapable"
S1_IS_UPGRADING: Final = "isUpgrading"

S1_LASTNAME: Final = "lastname"
S1_LATEST_EULA_ACCEPTED: Final = "latestEulaAccepted"
S1_LOCATION_ID: Final = "locationID"  # is ID, not Id
S1_LOCATION_OWNER_ID: Final = "locationOwnerID"  # is ID, not Id
S1_LOCATION_OWNER_NAME: Final = "locationOwnerName"
S1_LOCATION_OWNER_USER_NAME: Final = "locationOwnerUserName"

S1_MAC_ID: Final = "macID"  # is ID, not Id
S1_MAX_COOL_SETPOINT: Final = "maxCoolSetpoint"
S1_MAX_HEAT_SETPOINT: Final = "maxHeatSetpoint"
S1_MESSAGE: Final = "message"
S1_MIN_COOL_SETPOINT: Final = "minCoolSetpoint"
S1_MIN_HEAT_SETPOINT: Final = "minHeatSetpoint"
S1_MODE: Final = "mode"

S1_NAME: Final = "name"
S1_NEXT_TIME: Final = "nextTime"

S1_ONE_TOUCH_ACTIONS_SUSPENDED: Final = "oneTouchActionsSuspended"
S1_ONE_TOUCH_BUTTONS: Final = "oneTouchButtons"
S1_OUTDOOR_HUMIDITY: Final = "outdoorHumidity"
S1_OUTDOOR_HUMIDITY_STATUS: Final = "outdoorHumidityStatus"
S1_OUTDOOR_TEMPERATURE: Final = "outdoorTemperature"
S1_OUTDOOR_TEMPERATURE_AVAILABLE: Final = "outdoorTemperatureAvailable"
S1_OUTDOOR_TEMPERATURE_STATUS: Final = "outdoorTemperatureStatus"
S1_OUTDOOT_HUMIDITY_AVAILABLE: Final = "outdootHumidityAvailable"  # NOTE: not a typo

S1_PCB_NUMBER: Final = "pcbNumber"

S1_QUICK_ACTION: Final = "quickAction"
S1_QUICK_ACTION_NEXT_TIME: Final = "quickActionNextTime"

S1_SCHEDULE: Final = "schedule"
S1_SCHEDULE_CAPABLE: Final = "scheduleCapable"
S1_SCHEDULE_COOL_SP: Final = "scheduleCoolSp"
S1_SCHEDULE_HEAT_SP: Final = "scheduleHeatSp"
S1_SECURITY_QUESTION_1: Final = "securityQuestion1"
S1_SECURITY_QUESTION_2: Final = "securityQuestion2"
S1_SECURITY_QUESTION_3: Final = "securityQuestion3"
S1_SERIAL_NUMBER: Final = "serialNumber"
S1_SESSION_ID: Final = "sessionId"
S1_SPECIAL_MODES: Final = "specialModes"
S1_STATE: Final = "state"
S1_STATUS: Final = "status"
S1_STREET_ADDRESS: Final = "streetAddress"
S1_SYSTEM_CONFIGURATION: Final = "systemConfiguration"

S1_TELEPHONE: Final = "telephone"
S1_TENANT_ID: Final = "tenantID"  # is ID, not Id
S1_THERMOSTAT: Final = "thermostat"
S1_THERMOSTAT_MODEL_TYPE: Final = "thermostatModelType"
S1_THERMOSTAT_VERSION: Final = "thermostatVersion"
S1_TIME_ZONE: Final = "timeZone"
S1_TYPE: Final = "type"

S1_UNITS: Final = "units"
S1_USER_ID: Final = "userID"  # is ID, not Id
S1_USER_INFO: Final = "userInfo"
S1_USER_LANGUAGE: Final = "userLanguage"
S1_USERNAME: Final = "username"

S1_VACATION_HOLD_CANCELABLE: Final = "vacationHoldCancelable"
S1_VACATION_HOLD_CHANGEABLE: Final = "vacationHoldChangeable"
S1_VALUE: Final = "value"

S1_WEATHER: Final = "weather"

S1_ZIPCODE: Final = "zipcode"


# String enums (not camelCase, usu. start with an upper case letter)
@verify(EnumCheck.UNIQUE)
class TccSystemMode(StrEnum):
    AUTO = "Auto"
    AUTO_WITH_ECO = "AutoWithEco"
    AWAY = "Away"
    CUSTOM = "Custom"
    DAY_OFF = "DayOff"
    HEATING_OFF = "HeatingOff"


@verify(EnumCheck.UNIQUE)
class TccDhwMode(StrEnum):  # changeableValues.mode, allowedModes (of a DHW)
    DHW_OFF = "DHWOff"
    DHW_ON = "DHWOn"


@verify(EnumCheck.UNIQUE)
class TccEquipmentOutputStatus(StrEnum):  # thermostat.equipmentOutputStatus
    COOLING = "Cooling"
    HEATING = "Heating"
    OFF = "Off"


@verify(EnumCheck.UNIQUE)
class TccLocationType(StrEnum):  # location.type
    COMMERCIAL = "Commercial"
    RESIDENTIAL = "Residential"


@verify(EnumCheck.UNIQUE)
class TccSetpointStatus(StrEnum):  # changeableValues[.heatSetpoint].status
    HOLD = "Hold"
    SCHEDULED = "Scheduled"
    TEMPORARY = "Temporary"  # a zone only
    VACATION_HOLD = "VacationHold"  # a zone only


@verify(EnumCheck.UNIQUE)
class TccSensorStatus(StrEnum):  # thermostat.(in|out)door(Temperature|Humidity)Status
    MEASURED = "Measured"
    NOT_AVAILABLE = "NotAvailable"
    SENSOR_FAULT = "SensorFault"


@verify(EnumCheck.UNIQUE)
class TccThermostatMode(StrEnum):  # changeableValues.mode, allowedModes (of a zone)
    AUTO_COOL = "AutoCool"  # not seen with EMEA Evohome
    AUTO_HEAT = "AutoHeat"  # not seen with EMEA Evohome
    COOL = "Cool"  # not seen with EMEA Evohome
    EMERGENCY_HEAT = "EmergencyHeat"  # not seen with EMEA Evohome
    HEAT = "Heat"
    OFF = "Off"
    SOUTHERN_AWAY = "SouthernAway"  # not seen with EMEA Evohome


# NOTE: This list may be incomplete (a zone type need only be prefixed with "EMEA_")
@verify(EnumCheck.UNIQUE)
class TccThermostatModelType(StrEnum):  # device.thermostatModelType
    """The vendor's model type of a device (these values are received, not sent).

    Unlike the other enums here, these values are not PascalCase. They must not be sent
    in a request body, as the library would mangle them: see AbstractAuth.request(),
    which converts StrEnum values (e.g. DOMESTIC_HOT_WATER -> DOMESTICHotWater).

    This list is not exhaustive, but these systems are expected to work OK.
    """

    DOMESTIC_HOT_WATER = "DOMESTIC_HOT_WATER"
    EVO_TOUCH_SYSTEM = "EVO_TOUCH_SYSTEM"
    EMEA_ROUND_MODULATION = "EMEA_ROUND_MODULATION"
    EMEA_ROUND_WIRELESS = "EMEA_ROUND_WIRELESS"
    EMEA_ZONE = "EMEA_ZONE"
    FOCUS_PRO_REDLINK = "FOCUS_PRO_REDLINK"
    FOCUS_PRO_WIFI_RETAIL = "FOCUS_PRO_WIFI_RETAIL"
    FOCUS_PRO_WIFI_TRADE = "FOCUS_PRO_WIFI_TRADE"
    FOCUS_PRO_WIFI_ETAILER = "FOCUS_PRO_WIFI_ETAILER"
    SARATOGA = "SARATOGA"
    UNKNOWN = "UNKNOWN"


def factory_failure_response(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the code/message response schema."""

    entry = vol.Schema(
        {
            vol.Required(fnc(S1_CODE)): str,
            vol.Required(fnc(S1_MESSAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(vol.All([entry], vol.Length(min=1)))


# PUT (e.g. api/devices/{zone_id}/thermostat/changeableValues/heatSetpoint) -> task
def factory_task_response(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the task response schema (a successful PUT)."""

    return vol.Schema(
        {
            vol.Required(fnc(S1_ID)): int,
        },
        extra=vol.PREVENT_EXTRA,
    )


# GET api/accountInfo -> userAccountInfoResponse
def factory_user_account_info_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to GET api/accountInfo."""

    # username: an email address
    # country:  ISO 3166-1 alpha-2 format (e.g. GB)

    return vol.Schema(
        {
            vol.Required(fnc(S1_USER_ID)): int,
            vol.Required(fnc(S1_USERNAME)): vol.All(str, vol.Length(min=1), redact),
            vol.Optional(fnc(S1_FIRSTNAME)): vol.All(str, redact),
            vol.Optional(fnc(S1_LASTNAME)): vol.All(str, redact),
            vol.Optional(fnc(S1_STREET_ADDRESS)): vol.All(str, redact),
            vol.Optional(fnc(S1_CITY)): vol.All(str, redact),
            vol.Optional(fnc(S1_STATE)): vol.All(str, redact),  # documented, not seen
            vol.Optional(fnc(S1_ZIPCODE)): vol.All(str, redact),
            vol.Optional(fnc(S1_COUNTRY)): vol.All(str, vol.Length(min=2)),
            vol.Optional(fnc(S1_TELEPHONE)): vol.All(str, redact),
            vol.Optional(fnc(S1_USER_LANGUAGE)): str,
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
            vol.Optional(fnc(S1_IS_ACTIVATED)): bool,
            vol.Optional(fnc(S1_DEVICE_COUNT)): int,
            vol.Optional(fnc(S1_TENANT_ID)): int,
            vol.Optional(fnc(S1_SECURITY_QUESTION_1)): SCH_SECURITY_QUESTION,
            vol.Optional(fnc(S1_SECURITY_QUESTION_2)): SCH_SECURITY_QUESTION,
            vol.Optional(fnc(S1_SECURITY_QUESTION_3)): SCH_SECURITY_QUESTION,
            vol.Optional(fnc(S1_LATEST_EULA_ACCEPTED)): bool,  # via dict.get() only
        },
        extra=vol.ALLOW_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S1_SESSION_ID)): vol.All(str, redact),
            vol.Required(fnc(S1_USER_INFO)): SCH_USER_ACCOUNT_RESPONSE,
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_thermostat_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the thermostat schema of a location's device."""

    return vol.Schema(
        {
            vol.Required(fnc(S1_INDOOR_TEMPERATURE)): float,
            vol.Required(fnc(S1_INDOOR_TEMPERATURE_STATUS)): str,  # Measured, etc.
            vol.Required(fnc(S1_ALLOWED_MODES)): [str],  # ThermostatMode
            vol.Required(fnc(S1_MAX_HEAT_SETPOINT)): float,
            vol.Required(fnc(S1_MIN_HEAT_SETPOINT)): float,
            vol.Optional(fnc(S1_UNITS)): str,
            vol.Optional(fnc(S1_OUTDOOR_TEMPERATURE)): float,
            vol.Optional(fnc(S1_OUTDOOR_TEMPERATURE_AVAILABLE)): bool,
            vol.Optional(fnc(S1_OUTDOOR_HUMIDITY)): float,
            vol.Optional(fnc(S1_OUTDOOT_HUMIDITY_AVAILABLE)): bool,  # NOTE: not a typo
            vol.Optional(fnc(S1_INDOOR_HUMIDITY)): float,
            vol.Optional(fnc(S1_INDOOR_HUMIDITY_STATUS)): str,
            vol.Optional(fnc(S1_OUTDOOR_TEMPERATURE_STATUS)): str,
            vol.Optional(fnc(S1_OUTDOOR_HUMIDITY_STATUS)): str,
            vol.Optional(fnc(S1_IS_COMMERCIAL)): bool,
            vol.Optional(fnc(S1_DEADBAND)): float,
            vol.Optional(fnc(S1_MIN_COOL_SETPOINT)): float,
            vol.Optional(fnc(S1_MAX_COOL_SETPOINT)): float,
            vol.Optional(fnc(S1_COOL_RATE)): float,  # is NotRequired
            vol.Optional(fnc(S1_HEAT_RATE)): float,  # is NotRequired
            vol.Optional(fnc(S1_IS_PRE_COOL_CAPABLE)): bool,
            vol.Optional(fnc(S1_CHANGEABLE_VALUES)): {str: object},
            vol.Optional(fnc(S1_EQUIPMENT_OUTPUT_STATUS)): str,
            vol.Optional(fnc(S1_SCHEDULE_CAPABLE)): bool,
            vol.Optional(fnc(S1_VACATION_HOLD_CHANGEABLE)): bool,
            vol.Optional(fnc(S1_VACATION_HOLD_CANCELABLE)): bool,
            vol.Optional(fnc(S1_SCHEDULE_HEAT_SP)): float,
            vol.Optional(fnc(S1_SCHEDULE_COOL_SP)): float,
            vol.Optional(fnc(S1_SERIAL_NUMBER)): str,
            vol.Optional(fnc(S1_PCB_NUMBER)): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_device_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the schema of one of a location's devices (a DHW or a zone)."""

    return vol.Schema(
        {
            vol.Required(fnc(S1_DEVICE_ID)): int,  # is ID, not Id
            vol.Required(fnc(S1_GATEWAY_ID)): int,
            # NOTE: is an int for the Honeywell TH9320WF3003 (c.f. DOMESTIC_HOT_WATER)
            vol.Required(fnc(S1_THERMOSTAT_MODEL_TYPE)): vol.Any(str, int),
            vol.Required(fnc(S1_NAME)): str,  # is "" for DHW
            vol.Required(fnc(S1_INSTANCE)): int,  # is the zone idx
            vol.Required(fnc(S1_MAC_ID)): str,  # is ID, not Id
            vol.Required(fnc(S1_THERMOSTAT)): _factory_thermostat_response(fnc),
            vol.Optional(fnc(S1_DEVICE_TYPE)): int,
            vol.Optional(fnc(S1_SCHEDULE_CAPABLE)): bool,
            vol.Optional(fnc(S1_HOLD_UNTIL_CAPABLE)): bool,
            vol.Optional(fnc(S1_HUMIDIFIER)): {str: object},
            vol.Optional(fnc(S1_DEHUMIDIFIER)): {str: object},
            vol.Optional(fnc(S1_FAN)): {str: object},
            vol.Optional(fnc(S1_SCHEDULE)): {str: object},
            vol.Optional(fnc(S1_ALERT_SETTINGS)): {str: object},
            vol.Optional(fnc(S1_IS_UPGRADING)): bool,
            vol.Optional(fnc(S1_IS_ALIVE)): bool,
            vol.Optional(fnc(S1_THERMOSTAT_VERSION)): str,
            vol.Required(fnc(S1_LOCATION_ID)): int,
            vol.Optional(fnc(S1_DOMAIN_ID)): int,
            vol.Optional(fnc(S1_SERIAL_NUMBER)): str,
            vol.Optional(fnc(S1_PCB_NUMBER)): str,
            vol.Optional(fnc(S1_DR_EVENTS)): list,
            vol.Optional(fnc(S1_SYSTEM_CONFIGURATION)): {str: object},
        },
        extra=vol.ALLOW_EXTRA,
    )


def _factory_location_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the user's location schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S1_LOCATION_ID)): int,  # is ID, not Id
            vol.Required(fnc(S1_NAME)): vol.All(str, vol.Length(min=1)),
            vol.Optional(fnc(S1_STREET_ADDRESS)): str,
            vol.Optional(fnc(S1_CITY)): str,
            vol.Optional(fnc(S1_STATE)): str,
            vol.Required(fnc(S1_COUNTRY)): vol.All(str, vol.Length(min=2)),  # GB
            vol.Optional(fnc(S1_ZIPCODE)): str,
            vol.Optional(fnc(S1_TYPE)): vol.In(TccLocationType),
            vol.Optional(fnc(S1_HAS_STATION)): bool,
            vol.Required(fnc(S1_DEVICES)): [_factory_device_response(fnc)],
            vol.Optional(fnc(S1_ONE_TOUCH_BUTTONS)): list,
            vol.Optional(fnc(S1_WEATHER)): {str: object},  # is NotRequired
            vol.Required(fnc(S1_DAYLIGHT_SAVING_TIME_ENABLED)): bool,
            vol.Required(fnc(S1_TIME_ZONE)): {str: object},  # TimeZoneResponse
            vol.Optional(fnc(S1_ONE_TOUCH_ACTIONS_SUSPENDED)): bool,
            vol.Optional(fnc(S1_IS_LOCATION_OWNER)): bool,
            vol.Required(fnc(S1_LOCATION_OWNER_ID)): int,
            vol.Optional(fnc(S1_LOCATION_OWNER_NAME)): str,
            vol.Optional(fnc(S1_LOCATION_OWNER_USER_NAME)): vol.All(
                str, vol.Length(min=1)
            ),
            vol.Optional(fnc(S1_CAN_SEARCH_FOR_CONTRACTORS)): bool,
            vol.Optional(fnc(S1_CONTRACTOR)): {str: dict},  # is NotRequired
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
# These are the top-level schema validators for the vendor API responses.

# NOTE: These validators can return values that do not satisfy their annotations.

# For example, `TccUserAccountInfoResponseT.firstname` is promised to exist (it isn't
# `NotRequired`), but the schema has `vol.Optional(fnc(S1_FIRSTNAME))`.

# The factories are used to produce two distinct schemas: as used by vendor API calls
# and responses (TCC_*) and as used by the runtime validators (EVO_*); the latter would
# use less restrictive TypedDicts (but does not have to).

TCC_FAILURE_RESPONSE: Final[Validator[list[TccFailureResponseT]]] = (
    factory_failure_response()
)
TCC_TASK_RESPONSE: Final[Validator[TccTaskResponseT]] = factory_task_response()
TCC_GET_USR_INFO: Final[Validator[TccUserAccountInfoResponseT]] = (
    # This validator can accept {userID, username} because all other account fields are
    # vol.Optional in factory_user_account_info_response, yet its new return type
    # promises TccUserAccountInfoResponseT, where those fields are required.
    factory_user_account_info_response()
)
TCC_GET_USR_LOCS: Final[Validator[list[TccLocationResponseT]]] = (
    # factory_location_response_list deliberately marks many location, device, and
    # thermostat keys optional, while TccLocationResponseT and its nested vendor-
    # documentation types require them.
    factory_location_response_list()
)
TCC_POST_USR_SESSION: Final[Validator[TccSessionResponseT]] = (
    # The session schema embeds the permissive account-info schema and makes the
    # additional account fields optional, but TccSessionResponseT.userInfo is
    # TccUserAccountResponseT, whose fields are required.
    factory_session_response()
)


#######################################################################################
# These the responses via the vendor's API; they have camelCase keys...
# These typed dicts represent the 'ground truth' as best known for an undocumented API


type _TccResponse = Mapping[str, object]


class TccFailureResponseT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    code: str
    message: str


class TccTaskResponseT(TypedDict):
    """Typed dict for responses from the vendor servers for successful PUTs."""

    id: _TaskIdT  # e.g. {"id": 1234567890}


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
    state: NotRequired[str]  # documented, but absent from all responses seen
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
    type: TccLocationType
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
    contractor: NotRequired[_TccResponse]  # ContractorResponse


class TccDeviceResponseT(TypedDict):
    deviceID: _DhwIdT | _ZoneIdT  # is ID, not Id
    gatewayId: _GatewayIdT
    # enum may be incomplete, so allow str; is an int for some (e.g. Honeywell TH9320WF3003)
    thermostatModelType: TccThermostatModelType | str | int
    deviceType: int
    name: str
    scheduleCapable: bool
    holdUntilCapable: bool
    thermostat: TccThermostatResponseT
    humidifier: NotRequired[_TccResponse]  # HumidifierResponse
    dehumidifier: NotRequired[_TccResponse]  # DehumidifierResponse
    fan: NotRequired[_TccResponse]  # FanResponse
    schedule: NotRequired[_TccResponse]  # ScheduleResponse
    alertSettings: NotRequired[_TccResponse]  # AlertSettingsResponse
    isUpgrading: bool
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
    indoorTemperatureStatus: TccSensorStatus
    indoorHumidityStatus: TccSensorStatus
    outdoorTemperatureStatus: TccSensorStatus
    outdoorHumidityStatus: TccSensorStatus
    isCommercial: bool
    allowedModes: list[TccThermostatMode] | list[TccDhwMode]  # a zone | a DHW
    deadband: float
    minHeatSetpoint: float
    maxHeatSetpoint: float
    minCoolSetpoint: float
    maxCoolSetpoint: float
    coolRate: NotRequired[float]
    heatRate: NotRequired[float]
    isPreCoolCapable: NotRequired[bool]
    # the Dhw variant is sent for a DOMESTIC_HOT_WATER device, else the Zone variant
    changeableValues: TccZoneChangeableValuesT | TccDhwChangeableValuesT
    equipmentOutputStatus: NotRequired[TccEquipmentOutputStatus]
    scheduleCapable: bool
    vacationHoldChangeable: bool
    vacationHoldCancelable: bool
    scheduleHeatSp: float
    scheduleCoolSp: float
    serialNumber: NotRequired[str]
    pcbNumber: NotRequired[str]


class TccZoneChangeableValuesT(TypedDict):
    """The changeableValues of a zone (c.f. TccDhwChangeableValuesT).

    "changeableValues": {
        "mode": "Off",
        "heatSetpoint": {"value": 21.0, "status": "Scheduled"},
        "vacationHoldDays": 0,
    },
    """

    mode: TccThermostatMode  # usu. Off
    heatSetpoint: TccHeatSetpointT
    vacationHoldDays: int
    nextTime: NotRequired[str]  # documented, not seen (a local time)


class TccDhwChangeableValuesT(TypedDict):
    """The changeableValues of a DHW (c.f. TccZoneChangeableValuesT).

    "changeableValues": {"mode": "DHWOff", "status": "Scheduled"},
    """

    mode: TccDhwMode
    status: TccSetpointStatus  # Scheduled, Hold
    nextTime: NotRequired[str]  # documented, not seen (a local time)


class TccHeatSetpointT(TypedDict):
    value: float
    status: TccSetpointStatus
    nextTime: NotRequired[str]  # documented, not seen (a local time)


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


#######################################################################################
# These are the request bodies sent to the vendor's API (PUT)


class TccSetTcsModeT(TypedDict):
    """PUT /evoTouchSystems?locationId={loc_id}"""

    quickAction: TccSystemMode
    quickActionNextTime: NotRequired[str | None]  # "%Y-%m-%dT%H:%M:%SZ"


class TccSetDhwModeT(TypedDict):
    """PUT /devices/{dhw_id}/thermostat/changeableValues"""

    status: TccSetpointStatus  # Scheduled, Hold
    mode: NotRequired[TccDhwMode | None]  # required by Hold
    nextTime: NotRequired[str | None]  # "%Y-%m-%dT%H:%M:%SZ"
    specialModes: NotRequired[None]
    heatSetpoint: NotRequired[None]
    coolSetpoint: NotRequired[None]


class TccSetZonModeT(TypedDict):
    """PUT /devices/{zon_id}/thermostat/changeableValues/heatSetpoint"""

    status: TccSetpointStatus  # Scheduled, Temporary, Hold
    value: NotRequired[float | None]  # required by Temporary, Hold
    nextTime: NotRequired[str | None]  # required by Temporary; "%Y-%m-%dT%H:%M:%SZ"
