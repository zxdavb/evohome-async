"""Schema for the vendor's TCC v2 API - for GET status of Location.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the voluptuous
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import Final, NotRequired, TypedDict

import voluptuous as vol

from _evohome.helpers import camel_to_snake, noop

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
    TCC_DTM_STRFTIME,
    TccDhwState,
    TccFanMode,
    TccFaultType,
    TccSystemMode,
    TccZoneMode,
)
from .helpers import Case, factory_enum

# HACK: "2023-05-04T18:47:36.7727046" (7, not 6 digits) seen with gateway fault
_DTM_FORMAT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,7}$"


# GET /location/{loc_id}/status?include... returns this dict
class TccLocStatusResponseT(TypedDict):
    """Response to /location/{loc_id}/status?includeTemperatureControlSystems=True

    The response is a dict of a single location.
    """

    locationId: str
    gateways: list[TccGwyStatusResponseT]


class TccGwyStatusResponseT(TypedDict):
    gatewayId: str
    activeFaults: list[TccActiveFaultResponseT]
    temperatureControlSystems: list[TccTcsStatusResponseT]


class TccActiveFaultResponseT(TypedDict):
    faultType: str
    since: str


class TccTcsStatusResponseT(TypedDict):
    systemId: str
    activeFaults: list[TccActiveFaultResponseT]
    systemModeStatus: TccSystemModeStatusResponseT
    zones: list[TccZonStatusResponseT]
    dhw: NotRequired[TccDhwStatusResponseT]


class TccSystemModeStatusResponseT(TypedDict):
    mode: TccSystemMode
    isPermanent: bool
    timeUntil: NotRequired[str]


class TccZonStatusResponseT(TypedDict):
    zoneId: str
    activeFaults: list[TccActiveFaultResponseT]
    setpointStatus: TccZonSetpointStatusResponseT
    temperatureStatus: TccTemperatureStatusResponseT
    name: str


class TccZonSetpointStatusResponseT(TypedDict):
    setpointMode: TccZoneMode
    targetHeatTemperature: float
    until: NotRequired[str]


class TccTemperatureStatusResponseT(TypedDict):
    isAvailable: bool
    temperature: NotRequired[float]


class TccDhwStatusResponseT(TypedDict):
    dhwId: str
    activeFaults: list[TccActiveFaultResponseT]
    stateStatus: TccDhwStateStatusResponseT
    temperatureStatus: TccTemperatureStatusResponseT


class TccDhwStateStatusResponseT(TypedDict):
    mode: TccZoneMode
    state: TccDhwState
    until: NotRequired[str]


def factory_active_faults(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the active faults schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_FAULT_TYPE)): factory_enum(case, TccFaultType),
            vol.Required(fnc(S2_SINCE)): vol.Any(
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S"),  # faults for zones
                vol.Datetime(format="%Y-%m-%dT%H:%M:%S.%f"),
                vol.All(str, vol.Match(_DTM_FORMAT)),  # faults for gateways
            ),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_temp_status(case: Case = Case.VENDOR) -> vol.Any:
    """Factory for the temperature status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

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


def factory_zon_status(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the zone status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_SETPOINT_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_TARGET_HEAT_TEMPERATURE)): float,
            vol.Required(fnc(S2_SETPOINT_MODE)): factory_enum(case, TccZoneMode),
            vol.Optional(fnc(S2_UNTIL)): vol.Datetime(format=TCC_DTM_STRFTIME),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    SCH_FAN_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_FAN_MODE)): factory_enum(case, TccFanMode),
            vol.Required(fnc(S2_CAN_BE_CHANGED)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(S2_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(S2_NAME)): str,
            vol.Required(fnc(S2_TEMPERATURE_STATUS)): factory_temp_status(case),
            vol.Required(fnc(S2_SETPOINT_STATUS)): SCH_SETPOINT_STATUS,
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(case)],
            vol.Optional(fnc(S2_FAN_STATUS)): SCH_FAN_STATUS,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_dhw_status(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the DHW status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_STATE_STATUS: Final = vol.Schema(
        {
            vol.Required(fnc(S2_STATE)): factory_enum(case, TccDhwState),
            vol.Required(fnc(S2_MODE)): factory_enum(case, TccZoneMode),
            vol.Optional(fnc(S2_UNTIL)): vol.Datetime(format=TCC_DTM_STRFTIME),
        },
        extra=vol.PREVENT_EXTRA,
    )  # NOTE: S2_UNTIL is present only for some modes

    return vol.Schema(
        {
            vol.Required(fnc(S2_DHW_ID)): vol.Match(REGEX_DHW_ID),
            vol.Required(fnc(S2_TEMPERATURE_STATUS)): factory_temp_status(case),
            vol.Required(fnc(S2_STATE_STATUS)): SCH_STATE_STATUS,
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_system_mode_status(case: Case = Case.VENDOR) -> vol.Any:
    """Factory for the system mode status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    # only these modes can be temporary (i.e. have a time_until)
    temporary_modes = (
        TccSystemMode.AUTO_WITH_ECO,
        TccSystemMode.AWAY,
        TccSystemMode.CUSTOM,
        TccSystemMode.DAY_OFF,
    )
    temporary_mode: vol.In | vol.All
    if case is Case.VENDOR:
        temporary_mode = vol.In([str(m) for m in temporary_modes])
    else:
        temporary_mode = vol.All(
            factory_enum(case, TccSystemMode),
            vol.In([camel_to_snake(str(m)) for m in temporary_modes]),
        )

    return vol.Any(
        vol.Schema(
            {
                vol.Required(fnc(S2_MODE)): factory_enum(case, TccSystemMode),
                vol.Required(fnc(S2_IS_PERMANENT)): True,
            }
        ),
        vol.Schema(
            {
                vol.Required(fnc(S2_MODE)): temporary_mode,
                vol.Required(fnc(S2_TIME_UNTIL)): vol.Datetime(format=TCC_DTM_STRFTIME),
                vol.Required(fnc(S2_IS_PERMANENT)): False,
            }
        ),
        extra=vol.PREVENT_EXTRA,
    )


def factory_tcs_status(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the TCS status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(S2_SYSTEM_MODE_STATUS)): factory_system_mode_status(case),
            vol.Required(fnc(S2_ZONES)): [factory_zon_status(case)],
            vol.Optional(fnc(S2_DHW)): factory_dhw_status(case),
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_gwy_status(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the gateway status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_ID)): vol.Match(REGEX_GATEWAY_ID),
            vol.Required(fnc(S2_TEMPERATURE_CONTROL_SYSTEMS)): [factory_tcs_status(case)],
            vol.Required(fnc(S2_ACTIVE_FAULTS)): [factory_active_faults(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_loc_status(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the locations status schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_ID)): vol.Match(REGEX_LOCATION_ID),
            vol.Required(fnc(S2_GATEWAYS)): [factory_gwy_status(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


# GET /location/{loc_id}/status?includeTemperatureControlSystems=True
TCC_GET_LOC_STATUS: Final = factory_loc_status()

# GET /gateway/{gwy_id}/status...
TCC_GET_GWY_STATUS: Final = factory_gwy_status()

# GET /temperatureControlSystem/{tcs_id}/status
TCC_GET_TCS_STATUS: Final = factory_tcs_status()

# GET /domesticHotWater/{dhw_id}/status
TCC_GET_DHW_STATUS: Final = factory_dhw_status()

# GET /temperatureZone/{zone_id}/heatSetpoint
# TODO:

# GET /temperatureZone/{zone_id}/status
TCC_GET_ZON_STATUS: Final = factory_zon_status()
