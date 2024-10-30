#!/usr/bin/env python3
"""evohomeasync2 schema - for Status JSON of RESTful API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import voluptuous as vol

from .const import (
    REGEX_DHW_ID,
    REGEX_GATEWAY_ID,
    REGEX_LOCATION_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
    SZ_ACTIVE_FAULTS,
    SZ_CAN_BE_CHANGED,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_FAN_MODE,
    SZ_FAN_STATUS,
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
    SZ_TARGET_HEAT_TEMPERATURE,  # also: SZ_TARGET_COOL_TEMPERATURE ??
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TEMPERATURE_STATUS,
    SZ_TIME_UNTIL,
    SZ_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONES,
    DhwState,
    FanMode,
    FaultType,
    SystemMode,
    ZoneMode,
)
from .helpers import do_nothing, snake_to_camel

# HACK: "2023-05-04T18:47:36.7727046" (7, not 6 digits) seen with gateway fault
_DTM_FORMAT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{1,7}$"


def _factory_active_faults(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the active faults schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_FAULT_TYPE)): vol.In([m.value for m in FaultType]),
            vol.Required(fnc(SZ_SINCE)): vol.Any(
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S"),  # faults for zones
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S.%f"),
                vol.All(str, vol.Match(_DTM_FORMAT)),  # faults for gateways
            ),
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_temp_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the temperature status schema."""

    return vol.Any(
        vol.Schema(
            {vol.Required(fnc(SZ_IS_AVAILABLE)): False},
            extra=vol.PREVENT_EXTRA,
        ),
        vol.Schema(
            {
                vol.Required(fnc(SZ_IS_AVAILABLE)): True,
                vol.Required(fnc(SZ_TEMPERATURE)): float,
            },
            extra=vol.PREVENT_EXTRA,
        ),
        extra=vol.PREVENT_EXTRA,
    )


def _factory_zone_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the zone status schema."""

    SCH_SETPOINT_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_TARGET_HEAT_TEMPERATURE)): float,
            vol.Required(fnc(SZ_SETPOINT_MODE)): vol.In([m.value for m in ZoneMode]),
            vol.Optional(fnc(SZ_UNTIL)): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: SZ_UNTIL is present only for some modes

    SCH_FAN_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_FAN_MODE)): vol.In([m.value for m in FanMode]),
            vol.Required(fnc(SZ_CAN_BE_CHANGED)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: SZ_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(SZ_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(SZ_NAME)): str,
            vol.Required(fnc(SZ_TEMPERATURE_STATUS)): _factory_temp_status(fnc),
            vol.Required(fnc(SZ_SETPOINT_STATUS)): SCH_SETPOINT_STATUS,
            vol.Required(fnc(SZ_ACTIVE_FAULTS)): [_factory_active_faults(fnc)],
            vol.Optional(fnc(SZ_FAN_STATUS)): SCH_FAN_STATUS,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_dhw_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the DHW status schema."""

    SCH_STATE_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_STATE)): vol.In([m.value for m in DhwState]),
            vol.Required(fnc(SZ_MODE)): vol.In([m.value for m in ZoneMode]),
            vol.Optional(fnc(SZ_UNTIL)): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: SZ_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(SZ_DHW_ID)): vol.Match(REGEX_DHW_ID),
            vol.Required(fnc(SZ_TEMPERATURE_STATUS)): _factory_temp_status(fnc),
            vol.Required(fnc(SZ_STATE_STATUS)): SCH_STATE_STATUS,
            vol.Required(fnc(SZ_ACTIVE_FAULTS)): [_factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_system_mode_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the system mode status schema."""

    return vol.Any(
        vol.Schema(
            {
                vol.Required(fnc(SZ_MODE)): vol.In([m.value for m in SystemMode]),
                vol.Required(fnc(SZ_IS_PERMANENT)): True,
            }
        ),
        vol.Schema(
            {
                vol.Required(SZ_MODE): vol.Any(
                    str(SystemMode.AUTO_WITH_ECO),
                    str(SystemMode.AWAY),
                    str(SystemMode.CUSTOM),
                    str(SystemMode.DAY_OFF),
                ),
                vol.Required(fnc(SZ_TIME_UNTIL)): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
                vol.Required(fnc(SZ_IS_PERMANENT)): False,
            }
        ),
        extra=vol.PREVENT_EXTRA,
    )


def _factory_tcs_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the TCS status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(SZ_SYSTEM_MODE_STATUS)): _factory_system_mode_status(fnc),
            vol.Required(fnc(SZ_ZONES)): [SCH_ZON_CONFIG],
            vol.Optional(fnc(SZ_DHW)): _factory_dhw_status(fnc),
            vol.Required(fnc(SZ_ACTIVE_FAULTS)): [_factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_gwy_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the gateway status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_GATEWAY_ID)): vol.Match(REGEX_GATEWAY_ID),
            vol.Required(fnc(SZ_TEMPERATURE_CONTROL_SYSTEMS)): [
                _factory_tcs_status(fnc)
            ],
            vol.Required(fnc(SZ_ACTIVE_FAULTS)): [_factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_loc_status(fnc: Callable = do_nothing) -> vol.Schema:
    """Factory for the locations status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_LOCATION_ID)): vol.Match(REGEX_LOCATION_ID),
            vol.Required(fnc(SZ_GATEWAYS)): [_factory_gwy_status(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


SCH_DHW_STATUS: Final = _factory_dhw_status(snake_to_camel)

SCH_ZON_CONFIG: Final = _factory_zone_status(snake_to_camel)

SCH_TCS_STATUS: Final = _factory_tcs_status(snake_to_camel)

SCH_GWY_STATUS: Final = _factory_gwy_status(snake_to_camel)

# location/{location_id}/status?includeTemperatureControlSystems=True
SCH_LOC_STATUS: Final = _factory_loc_status(snake_to_camel)
