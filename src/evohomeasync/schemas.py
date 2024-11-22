#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

from collections.abc import Callable
from enum import EnumCheck, StrEnum, verify
from typing import Any, Final, NewType, TypedDict, TypeVar

import voluptuous as vol

from evocommon.helpers import noop

_T = TypeVar("_T")


# TCC config, status dicts
_EvoLeafT = bool | float | int | str | list[str]  # Any
_DeviceDictT = NewType("_DeviceDictT", dict[str, Any])  # '_EvoDeviceT' | _EvoLeafT]
_EvoDictT = NewType("_EvoDictT", dict[str, Any])  # '_EvoDictT' | _EvoLeafT]
_EvoListT = NewType("_EvoListT", list[_EvoDictT])
_EvoSchemaT = _EvoDictT | _EvoListT

# TCC identifiers (Usr, Loc, Gwy, Sys, Zon|Dhw)
_DhwIdT = NewType("_DhwIdT", int)
_GatewayIdT = NewType("_GatewayIdT", int)
_LocationIdT = NewType("_LocationIdT", int)
_SystemIdT = NewType("_SystemIdT", int)
_UserIdT = NewType("_UserIdT", int)
_ZoneIdT = NewType("_ZoneIdT", int)
_ZoneNameT = NewType("_ZoneNameT", str)

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


#######################################################################################


# GET api/accountInfo -> userAccountInfoResponse
def factory_user_account_info_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to GET /accountInfo."""

    # username: an email address
    # country:  ISO 3166-1 alpha-2 format (e.g. GB)

    return vol.Schema(
        {
            vol.Required(fnc(SZ_USER_ID)): int,
            vol.Required(fnc(SZ_USERNAME)): vol.All(str, vol.Length(min=1)),
            vol.Required(fnc(SZ_FIRSTNAME)): str,
            vol.Required(fnc(SZ_LASTNAME)): str,
            vol.Required(fnc(SZ_STREET_ADDRESS)): str,
            vol.Required(fnc(SZ_CITY)): str,
            # l.Optional(fnc(SZ_STATE)): str,  # missing?
            vol.Required(fnc(SZ_ZIPCODE)): str,
            vol.Required(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),
            vol.Required(fnc(SZ_TELEPHONE)): str,
            vol.Required(fnc(SZ_USER_LANGUAGE)): str,
        },
        extra=vol.ALLOW_EXTRA,
    )


# POST api/session -> sessionResponse
def factory_session_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to POST /session."""

    # securityQuestionX: usu. "notUsed", a sentinel value

    SCH_USER_ACCOUNT_RESPONSE = factory_user_account_info_response(fnc).extend(
        {
            vol.Required(fnc(SZ_IS_ACTIVATED)): bool,
            vol.Optional(fnc(SZ_DEVICE_COUNT)): int,
            vol.Optional(fnc("tenantID")): int,
            vol.Optional(fnc("securityQuestion1")): str,
            vol.Optional(fnc("securityQuestion2")): str,
            vol.Optional(fnc("securityQuestion3")): str,
            vol.Required(fnc(SZ_LATEST_EULA_ACCEPTED)): bool,
        },
        extra=vol.ALLOW_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SESSION_ID)): str,
            vol.Required(fnc(SZ_USER_INFO)): SCH_USER_ACCOUNT_RESPONSE,
        },
        extra=vol.ALLOW_EXTRA,
    )


def factory_location_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the user account schema."""

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
            vol.Required(fnc("contractor")): {str: dict},  # ContractorResponse
        },
        extra=vol.ALLOW_EXTRA,
    )


# GET api/locations?userId={userId}&allData=True -> list[locationResponse]
def factory_location_response_list(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Schema for the response to GET api/locations?userId={userId}&allData=True."""

    return vol.Schema(
        vol.All([factory_location_response(fnc)], vol.Length(min=0)),
        extra=vol.ALLOW_EXTRA,
    )


#######################################################################################


SCH_USER_ACCOUNT_INFO_RESPONSE: Final = factory_user_account_info_response()
SCH_USER_SESSION_RESPONSE: Final = factory_session_response()
SCH_USER_LOCATIONS_RESPONSE: Final = factory_location_response_list()


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
SZ_AUTO: Final = "Auto"
SZ_AUTO_WITH_ECO: Final = "AutoWithEco"
SZ_AWAY: Final = "Away"
SZ_CUSTOM: Final = "Custom"
SZ_DAY_OFF: Final = "DayOff"
SZ_HEATING_OFF: Final = "HeatingOff"


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO = SZ_AUTO
    AUTO_WITH_ECO = SZ_AUTO_WITH_ECO
    AWAY = SZ_AWAY
    CUSTOM = SZ_CUSTOM
    DAY_OFF = SZ_DAY_OFF
    HEATING_OFF = SZ_HEATING_OFF


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


class TccErrorResponseT(TypedDict):
    code: str
    message: str


class TccUserAccountInfoResponseT(TypedDict):  # NOTE: is not  UserAccountResponseT
    userId: int
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


class TccUserAccountResponseT(  # NOTE: is not TccUserAccountInfoResponseT
    TccUserAccountInfoResponseT
):
    isActivated: bool
    deviceCount: int  # NotRequired?
    tenantId: int  # NotRequired?
    securityQuestion1: str  # NotRequired?
    securityQuestion2: str  # NotRequired?
    securityQuestion3: str  # NotRequired?
    latestEulaAccepted: bool  # NotRequired?


class TccSessionResponseT(TypedDict):
    sessionId: str
    userInfo: TccUserAccountResponseT


class TccWeatherResponseT(TypedDict):
    condition: str  # an enum
    temperature: float
    units: str  # Fahrenheit (precision 1.0) or Celsius (0.5)
    humidity: int
    phrase: str


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
    changeable_values: Any  # thermostatChangeableValues
    equipment_outputStatus: str  # Off | Heating | Cooling
    schedule_capable: bool
    vacationHoldChangeable: bool
    vacationHoldCancelable: bool
    scheduleHeatSp: float
    scheduleCoolSp: float
    serialNumber: str
    pcbNumber: str


class TccDeviceResponseT(TypedDict):
    gatewayId: int
    deviceId: int
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
    macId: str
    locationId: int
    domainId: int
    instance: int
    serialNumber: str
    pcbNumber: str


class TccTimeZoneResponseT(TypedDict):
    id: str
    displayName: str
    offsetMinutes: int
    currentOffsetMinutes: int
    usingDaylightSavingTime: bool


class TccLocationResponseT(TypedDict):
    locationID: _LocationIdT  # TODO: check is ID, not Id
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
    contractor: dict[str, Any]  # ContractorResponse


#######################################################################################
# These are identical but have snake_case keys, not camelCase keys...


class EvoErrorDictT(TypedDict):
    code: str
    message: str


class EvoUserAccountInfoDictT(TypedDict):  # NOT UserAccountResponseScT
    user_id: int
    username: str  # email address
    firstname: str
    lastname: str
    street_address: str
    city: str
    # state: str  # missing?
    zipcode: str
    country: str  # GB
    telephone: str
    user_language: str


class EvoUserAccountDictT(EvoUserAccountInfoDictT):  # NOT EvoUserAccountInfoT
    is_activated: bool
    device_count: int  # NotRequired?
    tenant_id: int  # NotRequired?
    security_question_1: str  # NotRequired?
    security_question_2: str  # NotRequired?
    security_question_3: str  # NotRequired?
    latest_eula_accepted: bool  # NotRequired?


class EvoSessionDictT(TypedDict):
    session_id: str
    user_info: EvoUserAccountDictT


class EvoWeatherDictT(TypedDict):
    condition: str  # an enum
    temperature: float
    units: str  # Fahrenheit (precision 1.0) or Celsius (0.5)
    humidity: int
    phrase: str


class EvoThermostatDictT(TypedDict):
    units: str  # displayedUnits: Fahrenheit or Celsius
    indoor_temperature: float
    outdoor_temperature: float
    outdoor_temperature_available: bool
    outdoor_humidity: float
    outdoor_Humidity_available: bool
    indoor_humidity: float
    indoor_temperature_status: str  # Measured|NotAvailable|SensorError|SensorFault
    indoor_humidity_status: str
    outdoor_temperature_status: str
    outdoor_humidity_status: str
    is_commercial: bool
    allowed_modes: list[str]  # ThermostatMode
    deadband: float
    min_heat_setpoint: float
    max_heat_setpoint: float
    min_cool_setpoint: float
    max_cool_setpoint: float
    cool_rate: float
    heat_rate: float
    is_pre_cool_capable: bool
    changeable_values: Any  # thermostatChangeableValues
    equipment_output_status: str  # Off | Heating | Cooling
    schedule_capable: bool
    vacation_hold_changeable: bool
    vacation_hold_cancelable: bool
    schedule_heat_sp: float
    schedule_cool_sp: float
    serial_number: str
    pcb_number: str


class EvoDeviceDictT(TypedDict):
    gateway_id: int
    device_id: int
    thermostat_model_type: str  # DOMESTIC_HOT_WATER or a zone
    device_type: int
    name: str
    schedule_capable: bool
    hold_until_capable: bool
    thermostat: EvoThermostatDictT
    humidifier: dict[str, Any]  # HumidifierResponse
    dehumidifier: dict[str, Any]  # DehumidifierResponse
    fan: dict[str, Any]  # FanResponse
    schedule: dict[str, Any]  # ScheduleResponse
    alert_settings: dict[str, Any]  # AlertSettingsResponse
    is_upgrading: bool
    is_alive: bool
    thermostat_version: str
    mac_id: str
    location_id: int
    domain_id: int
    instance: int
    serial_number: str
    pcb_number: str


class EvoTimeZoneDictT(TypedDict):
    id: str
    display_name: str
    offset_minutes: int
    current_offset_minutes: int
    using_daylight_saving_time: bool


class EvoLocationDictT(TypedDict):
    location_id: _LocationIdT
    name: str
    street_address: str
    city: str
    state: str
    country: str
    zipcode: str
    type: str  # LocationType: "Commercial" | "Residential"
    has_station: bool
    devices: list[EvoDeviceDictT]
    weather: EvoWeatherDictT  # WeatherResponse
    daylight_saving_time_enabled: bool
    time_zone: EvoTimeZoneDictT
    one_touch_actions_suspended: bool
    is_location_owner: bool
    locationOwner_id: int
    location_owner_name: str
    location_owner_user_name: str
    can_searchforcontractors: bool
    contractor: dict[str, Any]  # ContractorResponse
