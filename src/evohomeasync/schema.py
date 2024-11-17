#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import EnumCheck, StrEnum, verify
from typing import Any, Final, NewType, TypedDict, TypeVar

import voluptuous as vol

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


def camel_to_snake(s: str) -> str:
    """Return a string converted from camelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(s: str) -> str:
    """Return a string converted from snake_case to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _do_nothing(s: str) -> str:
    """Return a string unconverted."""
    return s


def _convert_keys(data: _T, fnc: Callable) -> _T:
    """Convert all keys in a dictionary to snake_case.

    Used after retreiiving JSON data from the vendor API.
    """

    if isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data

    return {fnc(k): convert_keys_to_snake_case(v) for k, v in data.items()}  # type: ignore[return-value]


def convert_keys_to_camel_case(data: _T) -> _T:
    return _convert_keys(data, camel_to_snake)


def convert_keys_to_snake_case(data: _T) -> _T:
    return _convert_keys(data, camel_to_snake)


class ErrorResponse(TypedDict):
    code: str
    message: str


class UserAccountResponseT(TypedDict):
    userID: int
    username: str  # email address
    firstname: str
    lastname: str
    streetAddress: str
    city: str
    # state: str
    zipcode: str
    country: str  # GB
    telephone: str
    userLanguage: str
    isActivated: bool
    deviceCount: int
    tenantID: int
    securityQuestion1: str  # "notUsed"
    securityQuestion2: str
    securityQuestion3: str
    latestEulaAccepted: bool


def factory_user_account_response(
    fnc: Callable[[str], str] = _do_nothing,
) -> vol.Schema:
    """Factory for the user account schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_USER_ID)): int,
            vol.Required(fnc(SZ_USERNAME)): vol.All(
                str, vol.Length(min=1)
            ),  # email address
            vol.Required(fnc(SZ_FIRSTNAME)): str,
            vol.Required(fnc(SZ_LASTNAME)): str,
            vol.Required(fnc(SZ_STREET_ADDRESS)): str,
            vol.Required(fnc(SZ_CITY)): str,
            # l.Optional(fnc(SZ_STATE)): str,  # Uncomment if state is used
            vol.Required(fnc(SZ_ZIPCODE)): str,
            vol.Required(fnc(SZ_COUNTRY)): vol.All(str, vol.Length(min=2)),  # GB
            vol.Required(fnc(SZ_TELEPHONE)): str,
            vol.Required(fnc(SZ_USER_LANGUAGE)): str,
            vol.Required(fnc(SZ_IS_ACTIVATED)): bool,
            vol.Required(fnc(SZ_DEVICE_COUNT)): int,
            vol.Required(fnc("tenantID")): int,
            vol.Required(fnc("securityQuestion1")): str,
            vol.Required(fnc("securityQuestion2")): str,
            vol.Required(fnc("securityQuestion3")): str,
            vol.Required(fnc(SZ_LATEST_EULA_ACCEPTED)): bool,
        },
        extra=vol.ALLOW_EXTRA,
    )


SCH_USER_ACCOUNT_RESPONSE: Final = factory_user_account_response()


class SessionResponseT(TypedDict):
    sessionId: str
    userInfo: UserAccountResponseT


class ThermostatResponseT(TypedDict):
    Units: str  # displayedUnits: Fahrenheit or Celsius
    IndoorTemperature: float
    OutdoorTemperature: float
    OutdoorTemperatureAvailable: bool
    OutdoorHumidity: float
    OutdootHumidityAvailable: bool
    IndoorHumidity: float
    IndoorTemperatureStatus: str  # Measured | NotAvailable | SensorError | SensorFault
    IndoorHumidityStatus: str
    OutdoorTemperatureStatus: str
    OutdoorHumidityStatus: str
    IsCommercial: bool
    AllowedModes: list[str]  # ThermostatMode
    Deadband: float
    MinHeatSetpoint: float
    MaxHeatSetpoint: float
    MinCoolSetpoint: float
    MaxCoolSetpoint: float
    CoolRate: float
    HeatRate: float
    IsPreCoolCapable: bool
    ChangeableValues: Any  # thermostatChangeableValues
    EquipmentOutputStatus: str  # Off | Heating | Cooling
    ScheduleCapable: bool
    VacationHoldChangeable: bool
    VacationHoldCancelable: bool
    ScheduleHeatSp: float
    ScheduleCoolSp: float
    SerialNumber: str
    PcbNumber: str


class DeviceResponseT(TypedDict):
    GatewayId: int
    DeviceID: int
    ThermostatModelType: str
    DeviceType: int
    Name: str
    ScheduleCapable: bool
    HoldUntilCapable: bool
    Thermostat: ThermostatResponseT
    Humidifier: dict[str, Any]  # HumidifierResponse
    Dehumidifier: dict[str, Any]  # DehumidifierResponse
    Fan: dict[str, Any]  # FanResponse
    Schedule: dict[str, Any]  # ScheduleResponse
    AlertSettings: dict[str, Any]  # AlertSettingsResponse
    IsUpgrading: bool
    IsAlive: bool
    ThermostatVersion: str
    macID: str
    LocationId: int
    DomainID: int
    Instance: int
    SerialNumber: str
    PcbNumber: str


class TimeZoneResponseT(TypedDict):
    ID: str
    DisplayName: str
    OffsetMinutes: int
    CurrentOffsetMinutes: int
    UsingDaylightSavingTime: bool


class LocationResponseT(TypedDict):
    locationID: int  # is ID, not Id
    name: str
    streetAddress: str
    city: str
    state: str
    country: str
    zipcode: str
    type: str  # LocationType: "Commercial" | "Residential"
    hasStation: bool
    devices: list[DeviceResponseT]
    weather: dict[str, Any]  # WeatherResponse
    daylightSavingTimeEnabled: bool
    timeZone: TimeZoneResponseT
    oneTouchActionsSuspended: bool
    isLocationOwner: bool
    locationOwnerID: int  # ID, not Id
    locationOwnerName: str
    locationOwnerUserName: str
    canSearchForContractors: bool
    contractor: dict[str, Any]  # ContractorResponse


def factory_user_account_response(
    fnc: Callable[[str], str] = _do_nothing,
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
            vol.Required(fnc("contractor")): {str: object},  # ContractorResponse
        },
        extra=vol.ALLOW_EXTRA,
    )


SCH_LOCATION_RESPONSE: Final = factory_user_account_response()


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
