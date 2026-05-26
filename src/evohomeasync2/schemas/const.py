"""evohomeasync schema - shared constants."""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import Final

# Various useful regex forms
REGEX_DHW_ID: Final = r"[0-9]*"
REGEX_GATEWAY_ID: Final = r"[0-9]*"
REGEX_LOCATION_ID: Final = r"[0-9]*"
REGEX_SYSTEM_ID: Final = r"[0-9]*"
REGEX_ZONE_ID: Final = r"[0-9]*"

# Datetime format used by the vendor's API
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"


# These are vendor constants (camelCase), used for keys in the vendor's schema.

S2_ACTIVE_FAULTS: Final = "activeFaults"
S2_ALLOWED_FAN_MODES: Final = "allowedFanModes"
S2_ALLOWED_MODES: Final = "allowedModes"
S2_ALLOWED_SETPOINT_MODES: Final = "allowedSetpointModes"
S2_ALLOWED_STATES: Final = "allowedStates"
S2_ALLOWED_SYSTEM_MODES: Final = "allowedSystemModes"

S2_CAN_BE_PERMANENT: Final = "canBePermanent"
S2_CAN_BE_CHANGED: Final = "canBeChanged"
S2_CAN_BE_TEMPORARY: Final = "canBeTemporary"
S2_CAN_CONTROL_COOL: Final = "canControlCool"
S2_CAN_CONTROL_HEAT: Final = "canControlHeat"
S2_CITY: Final = "city"
S2_COOL_SETPOINT: Final = "coolSetpoint"
S2_COOL_SETPOINT_VALUE: Final = "coolSetpointValue"  # extrapolated
S2_COUNTRY: Final = "country"
S2_CRC: Final = "crc"
S2_CURRENT_OFFSET_MINUTES: Final = "currentOffsetMinutes"

S2_DAILY_SCHEDULES: Final = "dailySchedules"
S2_DAY_OF_WEEK: Final = "dayOfWeek"
S2_DHW: Final = "dhw"
S2_DHW_ID: Final = "dhwId"
S2_DHW_STATE: Final = "dhwState"
S2_DHW_STATE_CAPABILITIES_RESPONSE: Final = "dhwStateCapabilitiesResponse"
S2_DISPLAY_NAME: Final = "displayName"

S2_FAN_MODE: Final = "fanMode"
S2_FAN_STATUS: Final = "fanStatus"
S2_FAULT_TYPE: Final = "faultType"
S2_FIRSTNAME: Final = "firstname"

S2_GATEWAY_ID: Final = "gatewayId"
S2_GATEWAY_INFO: Final = "gatewayInfo"
S2_GATEWAYS: Final = "gateways"

S2_HEAT_SETPOINT: Final = "heatSetpoint"
S2_HEAT_SETPOINT_VALUE: Final = "heatSetpointValue"

S2_IS_AVAILABLE: Final = "isAvailable"
S2_IS_CANCELABLE: Final = "isCancelable"
S2_IS_CHANGEABLE: Final = "isChangeable"
S2_IS_PERMANENT: Final = "isPermanent"
S2_IS_WI_FI: Final = "isWiFi"

S2_LANGUAGE: Final = "language"
S2_LASTNAME: Final = "lastname"
S2_LOCATION_ID: Final = "locationId"
S2_LOCATION_INFO: Final = "locationInfo"
S2_LOCATION_OWNER: Final = "locationOwner"
S2_LOCATION_TYPE: Final = "locationType"

S2_MAC: Final = "mac"
S2_MAX_COOL_SETPOINT: Final = "maxCoolSetpoint"  # extrapolated
S2_MAX_DURATION: Final = "maxDuration"
S2_MAX_HEAT_SETPOINT: Final = "maxHeatSetpoint"
S2_MAX_SWITCHPOINTS_PER_DAY: Final = "maxSwitchpointsPerDay"
S2_MIN_COOL_SETPOINT: Final = "minCoolSetpoint"
S2_MIN_DURATION: Final = "minDuration"
S2_MIN_HEAT_SETPOINT: Final = "minHeatSetpoint"
S2_MIN_SWITCHPOINTS_PER_DAY: Final = "minSwitchpointsPerDay"
S2_MODE: Final = "mode"
S2_MODEL_TYPE: Final = "modelType"

S2_NAME: Final = "name"

S2_OFFSET_MINUTES: Final = "offsetMinutes"

S2_PERMANENT: Final = "permanent"
S2_POSTCODE: Final = "postcode"

S2_SCHEDULE_CAPABILITIES: Final = "scheduleCapabilities"
S2_SCHEDULE_CAPABILITIES_RESPONSE: Final = "scheduleCapabilitiesResponse"
S2_SETPOINT_CAPABILITIES: Final = "setpointCapabilities"
S2_SETPOINT_DEADBAND: Final = "setpointDeadband"
S2_SETPOINT_MODE: Final = "setpointMode"
S2_SETPOINT_STATUS: Final = "setpointStatus"
S2_SETPOINT_VALUE_RESOLUTION: Final = "setpointValueResolution"
S2_SINCE: Final = "since"
S2_STATE: Final = "state"
S2_STATE_STATUS: Final = "stateStatus"
S2_STREET_ADDRESS: Final = "streetAddress"
S2_SUPPORTS_DAYLIGHT_SAVING: Final = "supportsDaylightSaving"
S2_SWITCHPOINTS: Final = "switchpoints"
S2_SYSTEM_ID: Final = "systemId"
S2_SYSTEM_MODE: Final = "systemMode"
S2_SYSTEM_MODE_STATUS: Final = "systemModeStatus"

S2_TARGET_COOL_TEMPERATURE: Final = "targetCoolTemperature"  # extrapolated
S2_TARGET_HEAT_TEMPERATURE: Final = "targetHeatTemperature"
S2_TEMPERATURE: Final = "temperature"
S2_TEMPERATURE_CONTROL_SYSTEMS: Final = "temperatureControlSystems"
S2_TEMPERATURE_STATUS: Final = "temperatureStatus"
S2_TIME_OF_DAY: Final = "timeOfDay"
S2_TIME_UNTIL: Final = "timeUntil"
S2_TIME_ZONE: Final = "timeZone"
S2_TIME_ZONE_ID: Final = "timeZoneId"
S2_TIMING_MODE: Final = "timingMode"
S2_TIMING_RESOLUTION: Final = "timingResolution"

S2_UNTIL: Final = "until"
S2_UNTIL_TIME: Final = "untilTime"
S2_USE_DAYLIGHT_SAVE_SWITCHING: Final = "useDaylightSaveSwitching"
S2_USER_ACCOUNT: Final = "userAccount"
S2_USER_ID: Final = "userId"
S2_USERNAME: Final = "username"

S2_VACATION_HOLD_CAPABILITIES: Final = "vacationHoldCapabilities"
S2_VALUE_RESOLUTION: Final = "valueResolution"

S2_ZONE_ID: Final = "zoneId"
S2_ZONE_TYPE: Final = "zoneType"
S2_ZONES: Final = "zones"


# These are vendor constants (camelCase), used as URL path components (not JSON keys).
# Each group is placed just before the StrEnum that uses it.

S2_DOMESTIC_HOT_WATER: Final = "domesticHotWater"
S2_GATEWAY: Final = "gateway"
S2_LOCATION: Final = "location"
S2_TEMPERATURE_CONTROL_SYSTEM: Final = "temperatureControlSystem"
S2_TEMPERATURE_ZONE: Final = "temperatureZone"


@verify(EnumCheck.UNIQUE)
class TccEntityType(StrEnum):
    LOC = S2_LOCATION
    GWY = S2_GATEWAY
    TCS = S2_TEMPERATURE_CONTROL_SYSTEM
    ZON = S2_TEMPERATURE_ZONE
    DHW = S2_DOMESTIC_HOT_WATER


# These are vendor constants (PascalCase), used for values in the vendor's schema.
# Generally, each group is placed just before the StrEnum that uses it.

S2_MONDAY: Final = "Monday"
S2_TUESDAY: Final = "Tuesday"
S2_WEDNESDAY: Final = "Wednesday"
S2_THURSDAY: Final = "Thursday"
S2_FRIDAY: Final = "Friday"
S2_SATURDAY: Final = "Saturday"
S2_SUNDAY: Final = "Sunday"


@verify(EnumCheck.UNIQUE)
class TccDayOfWeek(StrEnum):
    MONDAY = S2_MONDAY
    TUESDAY = S2_TUESDAY
    WEDNESDAY = S2_WEDNESDAY
    THURSDAY = S2_THURSDAY
    FRIDAY = S2_FRIDAY
    SATURDAY = S2_SATURDAY
    SUNDAY = S2_SUNDAY


S2_OFF: Final = "Off"
S2_ON: Final = "On"


@verify(EnumCheck.UNIQUE)
class TccDhwState(StrEnum):
    OFF = S2_OFF
    ON = S2_ON


S2_AUTO: Final = "Auto"


@verify(EnumCheck.UNIQUE)
class TccFanMode(StrEnum):
    AUTO = S2_AUTO
    ON = S2_ON


@verify(EnumCheck.UNIQUE)
class TccFaultType(StrEnum):  # NOTE: This list is incomplete
    SYS_B_CL = "BoilerCommunicationLost"
    SYS_C_CL = "ChValveCommunicationLost"
    DHW_A_FL = "DHWActuatorFailure"
    # W_A_CL = "DHWActuatorCommunicationLost"  # extrapolated
    DHW_S_CL = "DHWSensorCommunicationLost"
    DHW_S_FL = "DHWSensorFailure"
    DHW_S_LB = "DHWSensorLowBattery"  # extrapolated
    GWY_X_CL = "GatewayCommunicationLost"
    # S_X_LB = "TemperatureControlSystemLowBattery"  # extrapolated
    ZON_A_CL = "TempZoneActuatorCommunicationLost"
    ZON_A_LB = "TempZoneActuatorLowBattery"
    ZON_S_CL = "TempZoneSensorCommunicationLost"
    ZON_S_LB = "TempZoneSensorLowBattery"


@verify(EnumCheck.UNIQUE)
class TccLocationType(StrEnum):
    COMMERCIAL = "Commercial"
    RESIDENTIAL = "Residential"


S2_AUTO_WITH_ECO: Final = "AutoWithEco"
S2_AUTO_WITH_RESET: Final = "AutoWithReset"
S2_AWAY: Final = "Away"
S2_COOL: Final = "Cool"
S2_CUSTOM: Final = "Custom"
S2_DAY_OFF: Final = "DayOff"
S2_HEAT: Final = "Heat"
S2_HEATING_OFF: Final = "HeatingOff"


@verify(EnumCheck.UNIQUE)
class TccSystemMode(StrEnum):
    AUTO = S2_AUTO
    AUTO_WITH_ECO = S2_AUTO_WITH_ECO
    AUTO_WITH_RESET = S2_AUTO_WITH_RESET
    AWAY = S2_AWAY
    CUSTOM = S2_CUSTOM
    DAY_OFF = S2_DAY_OFF
    HEATING_OFF = S2_HEATING_OFF
    OFF = S2_OFF  # not evohome (VisionProWifiRetail)
    HEAT = S2_HEAT  # not evohome (VisionProWifiRetail)
    COOL = S2_COOL  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class TccTcsModelType(StrEnum):
    EVO_TOUCH = "EvoTouch"
    FOCUS_PRO_WIFI_RETAIL = "FocusProWifiRetail"
    VISION_PRO_WIFI_RETAIL = "VisionProWifiRetail"


S2_FOLLOW_SCHEDULE: Final = "FollowSchedule"
S2_PERMANENT_OVERRIDE: Final = "PermanentOverride"
S2_TEMPORARY_OVERRIDE: Final = "TemporaryOverride"
S2_VACATION_HOLD: Final = "VacationHold"


@verify(EnumCheck.UNIQUE)
class TccZoneMode(StrEnum):
    FOLLOW_SCHEDULE = S2_FOLLOW_SCHEDULE
    PERMANENT_OVERRIDE = S2_PERMANENT_OVERRIDE
    TEMPORARY_OVERRIDE = S2_TEMPORARY_OVERRIDE
    VACATION_HOLD = S2_VACATION_HOLD  # not evohome (VisionProWifiRetail)


S2_DURATION: Final = "Duration"
S2_HEATING_ZONE: Final = "HeatingZone"
S2_PERIOD: Final = "Period"
S2_UNKNOWN: Final = "Unknown"


@verify(EnumCheck.UNIQUE)
class TccZoneModelType(StrEnum):
    FOCUS_PRO_WIFI_RETAIL = "FocusProWifiRetail"
    HEATING_ZONE = "HeatingZone"
    ROUND_MODULATION = "RoundModulation"
    ROUND_WIRELESS = "RoundWireless"
    UNKNOWN = S2_UNKNOWN
    VISION_PRO_WIFI_RETAIL = "VisionProWifiRetail"


S2_ELECTRIC_HEAT: Final = "ElectricHeat"  # TODO: needs confirming
S2_MIXING_VALVE: Final = "MixingValve"
S2_RADIATOR_ZONE: Final = "RadiatorZone"
S2_THERMOSTAT: Final = "Thermostat"
S2_UNDERFLOOR_HEATING: Final = "UnderfloorHeating"
S2_ZONE_TEMPERATURE_CONTROL: Final = "ZoneTemperatureControl"
S2_ZONE_VALVES: Final = "ZoneValves"  # is not ZoneValve


@verify(EnumCheck.UNIQUE)
class TccZoneType(StrEnum):
    MIXING_VALVE = S2_MIXING_VALVE
    RADIATOR_ZONE = S2_RADIATOR_ZONE
    THERMOSTAT = S2_THERMOSTAT
    UNDERFLOOR_HEATING = S2_UNDERFLOOR_HEATING
    UNKNOWN = S2_UNKNOWN
    ZONE_TEMPERATURE_CONTROL = S2_ZONE_TEMPERATURE_CONTROL
    ZONE_VALVES = S2_ZONE_VALVES
