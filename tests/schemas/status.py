#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Config JSON."""
from __future__ import annotations

import voluptuous as vol  # type: ignore[import]

from .const import (
    SZ_ACTIVE_FAULTS,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_FAULT_TYPE,
    SZ_GATEWAY_ID,
    SZ_GATEWAYS,
    SZ_IS_AVAILABLE,
    SZ_IS_PERMANENT,
    SZ_LOCATION_ID,
    SZ_MODE,
    SZ_NAME,
    SZ_SETPOINT_MODE,
    SZ_SETPOINT_STATUS,
    SZ_SINCE,
    SZ_STATE,
    SZ_STATE_STATUS,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TEMPERATURE_STATUS,
    SZ_ZONE_ID,
    SZ_ZONES,
)

SCH_ACTIVE_FAULT = vol.Schema(
    {
        vol.Required(SZ_FAULT_TYPE): str,
        vol.Required(SZ_SINCE): str,  # "2023-10-09T01:45:04"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_TEMPERATURE_STATUS = vol.Schema(
    {
        vol.Required(SZ_IS_AVAILABLE): bool,
        vol.Optional(SZ_TEMPERATURE): float,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SETPOINT_STATUS = vol.Schema(
    {
        vol.Required(SZ_TARGET_HEAT_TEMPERATURE): float,
        vol.Required(SZ_SETPOINT_MODE): str,  # "PermanentOverride"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_ZONE = vol.Schema(
    {
        vol.Required(SZ_ZONE_ID): str,
        vol.Required(SZ_NAME): str,
        vol.Required(SZ_TEMPERATURE_STATUS): SCH_TEMPERATURE_STATUS,
        vol.Required(SZ_SETPOINT_STATUS): SCH_SETPOINT_STATUS,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_STATE_STATUS = vol.Schema(
    {
        vol.Required(SZ_STATE): str,  # "On", "Off"
        vol.Required(SZ_MODE): str,  # "PermanentOverride", "FollowSchedule"
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_DHW = vol.Schema(
    {
        vol.Required(SZ_DHW_ID): str,
        vol.Required(SZ_NAME): str,
        vol.Required(SZ_TEMPERATURE_STATUS): SCH_TEMPERATURE_STATUS,
        vol.Required(SZ_STATE_STATUS): SCH_STATE_STATUS,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SYSTEM_MODE_STATUS = vol.Schema(
    {
        vol.Required(SZ_MODE): str,
        vol.Required(SZ_IS_PERMANENT): bool,
    },
    extra=vol.PREVENT_EXTRA,
)  # TODO: also do isTemporary

SCH_TEMPERATURE_CONTROL_SYSTEM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_ID): str,
        vol.Required(SZ_SYSTEM_MODE_STATUS): SCH_SYSTEM_MODE_STATUS,
        vol.Required(SZ_ZONES): [SCH_ZONE],
        vol.Optional(SZ_DHW): SCH_DHW,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GATEWAY = vol.Schema(
    {
        vol.Required(SZ_GATEWAY_ID): str,
        vol.Required(SZ_TEMPERATURE_CONTROL_SYSTEMS): [dict],
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_STATUS = vol.Schema(
    {
        vol.Required(SZ_LOCATION_ID): str,
        vol.Required(SZ_GATEWAYS): [SCH_GATEWAY],
    },
    extra=vol.PREVENT_EXTRA,
)
