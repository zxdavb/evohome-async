#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API JSON."""
from __future__ import annotations

import voluptuous as vol  # type: ignore[import]

# constants

SZ_SYSTEM_MODE = "systemMode"
SZ_CAN_BE_PERMANENT = "canBePermanent"
SZ_CAN_BE_TEMPORARY = "canBeTemporary"
SZ_MAX_DURATION = "maxDuration"
SZ_TIMING_RESOLUTION = "timingResolution"
SZ_TIMING_MODE = "timingMode"

SZ_ALLOWED_SETPOINT_MODES = "allowedSetpointModes"
SZ_CAN_CONTROL_COOL = "canControlCool"
SZ_CAN_CONTROL_HEAT = "canControlHeat"
SZ_MAX_HEAT_SETPOINT = "maxHeatSetpoint"
SZ_MIN_HEAT_SETPOINT = "minHeatSetpoint"
SZ_VALUE_RESOLUTION = "valueResolution"

DEFAULT_SETPOINT_MODES = ["PermanentOverride", "FollowSchedule", "TemporaryOverride"]

SZ_MAX_SWITCHPOINTS_PER_DAY = "maxSwitchpointsPerDay"
SZ_MIN_SWITCHPOINTS_PER_DAY = "minSwitchpointsPerDay"
SZ_SETPOINT_VALUE_RESOLUTION = "setpointValueResolution"

SZ_HEATING_ZONE = "HeatingZone"
SZ_RADIATOR_ZONE = "RadiatorZone"

SZ_ZONE_ID = "zoneId"
SZ_MODEL_TYPE = "modelType"
SZ_SETPONT_CAPABILITIES = "setpointCapabilities"
SZ_SCHEDULE_CAPABILITIES = "scheduleCapabilities"
SZ_NAME = "name"
SZ_ZONE_TYPE = "zoneType"

SZ_ALLOWED_SYSTEM_ZONES = "allowedSystemModes"
SZ_MODEL_TYPE = "modelType"
SZ_SYSTEM_ID = "systemId"
SZ_ZONES = "zones"

SZ_TEMPERATURE_CONTROL_SYSTEMS = "temperatureControlSystems"

SZ_TIME_ZONE_ID = "timeZoneId"
SZ_DISPLAY_NAME = "displayName"
SZ_OFFSET_MINUTES = "offsetMinutes"
SZ_CURRENT_OFFSET_MINUTES = "currentOffsetMinutes"
SZ_SUPPORTS_DAYLIGHT_SAVING = "supportsDaylightSaving"

SZ_TIME_ZONE = "timeZone"

SZ_LOCATION_INFO = "locationInfo"
SZ_GATEWAYS = "gateways"

# schemas

SCH_SYSTEM_MODE_PERM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_MODE): str,
        vol.Required(SZ_CAN_BE_PERMANENT, default=True): bool,
        vol.Required(SZ_CAN_BE_TEMPORARY, default=False): bool,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_SYSTEM_MODE_TEMP = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_MODE): str,
        vol.Required(SZ_CAN_BE_PERMANENT, default=True): bool,
        vol.Required(SZ_CAN_BE_TEMPORARY, default=True): bool,
        vol.Required(SZ_MAX_DURATION, default="99.00:00:00"): str,
        vol.Required(SZ_TIMING_RESOLUTION, default="1.00:00:00"): str,
        vol.Required(SZ_TIMING_MODE, default="Duration"): str,  # Duration, Period
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_ALLOWED_SYSTEM_MODE = vol.Any(SCH_SYSTEM_MODE_PERM, SCH_SYSTEM_MODE_TEMP)

SCH_SETPOINT_CAPABILITIES = vol.Schema(
    {
        vol.Required(SZ_MAX_HEAT_SETPOINT, default=35.0): float,
        vol.Required(SZ_MIN_HEAT_SETPOINT, default=5.0): float,
        vol.Required(SZ_VALUE_RESOLUTION, default=0.5): float,
        vol.Required(SZ_CAN_CONTROL_HEAT, default=True): bool,
        vol.Required(SZ_CAN_CONTROL_COOL, default=False): bool,
        vol.Required(SZ_ALLOWED_SETPOINT_MODES, default=DEFAULT_SETPOINT_MODES): list,
        vol.Required(SZ_MAX_DURATION, default="1.00:00:00"): str,
        vol.Required(SZ_TIMING_RESOLUTION, default="00:10:00"): str,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_SCHEDULE_CAPABILITIES = vol.Schema(
    {
        vol.Required(SZ_MAX_SWITCHPOINTS_PER_DAY, default=6): int,
        vol.Required(SZ_MIN_SWITCHPOINTS_PER_DAY, default=1): int,
        vol.Required(SZ_TIMING_RESOLUTION, default="00:10:00"): str,
        vol.Required(SZ_SETPOINT_VALUE_RESOLUTION, default=0.5): float,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_ZONE = vol.Schema(
    {
        vol.Required(SZ_ZONE_ID): str,
        vol.Required(SZ_MODEL_TYPE): str,  # , default=SZ_HEATING_ZONE): str,
        vol.Required(SZ_SETPONT_CAPABILITIES): SCH_SETPOINT_CAPABILITIES,
        vol.Required(SZ_SCHEDULE_CAPABILITIES): SCH_SCHEDULE_CAPABILITIES,
        vol.Required(SZ_NAME): str,
        vol.Required(SZ_ZONE_TYPE): str,  # , default=SZ_RADIATOR_ZONE): str,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: does this apply to DHW?

SCH_TEMPERATURE_CONTROL_SYSTEM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_ID): str,
        vol.Required(SZ_MODEL_TYPE): str,  # "EvoTouch"
        vol.Required(SZ_ZONES): vol.All([SCH_ZONE], vol.Length(min=1, max=12)),
        vol.Required(SZ_ALLOWED_SYSTEM_ZONES): [SCH_ALLOWED_SYSTEM_MODE],
    }
)

SCH_GATEWAY = vol.Schema(
    {vol.Required(SZ_TEMPERATURE_CONTROL_SYSTEMS): [SCH_TEMPERATURE_CONTROL_SYSTEM]}
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
