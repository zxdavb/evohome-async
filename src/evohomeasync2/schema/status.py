#!/usr/bin/env python3
"""evohomeasync schema - for Status JSON of RESTful API."""

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
    S2_ACTIVE_FAULTS,
    S2_CAN_BE_CHANGED,
    S2_DHW,
    S2_DHW_ID,
    S2_FAN_MODE,
    S2_FAN_STATUS,
    S2_FAULT_TYPE,
    S2_GATEWAY_ID,
    S2_GATEWAYS,
    S2_IS_AVAILABLE,
    S2_IS_PERMANENT,
    S2_LOCATION_ID,
    S2_MODE,
    S2_NAME,
    S2_SETPOINT_MODE,
    S2_SETPOINT_STATUS,
    S2_SINCE,
    S2_STATE,
    S2_STATE_STATUS,
    S2_SYSTEM_ID,
    S2_SYSTEM_MODE_STATUS,
    S2_TARGET_HEAT_TEMPERATURE,  # also: SZ_TARGET_COOL_TEMPERATURE ??
    S2_TEMPERATURE,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    S2_TEMPERATURE_STATUS,
    S2_TIME_UNTIL,
    S2_UNTIL,
    S2_ZONE_ID,
    S2_ZONES,
    DhwState,
    FanMode,
    FaultType,
    SystemMode,
    ZoneMode,
)
from .helpers import _do_nothing

# HACK: "2023-05-04T18:47:36.7727046" (7, not 6 digits) seen with gateway fault
_DTM_FORMAT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{1,7}$"


def factory_active_faults(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the active faults schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_FAULT_TYPE)): vol.In([m.value for m in FaultType]),
            vol.Required(fnc(S2_SINCE)): vol.Any(
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S"),  # faults for zones
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S.%f"),
                vol.All(str, vol.Match(_DTM_FORMAT)),  # faults for gateways
            ),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_temp_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Any:
    """Factory for the temperature status schema."""

    return vol.Any(
        vol.Schema(
            {vol.Required(fnc(S2_IS_AVAILABLE)): False},
            extra=vol.PREVENT_EXTRA,
        ),
        vol.Schema(
            {
                vol.Required(fnc(S2_IS_AVAILABLE)): True,
                vol.Required(fnc(S2_TEMPERATURE)): float,
            },
            extra=vol.PREVENT_EXTRA,
        ),
        extra=vol.PREVENT_EXTRA,
    )


def factory_zone_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the zone status schema."""

    SCH_SETPOINT_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_TARGET_HEAT_TEMPERATURE)): float,
            vol.Required(fnc(S2_SETPOINT_MODE)): vol.In([m.value for m in ZoneMode]),
            vol.Optional(fnc(S2_UNTIL)): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    SCH_FAN_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_FAN_MODE)): vol.In([m.value for m in FanMode]),
            vol.Required(fnc(S2_CAN_BE_CHANGED)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(S2_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(S2_NAME)): str,
            vol.Required(fnc(S2_TEMPERATURE_STATUS)): factory_temp_status(fnc),
            vol.Required(fnc(S2_SETPOINT_STATUS)): SCH_SETPOINT_STATUS,
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(fnc)],
            vol.Optional(fnc(S2_FAN_STATUS)): SCH_FAN_STATUS,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_dhw_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the DHW status schema."""

    SCH_STATE_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_STATE)): vol.In([m.value for m in DhwState]),
            vol.Required(fnc(S2_MODE)): vol.In([m.value for m in ZoneMode]),
            vol.Optional(fnc(S2_UNTIL)): vol.Datetime(format="%Y-%m-%dT%H:%M:%SZ"),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(S2_DHW_ID)): vol.Match(REGEX_DHW_ID),
            vol.Required(fnc(S2_TEMPERATURE_STATUS)): factory_temp_status(fnc),
            vol.Required(fnc(S2_STATE_STATUS)): SCH_STATE_STATUS,
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_system_mode_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Any:
    """Factory for the system mode status schema."""

    return vol.Any(
        vol.Schema(
            {
                vol.Required(fnc(S2_MODE)): vol.In([m.value for m in SystemMode]),
                vol.Required(fnc(S2_IS_PERMANENT)): True,
            }
        ),
        vol.Schema(
            {
                vol.Required(S2_MODE): vol.Any(
                    str(SystemMode.AUTO_WITH_ECO),
                    str(SystemMode.AWAY),
                    str(SystemMode.CUSTOM),
                    str(SystemMode.DAY_OFF),
                ),
                vol.Required(fnc(S2_TIME_UNTIL)): vol.Datetime(
                    format="%Y-%m-%dT%H:%M:%SZ"
                ),
                vol.Required(fnc(S2_IS_PERMANENT)): False,
            }
        ),
        extra=vol.PREVENT_EXTRA,
    )


def factory_tcs_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the TCS status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(S2_SYSTEM_MODE_STATUS)): factory_system_mode_status(fnc),
            vol.Required(fnc(S2_ZONES)): [factory_zone_status(fnc)],
            vol.Optional(fnc(S2_DHW)): factory_dhw_status(fnc),
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_gwy_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the gateway status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_ID)): vol.Match(REGEX_GATEWAY_ID),
            vol.Required(fnc(S2_TEMPERATURE_CONTROL_SYSTEMS)): [
                factory_tcs_status(fnc)
            ],
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_loc_status(fnc: Callable[[str], str] = _do_nothing) -> vol.Schema:
    """Factory for the locations status schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_ID)): vol.Match(REGEX_LOCATION_ID),
            vol.Required(fnc(S2_GATEWAYS)): [factory_gwy_status(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


SCH_DHW_STATUS: Final = factory_dhw_status()

SCH_ZON_CONFIG: Final = factory_zone_status()

SCH_TCS_STATUS: Final = factory_tcs_status()

SCH_GWY_STATUS: Final = factory_gwy_status()

# GET /location/{location_id}/status?includeTemperatureControlSystems=True
SCH_LOC_STATUS: Final = factory_loc_status()
