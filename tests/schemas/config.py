#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Config JSON."""
from __future__ import annotations

import voluptuous as vol  # type: ignore[import]

from .const import (
    SZ_ALLOWED_MODES,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_ALLOWED_STATES,
    SZ_ALLOWED_SYSTEM_ZONES,
    SZ_CAN_BE_PERMANENT,
    SZ_CAN_BE_TEMPORARY,
    SZ_CAN_CONTROL_COOL,
    SZ_CAN_CONTROL_HEAT,
    SZ_CURRENT_OFFSET_MINUTES,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_DISPLAY_NAME,
    SZ_GATEWAYS,
    SZ_LOCATION_INFO,
    SZ_MAX_DURATION,
    SZ_MAX_HEAT_SETPOINT,
    SZ_SETPOINT_VALUE_RESOLUTION,
    SZ_MAX_SWITCHPOINTS_PER_DAY,
    SZ_MIN_HEAT_SETPOINT,
    SZ_MIN_SWITCHPOINTS_PER_DAY,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_OFFSET_MINUTES,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SUPPORTS_DAYLIGHT_SAVING,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TIME_ZONE,
    SZ_TIME_ZONE_ID,
    SZ_TIMING_MODE,
    SZ_TIMING_RESOLUTION,
    SZ_VALUE_RESOLUTION,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
    SZ_ZONES,
)


DEFAULT_SETPOINT_MODES = ["PermanentOverride", "FollowSchedule", "TemporaryOverride"]

SCH_SYSTEM_MODE_PERM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_MODE): str,
        vol.Required(SZ_CAN_BE_PERMANENT): bool,
        vol.Required(SZ_CAN_BE_TEMPORARY): bool,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_SYSTEM_MODE_TEMP = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_MODE): str,
        vol.Required(SZ_CAN_BE_PERMANENT): bool,
        vol.Required(SZ_CAN_BE_TEMPORARY): bool,
        vol.Required(SZ_MAX_DURATION): str,  # "99.00:00:00"
        vol.Required(SZ_TIMING_RESOLUTION): str,  # "1.00:00:00"
        vol.Required(SZ_TIMING_MODE): str,  # Duration, Period
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_ALLOWED_SYSTEM_MODE = vol.Any(SCH_SYSTEM_MODE_PERM, SCH_SYSTEM_MODE_TEMP)

SCH_DHW_STATE_CAPABILITIES_RESPONSE = vol.Schema(
    {
        vol.Required(SZ_ALLOWED_STATES): [str],
        vol.Required(SZ_ALLOWED_MODES): [str],
        vol.Required(SZ_MAX_DURATION): str,  # "1.00:00:00"
        vol.Required(SZ_TIMING_RESOLUTION): str,  # "00:10:00"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SCHEDULE_CAPABILITIES_RESPONSE = vol.Schema(
    {
        vol.Required(SZ_MAX_SWITCHPOINTS_PER_DAY): int,  # 6
        vol.Required(SZ_MIN_SWITCHPOINTS_PER_DAY): int,  # 1
        vol.Required(SZ_TIMING_RESOLUTION): str,  # "00:10:00"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_DHW = vol.Schema(
    {
        vol.Required(SZ_DHW_ID): str,
        vol.Required(
            SZ_DHW_STATE_CAPABILITIES_RESPONSE
        ): SCH_DHW_STATE_CAPABILITIES_RESPONSE,
        vol.Required(
            SZ_SCHEDULE_CAPABILITIES_RESPONSE
        ): SCH_SCHEDULE_CAPABILITIES_RESPONSE,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SETPOINT_CAPABILITIES = vol.Schema(
    {
        vol.Required(SZ_MAX_HEAT_SETPOINT): float,  # 35.0
        vol.Required(SZ_MIN_HEAT_SETPOINT): float,  # 5.0
        vol.Required(SZ_VALUE_RESOLUTION): float,  # 0.5
        vol.Required(SZ_CAN_CONTROL_HEAT): bool,
        vol.Required(SZ_CAN_CONTROL_COOL): bool,
        vol.Required(SZ_ALLOWED_SETPOINT_MODES): [str],
        vol.Required(SZ_MAX_DURATION): str,  # "1.00:00:00"
        vol.Required(SZ_TIMING_RESOLUTION): str,  # "00:10:00"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SCHEDULE_CAPABILITIES = SCH_SCHEDULE_CAPABILITIES_RESPONSE.extend(
    {
        vol.Required(SZ_SETPOINT_VALUE_RESOLUTION, default=0.5): float,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_ZONE = vol.Schema(
    {
        vol.Required(SZ_ZONE_ID): str,
        vol.Required(SZ_MODEL_TYPE): str,  # , default=SZ_HEATING_ZONE): str,  # ["HeatingZone", "RoundWireless", "Unknown"]
        vol.Required(SZ_SETPOINT_CAPABILITIES): SCH_SETPOINT_CAPABILITIES,
        vol.Required(SZ_SCHEDULE_CAPABILITIES): SCH_SCHEDULE_CAPABILITIES,
        vol.Required(SZ_NAME): str,
        vol.Required(SZ_ZONE_TYPE): str,  # , default=SZ_RADIATOR_ZONE): str,  # ["RadiatorZone", "Thermostat", "Unknown"]
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_TEMPERATURE_CONTROL_SYSTEM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_ID): str,
        vol.Required(SZ_MODEL_TYPE): str,  # "EvoTouch"
        vol.Required(SZ_ALLOWED_SYSTEM_ZONES): [SCH_ALLOWED_SYSTEM_MODE],
        vol.Required(SZ_ZONES): vol.All([SCH_ZONE], vol.Length(min=1, max=12)),
        vol.Optional(SZ_DHW): SCH_DHW,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GATEWAY = vol.Schema(
    {vol.Required(SZ_TEMPERATURE_CONTROL_SYSTEMS): [SCH_TEMPERATURE_CONTROL_SYSTEM]},
    extra=vol.PREVENT_EXTRA,
)

SCH_TIME_ZONE = vol.Schema(
    {
        vol.Required(SZ_TIME_ZONE_ID): str,
        vol.Required(SZ_DISPLAY_NAME): str,
        vol.Required(SZ_OFFSET_MINUTES): int,
        vol.Required(SZ_CURRENT_OFFSET_MINUTES): int,
        vol.Required(SZ_SUPPORTS_DAYLIGHT_SAVING): bool,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_LOCATION_INFO = vol.Schema(
    {
        vol.Required(SZ_TIME_ZONE): SCH_TIME_ZONE,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_CONFIG = vol.Schema(
    {
        vol.Required(SZ_LOCATION_INFO): SCH_LOCATION_INFO,
        vol.Required(SZ_GATEWAYS): [SCH_GATEWAY],
    },
    extra=vol.PREVENT_EXTRA,
)
