#!/usr/bin/env python3
"""evohomeasync2 schema - for Config JSON of RESTful API."""
# ruff: noqa: E501
# ruff: line-length=120

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import voluptuous as vol

from .const import (
    REGEX_DHW_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
    SZ_ALLOWED_FAN_MODES,
    SZ_ALLOWED_MODES,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_ALLOWED_STATES,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_CAN_BE_PERMANENT,
    SZ_CAN_BE_TEMPORARY,
    SZ_CAN_CONTROL_COOL,
    SZ_CAN_CONTROL_HEAT,
    SZ_CITY,
    SZ_COUNTRY,
    SZ_CRC,
    SZ_CURRENT_OFFSET_MINUTES,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_DISPLAY_NAME,
    SZ_DURATION,
    SZ_FAN_MODE,
    SZ_FIRSTNAME,
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_GATEWAYS,
    SZ_IS_CANCELABLE,
    SZ_IS_CHANGEABLE,
    SZ_IS_WI_FI,
    SZ_LASTNAME,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_LOCATION_OWNER,
    SZ_LOCATION_TYPE,
    SZ_MAC,
    SZ_MAX_COOL_SETPOINT,
    SZ_MAX_DURATION,
    SZ_MAX_HEAT_SETPOINT,
    SZ_MAX_SWITCHPOINTS_PER_DAY,
    SZ_MIN_COOL_SETPOINT,
    SZ_MIN_DURATION,
    SZ_MIN_HEAT_SETPOINT,
    SZ_MIN_SWITCHPOINTS_PER_DAY,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_OFFSET_MINUTES,
    SZ_PERIOD,
    SZ_POSTCODE,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_DEADBAND,
    SZ_SETPOINT_VALUE_RESOLUTION,
    SZ_STREET_ADDRESS,
    SZ_SUPPORTS_DAYLIGHT_SAVING,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TIME_ZONE,
    SZ_TIME_ZONE_ID,
    SZ_TIMING_MODE,
    SZ_TIMING_RESOLUTION,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
    SZ_USER_ID,
    SZ_USERNAME,
    SZ_VACATION_HOLD_CAPABILITIES,
    SZ_VALUE_RESOLUTION,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
    SZ_ZONES,
    DhwState,
    FanMode,
    SystemMode,
    TcsModelType,
    ZoneMode,
    ZoneModelType,
    ZoneType,
    obfuscate as _obfuscate,
)
from .helpers import do_nothing, snake_to_camel

# These are best guess
MAX_HEAT_SETPOINT_LOWER: Final = 21.0
MAX_HEAT_SETPOINT_UPPER: Final = 35.0

MIN_HEAT_SETPOINT_LOWER: Final = 4.5
MIN_HEAT_SETPOINT_UPPER: Final = 21.0


def _factory_system_mode_perm(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the permanent system modes schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SYSTEM_MODE)): vol.Any(
                str(SystemMode.AUTO),
                str(SystemMode.AUTO_WITH_RESET),
                str(SystemMode.HEATING_OFF),
                str(SystemMode.OFF),  # not evohome
                str(SystemMode.HEAT),  # not evohome
                str(SystemMode.COOL),  # not evohome
            ),
            vol.Required(fnc(SZ_CAN_BE_PERMANENT)): True,
            vol.Required(fnc(SZ_CAN_BE_TEMPORARY)): False,
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_system_mode_temp(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the temporary system modes schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SYSTEM_MODE)): vol.Any(
                str(SystemMode.AUTO_WITH_ECO),
                str(SystemMode.AWAY),
                str(SystemMode.CUSTOM),
                str(SystemMode.DAY_OFF),
            ),
            vol.Required(fnc(SZ_CAN_BE_PERMANENT)): True,
            vol.Required(fnc(SZ_CAN_BE_TEMPORARY)): True,
            vol.Required(fnc(SZ_MAX_DURATION)): str,  # "99.00:00:00"
            vol.Required(fnc(SZ_TIMING_RESOLUTION)): str,  # "1.00:00:00"
            vol.Required(fnc(SZ_TIMING_MODE)): vol.Any(SZ_DURATION, SZ_PERIOD),
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_schedule_capabilities_response(
    fnc: Callable[[str], str] = do_nothing,
) -> vol.Schema:
    """Factory for the schedule_capabilities_response schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_MAX_SWITCHPOINTS_PER_DAY)): int,  # 6
            vol.Required(fnc(SZ_MIN_SWITCHPOINTS_PER_DAY)): int,  # 1
            vol.Required(fnc(SZ_TIMING_RESOLUTION)): vol.Datetime(
                format="00:%M:00"
            ),  # "00:10:00"
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_dhw(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the DHW schema."""

    SCH_DHW_STATE_CAPABILITIES_RESPONSE: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_ALLOWED_STATES)): list(m.value for m in DhwState),
            vol.Required(fnc(SZ_ALLOWED_MODES)): list(m.value for m in ZoneMode),
            vol.Required(fnc(SZ_MAX_DURATION)): str,
            vol.Required(fnc(SZ_TIMING_RESOLUTION)): vol.Datetime(format="00:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_DHW_ID)): vol.Match(REGEX_DHW_ID),
            vol.Required(
                fnc(SZ_DHW_STATE_CAPABILITIES_RESPONSE)
            ): SCH_DHW_STATE_CAPABILITIES_RESPONSE,
            vol.Required(
                fnc(SZ_SCHEDULE_CAPABILITIES_RESPONSE)
            ): _factory_schedule_capabilities_response(fnc),
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_zone(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the zone schema."""

    SCH_FAN_MODE: Final = vol.Schema(  # noqa: F841
        {
            vol.Required(fnc(SZ_FAN_MODE)): vol.In([m.value for m in FanMode]),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_VACATION_HOLD_CAPABILITIES: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_IS_CHANGEABLE)): bool,
            vol.Required(fnc(SZ_IS_CANCELABLE)): bool,
            vol.Optional(fnc(SZ_MAX_DURATION)): str,
            vol.Optional(fnc(SZ_MIN_DURATION)): str,
            vol.Optional(fnc(SZ_TIMING_RESOLUTION)): vol.Datetime(format="00:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_SETPOINT_CAPABILITIES: Final = vol.Schema(  # min/max as per evohome
        {
            vol.Required(fnc(SZ_CAN_CONTROL_HEAT)): bool,
            vol.Required(fnc(SZ_MAX_HEAT_SETPOINT)): vol.All(
                float,
                vol.Range(min=MAX_HEAT_SETPOINT_LOWER, max=MAX_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(SZ_MIN_HEAT_SETPOINT)): vol.All(
                float,
                vol.Range(min=MIN_HEAT_SETPOINT_LOWER, max=MIN_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(SZ_CAN_CONTROL_COOL)): bool,
            vol.Optional(fnc(SZ_MAX_COOL_SETPOINT)): float,  # TODO
            vol.Optional(fnc(SZ_MIN_COOL_SETPOINT)): float,  # TODO
            vol.Required(fnc(SZ_ALLOWED_SETPOINT_MODES)): list(
                m.value for m in ZoneMode
            ),
            vol.Required(fnc(SZ_VALUE_RESOLUTION)): float,  # 0.5
            vol.Required(fnc(SZ_MAX_DURATION)): str,  # "1.00:00:00"
            vol.Required(fnc(SZ_TIMING_RESOLUTION)): vol.Datetime(
                format="00:%M:00"
            ),  # "00:10:00"
            vol.Optional(
                fnc(SZ_VACATION_HOLD_CAPABILITIES)
            ): SCH_VACATION_HOLD_CAPABILITIES,  # non-evohome
            # vol.Optional((SZ_ALLOWED_FAN_MODES)): dict,  # non-evohome
            vol.Optional(fnc(SZ_SETPOINT_DEADBAND)): float,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_SCHEDULE_CAPABILITIES = _factory_schedule_capabilities_response(fnc).extend(
        {
            vol.Required(fnc(SZ_SETPOINT_VALUE_RESOLUTION)): float,
        },
        extra=vol.PREVENT_EXTRA,
    )

    # schedule_capabilities is required for evo, optional for FocusProWifiRetail
    return vol.Schema(
        {
            vol.Required(fnc(SZ_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(SZ_MODEL_TYPE)): vol.In([m.value for m in ZoneModelType]),
            vol.Required(fnc(SZ_NAME)): str,
            vol.Required(fnc(SZ_SETPOINT_CAPABILITIES)): SCH_SETPOINT_CAPABILITIES,
            vol.Optional(fnc(SZ_SCHEDULE_CAPABILITIES)): SCH_SCHEDULE_CAPABILITIES,
            vol.Required(fnc(SZ_ZONE_TYPE)): vol.In([m.value for m in ZoneType]),
            vol.Optional(fnc(SZ_ALLOWED_FAN_MODES)): list,  # FocusProWifiRetail
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_tcs(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the TCS schema."""

    SCH_ALLOWED_SYSTEM_MODES: Final = vol.Any(
        _factory_system_mode_perm(fnc), _factory_system_mode_temp(fnc)
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(SZ_MODEL_TYPE)): vol.In([m.value for m in TcsModelType]),
            vol.Required(fnc(SZ_ALLOWED_SYSTEM_MODES)): [SCH_ALLOWED_SYSTEM_MODES],
            vol.Required(fnc(SZ_ZONES)): vol.All(
                [_factory_zone(fnc)], vol.Length(min=1, max=12)
            ),
            vol.Optional(fnc(SZ_DHW)): _factory_dhw(fnc),
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_gateway(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the gateway schema."""

    SCH_GATEWAY_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_GATEWAY_ID)): str,
            vol.Required(fnc(SZ_MAC)): str,
            vol.Required(fnc(SZ_CRC)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_IS_WI_FI)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_GATEWAY_INFO)): SCH_GATEWAY_INFO,
            vol.Required(fnc(SZ_TEMPERATURE_CONTROL_SYSTEMS)): [_factory_tcs(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_time_zone(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the time zone schema."""

    return vol.Schema(
        {
            vol.Required(fnc(SZ_TIME_ZONE_ID)): str,
            vol.Required(fnc(SZ_DISPLAY_NAME)): str,
            vol.Required(fnc(SZ_OFFSET_MINUTES)): int,
            vol.Required(fnc(SZ_CURRENT_OFFSET_MINUTES)): int,
            vol.Required(fnc(SZ_SUPPORTS_DAYLIGHT_SAVING)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_locations_installation_info(
    fnc: Callable[[str], str] = do_nothing,
) -> vol.Schema:
    """Factory for the location (config) schema."""

    SCH_LOCATION_OWNER: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_USER_ID)): str,
            vol.Required(fnc(SZ_USERNAME)): vol.All(vol.Email(), _obfuscate),
            vol.Required(fnc(SZ_FIRSTNAME)): str,
            vol.Required(fnc(SZ_LASTNAME)): vol.All(str, _obfuscate),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_LOCATION_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(SZ_LOCATION_ID)): str,
            vol.Required(fnc(SZ_NAME)): str,  # e.g. "My Home"
            vol.Required(fnc(SZ_STREET_ADDRESS)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_CITY)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_COUNTRY)): str,
            vol.Required(fnc(SZ_POSTCODE)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_LOCATION_TYPE)): str,  # "Residential"
            vol.Required(fnc(SZ_USE_DAYLIGHT_SAVE_SWITCHING)): bool,
            vol.Required(fnc(SZ_TIME_ZONE)): _factory_time_zone(fnc),
            vol.Required(fnc(SZ_LOCATION_OWNER)): SCH_LOCATION_OWNER,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(SZ_LOCATION_INFO)): SCH_LOCATION_INFO,
            vol.Required(fnc(SZ_GATEWAYS)): [_factory_gateway(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _factory_user_locations_installation_info(
    fnc: Callable[[str], str] = do_nothing,
) -> vol.Schema:
    """Factory for the user locations (config) schema."""

    return vol.Schema(
        [_factory_locations_installation_info(fnc)],
        extra=vol.PREVENT_EXTRA,
    )


SCH_DHW_CONFIG: Final = _factory_dhw(snake_to_camel)

SCH_ZON_CONFIG: Final = _factory_zone(snake_to_camel)

SCH_TCS_CONFIG: Final = _factory_tcs(snake_to_camel)

SCH_GWY_CONFIG: Final = _factory_gateway(snake_to_camel)

SCH_TIME_ZONE: Final = _factory_time_zone(snake_to_camel)

# GET /location/{location_id}/installationInfo?includeTemperatureControlSystems=True
SCH_LOCATION_INSTALLATION_INFO: Final = _factory_locations_installation_info(
    snake_to_camel
)
# GET /location/installationInfo?userId={user_id}&includeTemperatureControlSystems=True
SCH_USER_LOCATIONS_INSTALLATION_INFO: Final = _factory_user_locations_installation_info(
    snake_to_camel
)
