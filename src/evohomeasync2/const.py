#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from typing import Final

from .schema import DhwState as DhwState, SystemMode as SystemMode, ZoneMode as ZoneMode

# HDR_STRFTIME: Final = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"  # used by API


# These snake_case equivalents of schema strings
SZ_PERMANENT: Final = "permanent"
SZ_SYSTEM_MODE: Final = "system_mode"
# SZ_USER_ID: Final = "user_id"


SZ_ID: Final = "id"
SZ_MODE: Final = "mode"
SZ_NAME: Final = "name"
SZ_TEMP: Final = "temp"
SZ_THERMOSTAT: Final = "thermostat"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"
SZ_SETPOINT_MODE: Final = "setpoint_mode"
SZ_TARGET_COOL_TEMPERATURE: Final = "target_cool_temperature"
SZ_TARGET_HEAT_TEMPERATURE: Final = "target_heat_temperature"
