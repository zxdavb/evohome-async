#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from typing import Final

from .schema import DhwState as DhwState, SystemMode as SystemMode, ZoneMode as ZoneMode

# HDR_STRFTIME: Final = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"  # used by API


# snake_case equivalents of schema strings
SZ_COUNTRY: Final = "country"
SZ_GATEWAY_ID: Final = "gateway_id"
SZ_GATEWAY_INFO: Final = "gateway_info"
SZ_GATEWAYS: Final = "gateways"
SZ_LOCATION_ID: Final = "location_id"
SZ_LOCATION_INFO: Final = "location_info"
SZ_LOCATION_OWNER: Final = "location_owner"
SZ_MAC: Final = "mac"
SZ_NAME: Final = "name"
SZ_SYSTEM_ID: Final = "system_id"
SZ_TEMPERATURE_CONTROL_SYSTEMS: Final = "temperature_control_systems"
SZ_TIME_ZONE: Final = "time_zone"
SZ_USE_DAYLIGHT_SAVE_SWITCHING: Final = "use_daylight_save_switching"
SZ_USER_ID: Final = "user_id"


# These snake_case equivalents of schema strings
SZ_PERMANENT: Final = "permanent"
SZ_SYSTEM_MODE: Final = "system_mode"


SZ_ID: Final = "id"
SZ_IS_AVAILABLE: Final = "is_available"
SZ_MAX_HEAT_SETPOINT: Final = "max_heat_setpoint"
SZ_MIN_HEAT_SETPOINT: Final = "min_heat_setpoint"
SZ_MODE: Final = "mode"
SZ_TEMP: Final = "temp"
SZ_TEMPERATURE: Final = "temperature"
SZ_THERMOSTAT: Final = "thermostat"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"
SZ_SETPOINT_MODE: Final = "setpoint_mode"
SZ_TARGET_COOL_TEMPERATURE: Final = "target_cool_temperature"
SZ_TARGET_HEAT_TEMPERATURE: Final = "target_heat_temperature"
