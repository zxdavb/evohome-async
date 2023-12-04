#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Constants."""

import re
from enum import EnumCheck, StrEnum, verify
from typing import Final

# all debug flags should be False for published code
_DEBUG_DONT_OBSFUCATE = False  # used for pytest scripts


REGEX_DHW_ID = r"[0-9]*"
REGEX_EMAIL_ADDRESS = r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"
REGEX_GATEWAY_ID = r"[0-9]*"
REGEX_LOCATION_ID = r"[0-9]*"
REGEX_SYSTEM_ID = r"[0-9]*"
REGEX_ZONE_ID = r"[0-9]*"


# These are vendor-specific constants, used for keys
SZ_ACTIVE_FAULTS = "activeFaults"
SZ_ALLOWED_FAN_MODES = "allowedFanModes"
SZ_ALLOWED_MODES = "allowedModes"
SZ_ALLOWED_SETPOINT_MODES = "allowedSetpointModes"
SZ_ALLOWED_STATES = "allowedStates"
SZ_ALLOWED_SYSTEM_MODES = "allowedSystemModes"

SZ_CAN_BE_CHANGED = "canBeChanged"
SZ_CAN_BE_PERMANENT = "canBePermanent"
SZ_CAN_BE_TEMPORARY = "canBeTemporary"
SZ_CAN_CONTROL_COOL = "canControlCool"
SZ_CAN_CONTROL_HEAT = "canControlHeat"
SZ_CITY = "city"
SZ_COOL_SETPOINT = "coolSetpoint"
SZ_COOL_SETPOINT_VALUE = "coolSetpointValue"  # an extrapolation
SZ_COUNTRY = "country"
SZ_CRC = "crc"
SZ_CURRENT_OFFSET_MINUTES = "currentOffsetMinutes"

SZ_DAILY_SCHEDULES = "dailySchedules"
SZ_DAY_OF_WEEK = "dayOfWeek"
SZ_DHW = "dhw"
SZ_DHW_ID = "dhwId"
SZ_DHW_STATE = "dhwState"
SZ_DHW_STATE_CAPABILITIES_RESPONSE = "dhwStateCapabilitiesResponse"
SZ_DISPLAY_NAME = "displayName"
SZ_DOMESTIC_HOT_WATER = "domesticHotWater"

SZ_FAN_MODE = "fanMode"
SZ_FAN_STATUS = "fanStatus"
SZ_FAULT_TYPE = "faultType"
SZ_FIRSTNAME = "firstname"

SZ_GATEWAY = "gateway"
SZ_GATEWAY_ID = "gatewayId"
SZ_GATEWAY_INFO = "gatewayInfo"
SZ_GATEWAYS = "gateways"

SZ_HEAT_SETPOINT = "heatSetpoint"
SZ_HEAT_SETPOINT_VALUE = "HeatSetpointValue"
SZ_HEATING_ZONE = "HeatingZone"

SZ_IS_AVAILABLE = "isAvailable"
SZ_IS_CANCELABLE = "isCancelable"
SZ_IS_CHANGEABLE = "isChangeable"
SZ_IS_PERMANENT = "isPermanent"
SZ_IS_WI_FI = "isWiFi"

SZ_LANGUAGE = "language"
SZ_LASTNAME = "lastname"
SZ_LOCATION = "location"
SZ_LOCATION_ID = "locationId"
SZ_LOCATION_INFO = "locationInfo"
SZ_LOCATION_OWNER = "locationOwner"
SZ_LOCATION_TYPE = "locationType"

SZ_MAC = "mac"
SZ_MAX_COOL_SETPOINT = "maxCoolSetpoint"  # an extrapolation
SZ_MAX_DURATION = "maxDuration"
SZ_MAX_HEAT_SETPOINT = "maxHeatSetpoint"
SZ_MAX_SWITCHPOINTS_PER_DAY = "maxSwitchpointsPerDay"
SZ_MIN_COOL_SETPOINT = "minCoolSetpoint"
SZ_MIN_DURATION = "minDuration"
SZ_MIN_HEAT_SETPOINT = "minHeatSetpoint"
SZ_MIN_SWITCHPOINTS_PER_DAY = "minSwitchpointsPerDay"
SZ_MODE = "mode"
SZ_MODEL_TYPE = "modelType"

SZ_NAME = "name"

SZ_OFFSET_MINUTES = "offsetMinutes"

SZ_PERMANENT = "permanent"
SZ_POSTCODE = "postcode"

SZ_SCHEDULE_CAPABILITIES = "scheduleCapabilities"
SZ_SCHEDULE_CAPABILITIES_RESPONSE = "scheduleCapabilitiesResponse"
SZ_SETPOINT_CAPABILITIES = "setpointCapabilities"
SZ_SETPOINT_DEADBAND = "setpointDeadband"
SZ_SETPOINT_MODE = "setpointMode"
SZ_SETPOINT_STATUS = "setpointStatus"
SZ_SETPOINT_VALUE_RESOLUTION = "setpointValueResolution"
SZ_SINCE = "since"
SZ_STATE = "state"
SZ_STATE_STATUS = "stateStatus"
SZ_STREET_ADDRESS = "streetAddress"
SZ_SUPPORTS_DAYLIGHT_SAVING = "supportsDaylightSaving"
SZ_SWITCHPOINTS = "switchpoints"
SZ_SYSTEM_ID = "systemId"
SZ_SYSTEM_MODE = "systemMode"
SZ_SYSTEM_MODE_STATUS = "systemModeStatus"

SZ_TARGET_COOL_TEMPERATURE = "targetCoolTemperature"  # an extrapolation
SZ_TARGET_HEAT_TEMPERATURE = "targetHeatTemperature"
SZ_TEMPERATURE = "temperature"
SZ_TEMPERATURE_CONTROL_SYSTEM = "temperatureControlSystem"
SZ_TEMPERATURE_CONTROL_SYSTEMS = "temperatureControlSystems"
SZ_TEMPERATURE_STATUS = "temperatureStatus"
SZ_TEMPERATURE_ZONE = "temperatureZone"
SZ_TIME_OF_DAY = "timeOfDay"
SZ_TIME_UNTIL = "timeUntil"
SZ_TIME_ZONE = "timeZone"
SZ_TIME_ZONE_ID = "timeZoneId"
SZ_TIMING_MODE = "timingMode"
SZ_TIMING_RESOLUTION = "timingResolution"

SZ_UNTIL = "until"
SZ_UNTIL_TIME = "untilTime"
SZ_USE_DAYLIGHT_SAVE_SWITCHING = "useDaylightSaveSwitching"
SZ_USER_ACCOUNT = "userAccount"
SZ_USER_ID = "userId"
SZ_USERNAME = "username"

SZ_VACATION_HOLD_CAPABILITIES = "vacationHoldCapabilities"
SZ_VALUE_RESOLUTION = "valueResolution"

SZ_ZONE_ID = "zoneId"
SZ_ZONE_TYPE = "zoneType"
SZ_ZONES = "zones"


SZ_MONDAY = "Monday"
SZ_TUESDAY = "Tuesday"
SZ_WEDNESDAY = "Wednesday"
SZ_THURSDAY = "Thursday"
SZ_FRIDAY = "Friday"
SZ_SATURDAY = "Saturday"
SZ_SUNDAY = "Sunday"

DAYS_OF_WEEK = (
    SZ_MONDAY,
    SZ_TUESDAY,
    SZ_WEDNESDAY,
    SZ_THURSDAY,
    SZ_FRIDAY,
    SZ_SATURDAY,
    SZ_SUNDAY,
)


SZ_OFF = "Off"
SZ_ON = "On"


SZ_AUTO = "Auto"
SZ_AUTO_WITH_ECO = "AutoWithEco"
SZ_AUTO_WITH_RESET = "AutoWithReset"
SZ_AWAY = "Away"
SZ_CUSTOM = "Custom"
SZ_DAY_OFF = "DayOff"
SZ_HEATING_OFF = "HeatingOff"

SZ_COOL = "Cool"
SZ_HEAT = "Heat"


@verify(EnumCheck.UNIQUE)
class DhwState(StrEnum):
    OFF: Final[str] = SZ_OFF
    ON: Final[str] = SZ_ON


@verify(EnumCheck.UNIQUE)
class FanMode(StrEnum):
    AUTO: Final[str] = SZ_AUTO
    ON: Final[str] = SZ_ON


@verify(EnumCheck.UNIQUE)
class FaultType(StrEnum):
    # W_A_CL: Final[str] = "DHWActuatorCommunicationLost"  # extrapolated
    DHW_S_CL: Final[str] = "DHWSensorCommunicationLost"
    DHW_S_LB: Final[str] = "DHWSensorLowBattery"  # extrapolated
    GWY_X_CL: Final[str] = "GatewayCommunicationLost"
    # S_X_LB: Final[str] = "TemperatureControlSystemLowBattery"  # extrapolated
    ZON_A_CL: Final[str] = "TempZoneActuatorCommunicationLost"
    ZON_A_LB: Final[str] = "TempZoneActuatorLowBattery"
    ZON_S_CL: Final[str] = "TempZoneSensorCommunicationLost"
    ZON_S_LB: Final[str] = "TempZoneSensorLowBattery"


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO: Final[str] = SZ_AUTO
    AUTO_WITH_ECO: Final[str] = SZ_AUTO_WITH_ECO
    AUTO_WITH_RESET: Final[str] = SZ_AUTO_WITH_RESET
    AWAY: Final[str] = SZ_AWAY
    CUSTOM: Final[str] = SZ_CUSTOM
    DAY_OFF: Final[str] = SZ_DAY_OFF
    HEATING_OFF: Final[str] = SZ_HEATING_OFF
    OFF: Final[str] = SZ_OFF  # not evohome (VisionProWifiRetail)
    HEAT: Final[str] = SZ_HEAT  # not evohome (VisionProWifiRetail)
    COOL: Final[str] = SZ_COOL  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class TcsModelType(StrEnum):
    EVO_TOUCH: Final[str] = "EvoTouch"
    FOCUS_PRO_WIFI_RETAIL: Final[str] = "FocusProWifiRetail"
    VISION_PRO_WIFI_RETAIL: Final[str] = "VisionProWifiRetail"


SZ_FOLLOW_SCHEDULE = "FollowSchedule"
SZ_PERMANENT_OVERRIDE = "PermanentOverride"
SZ_TEMPORARY_OVERRIDE = "TemporaryOverride"
SZ_VACATION_HOLD = "VacationHold"


@verify(EnumCheck.UNIQUE)
class ZoneMode(StrEnum):
    FOLLOW_SCHEDULE: Final[str] = SZ_FOLLOW_SCHEDULE
    PERMANENT_OVERRIDE: Final[str] = SZ_PERMANENT_OVERRIDE
    TEMPORARY_OVERRIDE: Final[str] = SZ_TEMPORARY_OVERRIDE
    VACATION_HOLD: Final[str] = SZ_VACATION_HOLD  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class ZoneModelType(StrEnum):
    FOCUS_PRO_WIFI_RETAIL: Final[str] = "FocusProWifiRetail"
    HEATING_ZONE: Final[str] = "HeatingZone"
    ROUND_MODULATION: Final[str] = "RoundModulation"
    ROUND_WIRELESS: Final[str] = "RoundWireless"
    UNKNOWN: Final[str] = "Unknown"
    VISION_PRO_WIFI_RETAIL: Final[str] = "VisionProWifiRetail"


SZ_ELECTRIC_HEAT = "ElectricHeat"  # TODO: needs confirming
SZ_MIXING_VALVE = "MixingValve"
SZ_RADIATOR_ZONE = "RadiatorZone"
SZ_THERMOSTAT = "Thermostat"
SZ_UNDERFLOOR_HEATING = "UnderfloorHeating"
SZ_UNKNOWN = "Unknown"
SZ_ZONE_VALVES = "ZoneValves"  # is not ZoneValve


@verify(EnumCheck.UNIQUE)
class ZoneType(StrEnum):
    MIXING_VALVE: Final[str] = SZ_MIXING_VALVE
    RADIATOR_ZONE: Final[str] = SZ_RADIATOR_ZONE
    THERMOSTAT: Final[str] = SZ_THERMOSTAT
    UNDERFLOOR_HEATING: Final[str] = SZ_UNDERFLOOR_HEATING
    UNKNOWN: Final[str] = SZ_UNKNOWN
    ZONE_VALVES: Final[str] = SZ_ZONE_VALVES


# these may not be required with Python 3.12+ (used for 'if mode in ZONE_MODES'...)
DHW_STATES = tuple(x.value for x in DhwState)
FAULT_TYPES = tuple(x.value for x in FaultType)
SYSTEM_MODES = tuple(x.value for x in SystemMode)
TCS_MODEL_TYPES = tuple(x.value for x in TcsModelType)
ZONE_MODEL_TYPES = tuple(x.value for x in ZoneModelType)
ZONE_MODES = tuple(x.value for x in ZoneMode)
ZONE_TYPES = tuple(x.value for x in ZoneType)


def obfuscate(value: bool | int | str) -> bool | int | str | None:
    if _DEBUG_DONT_OBSFUCATE:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"obfuscate() expects bool | int | str, got {type(value)}")
    if re.match(REGEX_EMAIL_ADDRESS, value):
        return "nobody@nowhere.com"
    return "********"
