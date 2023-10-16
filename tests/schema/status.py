#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Config JSON."""
from __future__ import annotations

import voluptuous as vol  # type: ignore[import]

from .const import (
    REGEX_DHW_ID,
    REGEX_GATEWAY_ID,
    REGEX_LOCATION_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
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
    SZ_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONES,
)
from .const import (
    ZoneMode,
    DhwState,
    SystemMode,
    FaultType,
)

SCH_ACTIVE_FAULT = vol.Schema(
    {
        vol.Required(SZ_FAULT_TYPE): vol.Any(*[f.value for f in FaultType]),
        vol.Required(SZ_SINCE): vol.Datetime(format="%Y-%m-%dT%H:%M:%S"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_TEMPERATURE_STATUS = vol.Any(
    vol.Schema(
        {vol.Required(SZ_IS_AVAILABLE): False},
        extra=vol.PREVENT_EXTRA,
    ),
    vol.Schema(
        {vol.Required(SZ_IS_AVAILABLE): True, vol.Required(SZ_TEMPERATURE): float},
        extra=vol.PREVENT_EXTRA,
    ),
    extra=vol.PREVENT_EXTRA,
)

SCH_SETPOINT_STATUS = vol.Schema(
    {
        vol.Required(SZ_TARGET_HEAT_TEMPERATURE): float,
        vol.Required(SZ_SETPOINT_MODE): vol.Any(*[m.value for m in ZoneMode]),
        vol.Optional(SZ_UNTIL): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_ZONE = vol.Schema(
    {
        vol.Required(SZ_ZONE_ID): vol.Match(REGEX_ZONE_ID),
        vol.Required(SZ_NAME): str,
        vol.Required(SZ_TEMPERATURE_STATUS): SCH_TEMPERATURE_STATUS,
        vol.Required(SZ_SETPOINT_STATUS): SCH_SETPOINT_STATUS,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_STATE_STATUS = vol.Schema(
    {
        vol.Required(SZ_STATE): vol.Any(*[s.value for s in DhwState]),
        vol.Required(SZ_MODE): vol.Any(*[m.value for m in ZoneMode]),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_DHW = vol.Schema(
    {
        vol.Required(SZ_DHW_ID): vol.Match(REGEX_DHW_ID),
        vol.Required(SZ_TEMPERATURE_STATUS): SCH_TEMPERATURE_STATUS,
        vol.Required(SZ_STATE_STATUS): SCH_STATE_STATUS,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_SYSTEM_MODE_STATUS = vol.Schema(  # TODO: also do isTemporary?
    {
        vol.Required(SZ_MODE): vol.Any(*[m.value for m in SystemMode]),
        vol.Required(SZ_IS_PERMANENT): bool,
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_TEMPERATURE_CONTROL_SYSTEM = vol.Schema(
    {
        vol.Required(SZ_SYSTEM_ID): vol.Match(REGEX_SYSTEM_ID),
        vol.Required(SZ_SYSTEM_MODE_STATUS): SCH_SYSTEM_MODE_STATUS,
        vol.Required(SZ_ZONES): [SCH_ZONE],
        vol.Optional(SZ_DHW): SCH_DHW,
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GATEWAY = vol.Schema(
    {
        vol.Required(SZ_GATEWAY_ID): vol.Match(REGEX_GATEWAY_ID),
        vol.Required(SZ_TEMPERATURE_CONTROL_SYSTEMS): [SCH_TEMPERATURE_CONTROL_SYSTEM],
        vol.Required(SZ_ACTIVE_FAULTS): [SCH_ACTIVE_FAULT],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_STATUS = vol.Schema(
    {
        vol.Required(SZ_LOCATION_ID): vol.Match(REGEX_LOCATION_ID),
        vol.Required(SZ_GATEWAYS): [SCH_GATEWAY],
    },
    extra=vol.PREVENT_EXTRA,
)
