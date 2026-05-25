"""evohomeasync schema - shared constants."""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import Final

from _evohome.helpers import camel_to_snake

# Various useful regex forms
REGEX_DHW_ID: Final = r"[0-9]*"
REGEX_GATEWAY_ID: Final = r"[0-9]*"
REGEX_LOCATION_ID: Final = r"[0-9]*"
REGEX_SYSTEM_ID: Final = r"[0-9]*"
REGEX_ZONE_ID: Final = r"[0-9]*"

# Datetime format used by the vendor's API
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"


# These are vendor constants, used for keys in the vendor's schema
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
S2_MAX_COOL_SETPOINT: Final = "maxCoolSetpoint"  # an extrapolation
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

S2_TARGET_COOL_TEMPERATURE: Final = "targetCoolTemperature"  # an extrapolation
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
S2_USE_DAYLIGHT_SAVE_SWITCHING: Final = "useDaylightSaveSwitching"
S2_USER_ID: Final = "userId"
S2_USERNAME: Final = "username"

S2_VACATION_HOLD_CAPABILITIES: Final = "vacationHoldCapabilities"
S2_VALUE_RESOLUTION: Final = "valueResolution"

S2_ZONE_ID: Final = "zoneId"
S2_ZONE_TYPE: Final = "zoneType"
S2_ZONES: Final = "zones"


#
# These are vendor constants, used for API calls

S2_DOMESTIC_HOT_WATER: Final = "domesticHotWater"
S2_GATEWAY: Final = "gateway"
S2_LOCATION: Final = "location"
S2_TEMPERATURE_CONTROL_SYSTEM: Final = "temperatureControlSystem"
S2_TEMPERATURE_ZONE: Final = "temperatureZone"
S2_USER_ACCOUNT: Final = "userAccount"

S2_COOL_SETPOINT_VALUE: Final = "coolSetpointValue"  # an extrapolation
S2_HEAT_SETPOINT_VALUE: Final = "heatSetpointValue"

S2_PERMANENT: Final = "permanent"
S2_UNTIL_TIME: Final = "untilTime"

# These are vendor-specific constants, used for values
S2_DURATION: Final = "Duration"
S2_HEATING_ZONE: Final = "HeatingZone"
S2_PERIOD: Final = "Period"
S2_UNKNOWN: Final = "Unknown"

#
S2_MONDAY: Final = "Monday"
S2_TUESDAY: Final = "Tuesday"
S2_WEDNESDAY: Final = "Wednesday"
S2_THURSDAY: Final = "Thursday"
S2_FRIDAY: Final = "Friday"
S2_SATURDAY: Final = "Saturday"
S2_SUNDAY: Final = "Sunday"


@verify(EnumCheck.UNIQUE)
class DayOfWeek(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


DAYS_OF_WEEK: Final = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


S2_OFF: Final = "Off"
S2_ON: Final = "On"


S2_AUTO: Final = "Auto"
S2_AUTO_WITH_ECO: Final = "AutoWithEco"
S2_AUTO_WITH_RESET: Final = "AutoWithReset"
S2_AWAY: Final = "Away"
S2_CUSTOM: Final = "Custom"
S2_DAY_OFF: Final = "DayOff"
S2_HEATING_OFF: Final = "HeatingOff"

S2_COOL: Final = "Cool"
S2_HEAT: Final = "Heat"


@verify(EnumCheck.UNIQUE)
class DhwState(StrEnum):
    OFF = "off"
    ON = "on"


@verify(EnumCheck.UNIQUE)
class FanMode(StrEnum):
    AUTO = "auto"
    ON = "on"


@verify(EnumCheck.UNIQUE)
class FaultType(StrEnum):  # NOTE: This list is incomplete
    SYS_B_CL = "boiler_communication_lost"
    SYS_C_CL = "ch_valve_communication_lost"
    DHW_A_FL = "dhw_actuator_failure"
    # W_A_CL = "dhw_actuator_communication_lost"  # extrapolated
    DHW_S_CL = "dhw_sensor_communication_lost"
    DHW_S_FL = "dhw_sensor_failure"
    DHW_S_LB = "dhw_sensor_low_battery"  # extrapolated
    GWY_X_CL = "gateway_communication_lost"
    # S_X_LB = "temperature_control_system_low_battery"  # extrapolated
    ZON_A_CL = "temp_zone_actuator_communication_lost"
    ZON_A_LB = "temp_zone_actuator_low_battery"
    ZON_S_CL = "temp_zone_sensor_communication_lost"
    ZON_S_LB = "temp_zone_sensor_low_battery"


@verify(EnumCheck.UNIQUE)
class LocationType(StrEnum):
    COMMERCIAL = "commercial"
    RESIDENTIAL = "residential"


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO = "auto"
    AUTO_WITH_ECO = "auto_with_eco"
    AUTO_WITH_RESET = "auto_with_reset"
    AWAY = "away"
    CUSTOM = "custom"
    DAY_OFF = "day_off"
    HEATING_OFF = "heating_off"
    OFF = "off"  # not evohome (VisionProWifiRetail)
    HEAT = "heat"  # not evohome (VisionProWifiRetail)
    COOL = "cool"  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class EntityType(StrEnum):
    LOC = S2_LOCATION
    GWY = S2_GATEWAY
    TCS = S2_TEMPERATURE_CONTROL_SYSTEM
    ZON = S2_TEMPERATURE_ZONE
    DHW = S2_DOMESTIC_HOT_WATER


@verify(EnumCheck.UNIQUE)
class TcsModelType(StrEnum):
    EVO_TOUCH = "evo_touch"
    FOCUS_PRO_WIFI_RETAIL = "focus_pro_wifi_retail"
    VISION_PRO_WIFI_RETAIL = "vision_pro_wifi_retail"


S2_FOLLOW_SCHEDULE = "FollowSchedule"
S2_PERMANENT_OVERRIDE = "PermanentOverride"
S2_TEMPORARY_OVERRIDE = "TemporaryOverride"
S2_VACATION_HOLD = "VacationHold"


@verify(EnumCheck.UNIQUE)
class ZoneMode(StrEnum):
    FOLLOW_SCHEDULE = "follow_schedule"
    PERMANENT_OVERRIDE = "permanent_override"
    TEMPORARY_OVERRIDE = "temporary_override"
    VACATION_HOLD = "vacation_hold"  # not evohome (VisionProWifiRetail)


@verify(EnumCheck.UNIQUE)
class ZoneModelType(StrEnum):
    FOCUS_PRO_WIFI_RETAIL = "focus_pro_wifi_retail"
    HEATING_ZONE = "heating_zone"
    ROUND_MODULATION = "round_modulation"
    ROUND_WIRELESS = "round_wireless"
    UNKNOWN = "unknown"
    VISION_PRO_WIFI_RETAIL = "vision_pro_wifi_retail"


S2_ELECTRIC_HEAT = "ElectricHeat"  # TODO: needs confirming
S2_MIXING_VALVE = "MixingValve"
S2_RADIATOR_ZONE = "RadiatorZone"
S2_THERMOSTAT = "Thermostat"
S2_UNDERFLOOR_HEATING = "UnderfloorHeating"
S2_ZONE_VALVES = "ZoneValves"  # is not ZoneValve
S2_ZONE_TEMPERATURE_CONTROL = "ZoneTemperatureControl"


@verify(EnumCheck.UNIQUE)
class ZoneType(StrEnum):
    MIXING_VALVE = "mixing_valve"
    RADIATOR_ZONE = "radiator_zone"
    THERMOSTAT = "thermostat"
    UNDERFLOOR_HEATING = "underfloor_heating"
    UNKNOWN = "unknown"
    ZONE_TEMPERATURE_CONTROL = "zone_temperature_control"
    ZONE_VALVES = "zone_valves"


# Vendor-cased strings for all enum values appearing in vendor API responses.
# Used to build the vendor↔internal value conversion maps in auth.py and in
# schema factories when validating raw vendor payloads (TCC_GET_* schemas).
KNOWN_VENDOR_VALUES: Final[frozenset[str]] = frozenset(
    {
        # DayOfWeek
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        # DhwState
        "Off",
        "On",
        # FanMode (Auto; On already above)
        "Auto",
        # FaultType
        "BoilerCommunicationLost",
        "ChValveCommunicationLost",
        "DHWActuatorFailure",
        "DHWSensorCommunicationLost",
        "DHWSensorFailure",
        "DHWSensorLowBattery",
        "GatewayCommunicationLost",
        "TempZoneActuatorCommunicationLost",
        "TempZoneActuatorLowBattery",
        "TempZoneSensorCommunicationLost",
        "TempZoneSensorLowBattery",
        # LocationType
        "Commercial",
        "Residential",
        # SystemMode (Auto, Off already above)
        "AutoWithEco",
        "AutoWithReset",
        "Away",
        "Custom",
        "DayOff",
        "HeatingOff",
        "Heat",
        "Cool",
        # TcsModelType
        "EvoTouch",
        "FocusProWifiRetail",
        "VisionProWifiRetail",
        # ZoneMode
        "FollowSchedule",
        "PermanentOverride",
        "TemporaryOverride",
        "VacationHold",
        # ZoneModelType (FocusProWifiRetail, VisionProWifiRetail already above)
        "HeatingZone",
        "RoundModulation",
        "RoundWireless",
        "Unknown",
        # ZoneType (Unknown already above)
        "MixingValve",
        "RadiatorZone",
        "Thermostat",
        "UnderfloorHeating",
        "ZoneTemperatureControl",
        "ZoneValves",
    }
)

# Internal snake_case → vendor-cased mapping (inverse of camel_to_snake over vendor values).
INTERNAL_TO_VENDOR: Final[dict[str, str]] = {
    camel_to_snake(v): v for v in KNOWN_VENDOR_VALUES
}
