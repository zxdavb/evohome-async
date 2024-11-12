#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import Any, Final, NewType, TypedDict

import voluptuous as vol

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


class ErrorResponse(TypedDict):
    code: str
    message: str


class UserAccountResponse(TypedDict):
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


SCH_USER_ACCOUNT_RESPONSE: Final = vol.Schema(
    {
        vol.Required(SZ_USER_ID): int,
        vol.Required(SZ_USERNAME): vol.All(str, vol.Length(min=1)),  # email address
        vol.Required(SZ_FIRSTNAME): str,
        vol.Required(SZ_LASTNAME): str,
        vol.Required(SZ_STREET_ADDRESS): str,
        vol.Required(SZ_CITY): str,
        # l.Optional(SZ_STATE): str,  # Uncomment if state is used
        vol.Required(SZ_ZIPCODE): str,
        vol.Required(SZ_COUNTRY): vol.All(str, vol.Length(min=2)),  # GB
        vol.Required(SZ_TELEPHONE): str,
        vol.Required(SZ_USER_LANGUAGE): str,
        vol.Required(SZ_IS_ACTIVATED): bool,
        vol.Required(SZ_DEVICE_COUNT): int,
        vol.Required("tenantID"): int,
        vol.Required("securityQuestion1"): str,
        vol.Required("securityQuestion2"): str,
        vol.Required("securityQuestion3"): str,
        vol.Required(SZ_LATEST_EULA_ACCEPTED): bool,
    },
    extra=vol.ALLOW_EXTRA,
)


class SessionResponseT(TypedDict):
    sessionId: str
    userInfo: UserAccountResponse


class ThermostatResponse(TypedDict):
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


class DeviceResponse(TypedDict):
    GatewayId: int
    DeviceID: int
    ThermostatModelType: str
    DeviceType: int
    Name: str
    ScheduleCapable: bool
    HoldUntilCapable: bool
    Thermostat: ThermostatResponse
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


class TimeZoneResponse(TypedDict):
    ID: str
    DisplayName: str
    OffsetMinutes: int
    CurrentOffsetMinutes: int
    UsingDaylightSavingTime: bool


class LocationResponse(TypedDict):
    locationID: int  # is ID, not Id
    name: str
    streetAddress: str
    city: str
    state: str
    country: str
    zipcode: str
    type: str  # LocationType: "Commercial" | "Residential"
    hasStation: bool
    devices: list[DeviceResponse]
    weather: dict[str, Any]  # WeatherResponse
    daylightSavingTimeEnabled: bool
    timeZone: TimeZoneResponse
    oneTouchActionsSuspended: bool
    isLocationOwner: bool
    locationOwnerID: int  # ID, not Id
    locationOwnerName: str
    locationOwnerUserName: str
    canSearchForContractors: bool
    contractor: dict[str, Any]  # ContractorResponse


SCH_LOCATION_RESPONSE: Final = vol.Schema(
    {
        vol.Required(SZ_LOCATION_ID): int,  # is ID, not Id
        vol.Required(SZ_NAME): vol.All(str, vol.Length(min=1)),
        vol.Required(SZ_STREET_ADDRESS): str,
        vol.Required(SZ_CITY): str,
        vol.Optional(SZ_STATE): str,  # Uncomment if state is used
        vol.Required(SZ_COUNTRY): vol.All(str, vol.Length(min=2)),  # GB
        vol.Required(SZ_ZIPCODE): str,
        vol.Required("type"): vol.In(["Commercial", "Residential"]),
        vol.Required("hasStation"): bool,
        vol.Required(SZ_DEVICES): [dict],  # TODO: [DeviceResponse]
        vol.Required("oneTouchButtons"): list,
        vol.Required("weather"): {str: object},  # WeatherResponse
        vol.Required("daylightSavingTimeEnabled"): bool,
        vol.Required("timeZone"): {str: object},  # TimeZoneResponse
        vol.Required("oneTouchActionsSuspended"): bool,
        vol.Required("isLocationOwner"): bool,
        vol.Required("locationOwnerID"): int,  # ID, not Id
        vol.Required("locationOwnerName"): str,
        vol.Required("locationOwnerUserName"): vol.All(str, vol.Length(min=1)),
        vol.Required("canSearchForContractors"): bool,
        vol.Required("contractor"): {str: object},  # ContractorResponse
    },
    extra=vol.ALLOW_EXTRA,
)

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
