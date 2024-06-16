#!/usr/bin/env python3
"""evohomeasync2 schema - shared constants."""

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
SZ_ACTIVE_FAULTS: Final = "activeFaults"
SZ_ALLOWED_FAN_MODES: Final = "allowedFanModes"
SZ_ALLOWED_MODES: Final = "allowedModes"
SZ_ALLOWED_SETPOINT_MODES: Final = "allowedSetpointModes"
SZ_ALLOWED_STATES: Final = "allowedStates"
SZ_ALLOWED_SYSTEM_MODES: Final = "allowedSystemModes"

SZ_CAN_BE_CHANGED: Final = "canBeChanged"
SZ_CAN_BE_PERMANENT: Final = "canBePermanent"
SZ_CAN_BE_TEMPORARY: Final = "canBeTemporary"
SZ_CAN_CONTROL_COOL: Final = "canControlCool"
SZ_CAN_CONTROL_HEAT: Final = "canControlHeat"
SZ_CITY: Final = "city"
SZ_COOL_SETPOINT: Final = "coolSetpoint"
SZ_COOL_SETPOINT_VALUE: Final = "coolSetpointValue"  # an extrapolation
SZ_COUNTRY: Final = "country"
SZ_CRC: Final = "crc"
SZ_CURRENT_OFFSET_MINUTES: Final = "currentOffsetMinutes"

SZ_DAILY_SCHEDULES: Final = "dailySchedules"
SZ_DAY_OF_WEEK: Final = "dayOfWeek"
SZ_DHW: Final = "dhw"
SZ_DHW_ID: Final = "dhwId"
SZ_DHW_STATE: Final = "dhwState"
SZ_DHW_STATE_CAPABILITIES_RESPONSE: Final = "dhwStateCapabilitiesResponse"
SZ_DISPLAY_NAME: Final = "displayName"
SZ_DOMESTIC_HOT_WATER: Final = "domesticHotWater"

SZ_FAN_MODE: Final = "fanMode"
SZ_FAN_STATUS: Final = "fanStatus"
SZ_FAULT_TYPE: Final = "faultType"
SZ_FIRSTNAME: Final = "firstname"

SZ_GATEWAY: Final = "gateway"
SZ_GATEWAY_ID: Final = "gatewayId"
SZ_GATEWAY_INFO: Final = "gatewayInfo"
SZ_GATEWAYS: Final = "gateways"

SZ_HEAT_SETPOINT: Final = "heatSetpoint"
SZ_HEAT_SETPOINT_VALUE: Final = "HeatSetpointValue"

SZ_IS_AVAILABLE: Final = "isAvailable"
SZ_IS_CANCELABLE: Final = "isCancelable"
SZ_IS_CHANGEABLE: Final = "isChangeable"
SZ_IS_PERMANENT: Final = "isPermanent"
SZ_IS_WI_FI: Final = "isWiFi"

SZ_LANGUAGE: Final = "language"
SZ_LASTNAME: Final = "lastname"
SZ_LOCATION: Final = "location"
SZ_LOCATION_ID: Final = "locationId"
SZ_LOCATION_INFO: Final = "locationInfo"
SZ_LOCATION_OWNER: Final = "locationOwner"
SZ_LOCATION_TYPE: Final = "locationType"

SZ_MAC: Final = "mac"
SZ_MAX_COOL_SETPOINT: Final = "maxCoolSetpoint"  # an extrapolation
SZ_MAX_DURATION: Final = "maxDuration"
SZ_MAX_HEAT_SETPOINT: Final = "maxHeatSetpoint"
SZ_MAX_SWITCHPOINTS_PER_DAY: Final = "maxSwitchpointsPerDay"
SZ_MIN_COOL_SETPOINT: Final = "minCoolSetpoint"
SZ_MIN_DURATION: Final = "minDuration"
SZ_MIN_HEAT_SETPOINT: Final = "minHeatSetpoint"
SZ_MIN_SWITCHPOINTS_PER_DAY: Final = "minSwitchpointsPerDay"
SZ_MODE: Final = "mode"
SZ_MODEL_TYPE: Final = "modelType"

SZ_NAME: Final = "name"

SZ_OFFSET_MINUTES: Final = "offsetMinutes"

SZ_PERMANENT: Final = "permanent"
SZ_POSTCODE: Final = "postcode"

SZ_SCHEDULE_CAPABILITIES: Final = "scheduleCapabilities"
SZ_SCHEDULE_CAPABILITIES_RESPONSE: Final = "scheduleCapabilitiesResponse"
SZ_SETPOINT_CAPABILITIES: Final = "setpointCapabilities"
SZ_SETPOINT_DEADBAND: Final = "setpointDeadband"
SZ_SETPOINT_MODE: Final = "setpointMode"
SZ_SETPOINT_STATUS: Final = "setpointStatus"
SZ_SETPOINT_VALUE_RESOLUTION: Final = "setpointValueResolution"
SZ_SINCE: Final = "since"
SZ_STATE: Final = "state"
SZ_STATE_STATUS: Final = "stateStatus"
SZ_STREET_ADDRESS: Final = "streetAddress"
SZ_SUPPORTS_DAYLIGHT_SAVING: Final = "supportsDaylightSaving"
SZ_SWITCHPOINTS: Final = "switchpoints"
SZ_SYSTEM_ID: Final = "systemId"
SZ_SYSTEM_MODE: Final = "systemMode"
SZ_SYSTEM_MODE_STATUS: Final = "systemModeStatus"

SZ_TARGET_COOL_TEMPERATURE: Final = "targetCoolTemperature"  # an extrapolation
SZ_TARGET_HEAT_TEMPERATURE: Final = "targetHeatTemperature"
SZ_TEMPERATURE: Final = "temperature"
SZ_TEMPERATURE_CONTROL_SYSTEM: Final = "temperatureControlSystem"
SZ_TEMPERATURE_CONTROL_SYSTEMS: Final = "temperatureControlSystems"
SZ_TEMPERATURE_STATUS: Final = "temperatureStatus"
SZ_TEMPERATURE_ZONE: Final = "temperatureZone"
SZ_TIME_OF_DAY: Final = "timeOfDay"
SZ_TIME_UNTIL: Final = "timeUntil"
SZ_TIME_ZONE: Final = "timeZone"
SZ_TIME_ZONE_ID: Final = "timeZoneId"
SZ_TIMING_MODE: Final = "timingMode"
SZ_TIMING_RESOLUTION: Final = "timingResolution"

SZ_UNTIL: Final = "until"
SZ_UNTIL_TIME: Final = "untilTime"
SZ_USE_DAYLIGHT_SAVE_SWITCHING: Final = "useDaylightSaveSwitching"
SZ_USER_ACCOUNT: Final = "userAccount"
SZ_USER_ID: Final = "userId"
SZ_USERNAME: Final = "username"

SZ_VACATION_HOLD_CAPABILITIES: Final = "vacationHoldCapabilities"
SZ_VALUE_RESOLUTION: Final = "valueResolution"

SZ_ZONE_ID: Final = "zoneId"
SZ_ZONE_TYPE: Final = "zoneType"
SZ_ZONES: Final = "zones"


# These are vendor-specific constants, used for values
SZ_DURATION: Final = "Duration"
SZ_HEATING_ZONE: Final = "HeatingZone"
SZ_PERIOD: Final = "Period"
SZ_UNKNOWN: Final = "Unknown"


SZ_MONDAY: Final = "Monday"
SZ_TUESDAY: Final = "Tuesday"
SZ_WEDNESDAY: Final = "Wednesday"
SZ_THURSDAY: Final = "Thursday"
SZ_FRIDAY: Final = "Friday"
SZ_SATURDAY: Final = "Saturday"
SZ_SUNDAY: Final = "Sunday"

DAYS_OF_WEEK = (
    SZ_MONDAY,
    SZ_TUESDAY,
    SZ_WEDNESDAY,
    SZ_THURSDAY,
    SZ_FRIDAY,
    SZ_SATURDAY,
    SZ_SUNDAY,
)


SZ_OFF: Final = "Off"
SZ_ON: Final = "On"


SZ_AUTO: Final = "Auto"
SZ_AUTO_WITH_ECO: Final = "AutoWithEco"
SZ_AUTO_WITH_RESET: Final = "AutoWithReset"
SZ_AWAY: Final = "Away"
SZ_CUSTOM: Final = "Custom"
SZ_DAY_OFF: Final = "DayOff"
SZ_HEATING_OFF: Final = "HeatingOff"

SZ_COOL: Final = "Cool"
SZ_HEAT: Final = "Heat"


@verify(EnumCheck.UNIQUE)
class DhwState(StrEnum):
    OFF: Final = SZ_OFF
    ON: Final = SZ_ON


@verify(EnumCheck.UNIQUE)
class FanMode(StrEnum):
    AUTO: Final = SZ_AUTO
    ON: Final = SZ_ON


@verify(EnumCheck.UNIQUE)
class FaultType(StrEnum):  # NOTE: This list is incomplete
    SYS_B_CL: Final = "BoilerCommunicationLost"
    SYS_C_CL: Final = "ChValveCommunicationLost"
    DHW_A_FL: Final = "DHWActuatorFailure"
    # W_A_CL: Final = "DHWActuatorCommunicationLost"  # extrapolated
    DHW_S_CL: Final = "DHWSensorCommunicationLost"
    DHW_S_FL: Final = "DHWSensorFailure"
    DHW_S_LB: Final = "DHWSensorLowBattery"  # extrapolated
    GWY_X_CL: Final = "GatewayCommunicationLost"
    # S_X_LB: Final = "TemperatureControlSystemLowBattery"  # extrapolated
    ZON_A_CL: Final = "TempZoneActuatorCommunicationLost"
    ZON_A_LB: Final = "TempZoneActuatorLowBattery"
    ZON_S_CL: Final = "TempZoneSensorCommunicationLost"
    ZON_S_LB: Final = "TempZoneSensorLowBattery"


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO: Final = SZ_AUTO
    AUTO_WITH_ECO: Final = SZ_AUTO_WITH_ECO
    AUTO_WITH_RESET: Final = SZ_AUTO_WITH_RESET
    AWAY: Final = SZ_AWAY
    CUSTOM: Final = SZ_CUSTOM
    DAY_OFF: Final = SZ_DAY_OFF
    HEATING_OFF: Final = SZ_HEATING_OFF
    OFF: Final = SZ_OFF  # not evohome (VisionProWifiRetail)
    HEAT: Final = SZ_HEAT  # not evohome (VisionProWifiRetail)
    COOL: Final = SZ_COOL  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class TcsModelType(StrEnum):
    EVO_TOUCH: Final = "EvoTouch"
    FOCUS_PRO_WIFI_RETAIL: Final = "FocusProWifiRetail"
    VISION_PRO_WIFI_RETAIL: Final = "VisionProWifiRetail"


SZ_FOLLOW_SCHEDULE: Final = "FollowSchedule"
SZ_PERMANENT_OVERRIDE: Final = "PermanentOverride"
SZ_TEMPORARY_OVERRIDE: Final = "TemporaryOverride"
SZ_VACATION_HOLD: Final = "VacationHold"


@verify(EnumCheck.UNIQUE)
class ZoneMode(StrEnum):
    FOLLOW_SCHEDULE: Final = SZ_FOLLOW_SCHEDULE
    PERMANENT_OVERRIDE: Final = SZ_PERMANENT_OVERRIDE
    TEMPORARY_OVERRIDE: Final = SZ_TEMPORARY_OVERRIDE
    VACATION_HOLD: Final = SZ_VACATION_HOLD  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class ZoneModelType(StrEnum):
    FOCUS_PRO_WIFI_RETAIL: Final = "FocusProWifiRetail"
    HEATING_ZONE: Final = "HeatingZone"
    ROUND_MODULATION: Final = "RoundModulation"
    ROUND_WIRELESS: Final = "RoundWireless"
    UNKNOWN: Final = SZ_UNKNOWN
    VISION_PRO_WIFI_RETAIL: Final = "VisionProWifiRetail"


SZ_ELECTRIC_HEAT: Final = "ElectricHeat"  # TODO: needs confirming
SZ_MIXING_VALVE: Final = "MixingValve"
SZ_RADIATOR_ZONE: Final = "RadiatorZone"
SZ_THERMOSTAT: Final = "Thermostat"
SZ_UNDERFLOOR_HEATING: Final = "UnderfloorHeating"
SZ_ZONE_VALVES: Final = "ZoneValves"  # is not ZoneValve
SZ_ZONE_TEMPERATURE_CONTROL: Final = "ZoneTemperatureControl"


@verify(EnumCheck.UNIQUE)
class ZoneType(StrEnum):
    MIXING_VALVE: Final = SZ_MIXING_VALVE
    RADIATOR_ZONE: Final = SZ_RADIATOR_ZONE
    THERMOSTAT: Final = SZ_THERMOSTAT
    UNDERFLOOR_HEATING: Final = SZ_UNDERFLOOR_HEATING
    UNKNOWN: Final = SZ_UNKNOWN
    ZONE_TEMPERATURE_CONTROL: Final = SZ_ZONE_TEMPERATURE_CONTROL
    ZONE_VALVES: Final = SZ_ZONE_VALVES


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
