"""Shared constants for the vendor's TCC v2 API.

All strings are snake_case (vendor strings are camelCase, PascalCase).
"""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
from typing import Final

from _evohome.helpers import camel_to_snake

from .schemas.const import (
    TccDayOfWeek,
    TccDhwState,
    TccFanMode,
    TccFaultType,
    TccLocationType,
    TccSystemMode,
    TccTcsModelType,
    TccTimingMode,
    TccZoneMode,
    TccZoneModelType,
    TccZoneType,
)

_ERR_NOT_AVAILABLE: Final = "{} not available until after Location.update() is called"

# HDR_STRFTIME: Final = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers

# snake_case equivalents of every S2_* key in schemas/const.py.
# All are string literals; test_const.py asserts they equal camel_to_snake(S2_*).

SZ_ACTIVE_FAULTS: Final = "active_faults"
SZ_ALLOWED_FAN_MODES: Final = "allowed_fan_modes"
SZ_ALLOWED_MODES: Final = "allowed_modes"
SZ_ALLOWED_SETPOINT_MODES: Final = "allowed_setpoint_modes"
SZ_ALLOWED_STATES: Final = "allowed_states"
SZ_ALLOWED_SYSTEM_MODES: Final = "allowed_system_modes"

SZ_CAN_BE_CHANGED: Final = "can_be_changed"
SZ_CAN_BE_PERMANENT: Final = "can_be_permanent"
SZ_CAN_BE_TEMPORARY: Final = "can_be_temporary"
SZ_CAN_CONTROL_COOL: Final = "can_control_cool"
SZ_CAN_CONTROL_HEAT: Final = "can_control_heat"
SZ_CITY: Final = "city"
SZ_CODE: Final = "code"
SZ_COOL_SETPOINT: Final = "cool_setpoint"
SZ_COOL_SETPOINT_VALUE: Final = "cool_setpoint_value"
SZ_COUNTRY: Final = "country"
SZ_CRC: Final = "crc"
SZ_CURRENT_OFFSET_MINUTES: Final = "current_offset_minutes"

SZ_DAILY_SCHEDULES: Final = "daily_schedules"
SZ_DAY_OF_WEEK: Final = "day_of_week"
SZ_DHW: Final = "dhw"
SZ_DHW_ID: Final = "dhw_id"
SZ_DHW_STATE: Final = "dhw_state"
SZ_DHW_STATE_CAPABILITIES_RESPONSE: Final = "dhw_state_capabilities_response"
SZ_DISPLAY_NAME: Final = "display_name"
SZ_DOMESTIC_HOT_WATER: Final = "domestic_hot_water"
SZ_DURATION: Final = "duration"  # c.f. StrEnum val, TimingMode.DURATION

SZ_ERROR: Final = "error"

SZ_FAN_MODE: Final = "fan_mode"
SZ_FAN_STATUS: Final = "fan_status"
SZ_FAULT_TYPE: Final = "fault_type"
SZ_FIRSTNAME: Final = "firstname"

SZ_GATEWAY: Final = "gateway"
SZ_GATEWAY_ID: Final = "gateway_id"
SZ_GATEWAY_INFO: Final = "gateway_info"
SZ_GATEWAYS: Final = "gateways"

SZ_HEAT_SETPOINT: Final = "heat_setpoint"
SZ_HEAT_SETPOINT_VALUE: Final = "heat_setpoint_value"

SZ_IS_AVAILABLE: Final = "is_available"
SZ_IS_CANCELABLE: Final = "is_cancelable"
SZ_IS_CHANGEABLE: Final = "is_changeable"
SZ_IS_PERMANENT: Final = "is_permanent"
SZ_IS_WI_FI: Final = "is_wi_fi"

SZ_LANGUAGE: Final = "language"
SZ_LASTNAME: Final = "lastname"
SZ_LOCATION: Final = "location"
SZ_LOCATION_ID: Final = "location_id"
SZ_LOCATION_INFO: Final = "location_info"
SZ_LOCATION_OWNER: Final = "location_owner"
SZ_LOCATION_TYPE: Final = "location_type"

SZ_MAC: Final = "mac"
SZ_MAX_COOL_SETPOINT: Final = "max_cool_setpoint"
SZ_MAX_DURATION: Final = "max_duration"
SZ_MAX_HEAT_SETPOINT: Final = "max_heat_setpoint"
SZ_MAX_SWITCHPOINTS_PER_DAY: Final = "max_switchpoints_per_day"
SZ_MESSAGE: Final = "message"
SZ_MIN_COOL_SETPOINT: Final = "min_cool_setpoint"
SZ_MIN_DURATION: Final = "min_duration"
SZ_MIN_HEAT_SETPOINT: Final = "min_heat_setpoint"
SZ_MIN_SWITCHPOINTS_PER_DAY: Final = "min_switchpoints_per_day"
SZ_MODE: Final = "mode"
SZ_MODEL_TYPE: Final = "model_type"

SZ_NAME: Final = "name"

SZ_OFFSET_MINUTES: Final = "offset_minutes"

SZ_PERIOD: Final = "period"  # c.f. StrEnum val, TimingMode.PERIOD
SZ_PERMANENT: Final = "permanent"
SZ_POSTCODE: Final = "postcode"

SZ_SCHEDULE_CAPABILITIES: Final = "schedule_capabilities"
SZ_SCHEDULE_CAPABILITIES_RESPONSE: Final = "schedule_capabilities_response"
SZ_SETPOINT_CAPABILITIES: Final = "setpoint_capabilities"
SZ_SETPOINT_DEADBAND: Final = "setpoint_deadband"
SZ_SETPOINT_MODE: Final = "setpoint_mode"
SZ_SETPOINT_STATUS: Final = "setpoint_status"
SZ_SETPOINT_VALUE_RESOLUTION: Final = "setpoint_value_resolution"
SZ_SINCE: Final = "since"
SZ_STATE: Final = "state"
SZ_STATE_STATUS: Final = "state_status"
SZ_STREET_ADDRESS: Final = "street_address"
SZ_SUPPORTS_DAYLIGHT_SAVING: Final = "supports_daylight_saving"
SZ_SWITCHPOINTS: Final = "switchpoints"
SZ_SYSTEM_ID: Final = "system_id"
SZ_SYSTEM_MODE: Final = "system_mode"
SZ_SYSTEM_MODE_STATUS: Final = "system_mode_status"

SZ_TARGET_COOL_TEMPERATURE: Final = "target_cool_temperature"
SZ_TARGET_HEAT_TEMPERATURE: Final = "target_heat_temperature"
SZ_TEMPERATURE: Final = "temperature"
SZ_TEMPERATURE_CONTROL_SYSTEM: Final = "temperature_control_system"
SZ_TEMPERATURE_CONTROL_SYSTEMS: Final = "temperature_control_systems"
SZ_TEMPERATURE_STATUS: Final = "temperature_status"
SZ_TEMPERATURE_ZONE: Final = "temperature_zone"
SZ_TIME_OF_DAY: Final = "time_of_day"
SZ_TIME_UNTIL: Final = "time_until"
SZ_TIME_ZONE: Final = "time_zone"
SZ_TIME_ZONE_ID: Final = "time_zone_id"
SZ_TIMING_MODE: Final = "timing_mode"
SZ_TIMING_RESOLUTION: Final = "timing_resolution"

SZ_UNTIL: Final = "until"
SZ_UNTIL_TIME: Final = "until_time"
SZ_USE_DAYLIGHT_SAVE_SWITCHING: Final = "use_daylight_save_switching"
SZ_USER_ACCOUNT: Final = "user_account"
SZ_USER_ID: Final = "user_id"
SZ_USERNAME: Final = "username"

SZ_VACATION_HOLD_CAPABILITIES: Final = "vacation_hold_capabilities"
SZ_VALUE_RESOLUTION: Final = "value_resolution"

SZ_ZONE_ID: Final = "zone_id"
SZ_ZONE_TYPE: Final = "zone_type"
SZ_ZONES: Final = "zones"


# These keys are not in the vendor's schema.
SZ_ID: Final = "id"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"
SZ_THERMOSTAT: Final = "thermostat"


# These are user-facing StrEnums with snake_case values, each derived from its
# corresponding Tcc* StrEnum via camel_to_snake().


@verify(EnumCheck.UNIQUE)
class DayOfWeek(StrEnum):
    MONDAY = camel_to_snake(TccDayOfWeek.MONDAY)
    TUESDAY = camel_to_snake(TccDayOfWeek.TUESDAY)
    WEDNESDAY = camel_to_snake(TccDayOfWeek.WEDNESDAY)
    THURSDAY = camel_to_snake(TccDayOfWeek.THURSDAY)
    FRIDAY = camel_to_snake(TccDayOfWeek.FRIDAY)
    SATURDAY = camel_to_snake(TccDayOfWeek.SATURDAY)
    SUNDAY = camel_to_snake(TccDayOfWeek.SUNDAY)


@verify(EnumCheck.UNIQUE)
class DhwState(StrEnum):
    OFF = camel_to_snake(TccDhwState.OFF)
    ON = camel_to_snake(TccDhwState.ON)


@verify(EnumCheck.UNIQUE)
class FanMode(StrEnum):
    AUTO = camel_to_snake(TccFanMode.AUTO)
    ON = camel_to_snake(TccFanMode.ON)


@verify(EnumCheck.UNIQUE)
class FaultType(StrEnum):  # NOTE: This list is incomplete
    # W_A_CL = camel_to_snake(TccFaultType.DHW_A_CL)  # extrapolated
    DHW_A_FL = camel_to_snake(TccFaultType.DHW_A_FL)
    DHW_S_CL = camel_to_snake(TccFaultType.DHW_S_CL)
    DHW_S_FL = camel_to_snake(TccFaultType.DHW_S_FL)
    DHW_S_LB = camel_to_snake(TccFaultType.DHW_S_LB)  # extrapolated
    GWY_X_CL = camel_to_snake(TccFaultType.GWY_X_CL)
    SYS_B_CL = camel_to_snake(TccFaultType.SYS_B_CL)
    SYS_C_CL = camel_to_snake(TccFaultType.SYS_C_CL)
    # S_X_LB = camel_to_snake(TccFaultType.SYS_X_LB)  # extrapolated
    ZON_A_CL = camel_to_snake(TccFaultType.ZON_A_CL)
    ZON_A_LB = camel_to_snake(TccFaultType.ZON_A_LB)
    ZON_S_CL = camel_to_snake(TccFaultType.ZON_S_CL)
    ZON_S_LB = camel_to_snake(TccFaultType.ZON_S_LB)


@verify(EnumCheck.UNIQUE)
class LocationType(StrEnum):
    COMMERCIAL = camel_to_snake(TccLocationType.COMMERCIAL)
    RESIDENTIAL = camel_to_snake(TccLocationType.RESIDENTIAL)


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO = camel_to_snake(TccSystemMode.AUTO)
    AUTO_WITH_ECO = camel_to_snake(TccSystemMode.AUTO_WITH_ECO)
    AUTO_WITH_RESET = camel_to_snake(TccSystemMode.AUTO_WITH_RESET)
    AWAY = camel_to_snake(TccSystemMode.AWAY)
    CUSTOM = camel_to_snake(TccSystemMode.CUSTOM)
    DAY_OFF = camel_to_snake(TccSystemMode.DAY_OFF)
    HEATING_OFF = camel_to_snake(TccSystemMode.HEATING_OFF)
    OFF = camel_to_snake(TccSystemMode.OFF)  # not seen with Evohome
    HEAT = camel_to_snake(TccSystemMode.HEAT)  # not seen with Evohome
    COOL = camel_to_snake(TccSystemMode.COOL)  # not seen with Evohome


@verify(EnumCheck.UNIQUE)
class TcsModelType(StrEnum):
    EVO_TOUCH = camel_to_snake(TccTcsModelType.EVO_TOUCH)
    FOCUS_PRO_WIFI_RETAIL = camel_to_snake(TccTcsModelType.FOCUS_PRO_WIFI_RETAIL)
    SYDNEY = camel_to_snake(TccTcsModelType.SYDNEY)  # not seen with Evohome
    VISION_PRO_WIFI_RETAIL = camel_to_snake(TccTcsModelType.VISION_PRO_WIFI_RETAIL)


@verify(EnumCheck.UNIQUE)
class TimingMode(StrEnum):  # c.f. JSON keys: SZ_DURATION, SZ_PERIOD
    DURATION = camel_to_snake(TccTimingMode.DURATION)
    PERIOD = camel_to_snake(TccTimingMode.PERIOD)


@verify(EnumCheck.UNIQUE)
class ZoneMode(StrEnum):
    FOLLOW_SCHEDULE = camel_to_snake(TccZoneMode.FOLLOW_SCHEDULE)
    PERMANENT_OVERRIDE = camel_to_snake(TccZoneMode.PERMANENT_OVERRIDE)
    TEMPORARY_OVERRIDE = camel_to_snake(TccZoneMode.TEMPORARY_OVERRIDE)
    VACATION_HOLD = camel_to_snake(TccZoneMode.VACATION_HOLD)  # not seen with Evohome


@verify(EnumCheck.UNIQUE)
class ZoneModelType(StrEnum):
    FOCUS_PRO_WIFI_RETAIL = camel_to_snake(TccZoneModelType.FOCUS_PRO_WIFI_RETAIL)
    HEATING_ZONE = camel_to_snake(TccZoneModelType.HEATING_ZONE)
    ROUND_MODULATION = camel_to_snake(TccZoneModelType.ROUND_MODULATION)
    ROUND_WIRELESS = camel_to_snake(TccZoneModelType.ROUND_WIRELESS)
    SYDNEY = camel_to_snake(TccZoneModelType.SYDNEY)  # not seen with Evohome
    UNKNOWN = camel_to_snake(TccZoneModelType.UNKNOWN)
    VISION_PRO_WIFI_RETAIL = camel_to_snake(TccZoneModelType.VISION_PRO_WIFI_RETAIL)


@verify(EnumCheck.UNIQUE)
class ZoneType(StrEnum):
    ELECTRIC_HEAT = camel_to_snake(TccZoneType.ELECTRIC_HEAT)
    MIXING_VALVE = camel_to_snake(TccZoneType.MIXING_VALVE)
    RADIATOR_ZONE = camel_to_snake(TccZoneType.RADIATOR_ZONE)
    THERMOSTAT = camel_to_snake(TccZoneType.THERMOSTAT)
    UNDERFLOOR_HEATING = camel_to_snake(TccZoneType.UNDERFLOOR_HEATING)
    UNKNOWN = camel_to_snake(TccZoneType.UNKNOWN)
    ZONE_TEMPERATURE_CONTROL = camel_to_snake(TccZoneType.ZONE_TEMPERATURE_CONTROL)
    ZONE_VALVES = camel_to_snake(TccZoneType.ZONE_VALVES)
