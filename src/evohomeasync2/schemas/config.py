"""evohomeasync schema - for Config JSON of RESTful API."""
# ruff: line-length=120

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Literal, NotRequired, TypedDict

import voluptuous as vol

from evohome.helpers import noop, obfuscate

from .const import (
    REGEX_DHW_ID,
    REGEX_SYSTEM_ID,
    REGEX_ZONE_ID,
    S2_ALLOWED_FAN_MODES,
    S2_ALLOWED_MODES,
    S2_ALLOWED_SETPOINT_MODES,
    S2_ALLOWED_STATES,
    S2_ALLOWED_SYSTEM_MODES,
    S2_CAN_BE_PERMANENT,
    S2_CAN_BE_TEMPORARY,
    S2_CAN_CONTROL_COOL,
    S2_CAN_CONTROL_HEAT,
    S2_CITY,
    S2_COUNTRY,
    S2_CRC,
    S2_CURRENT_OFFSET_MINUTES,
    S2_DHW,
    S2_DHW_ID,
    S2_DHW_STATE_CAPABILITIES_RESPONSE,
    S2_DISPLAY_NAME,
    S2_DURATION,
    S2_FAN_MODE,
    S2_FIRSTNAME,
    S2_GATEWAY_ID,
    S2_GATEWAY_INFO,
    S2_GATEWAYS,
    S2_IS_CANCELABLE,
    S2_IS_CHANGEABLE,
    S2_IS_WI_FI,
    S2_LASTNAME,
    S2_LOCATION_ID,
    S2_LOCATION_INFO,
    S2_LOCATION_OWNER,
    S2_LOCATION_TYPE,
    S2_MAC,
    S2_MAX_COOL_SETPOINT,
    S2_MAX_DURATION,
    S2_MAX_HEAT_SETPOINT,
    S2_MAX_SWITCHPOINTS_PER_DAY,
    S2_MIN_COOL_SETPOINT,
    S2_MIN_DURATION,
    S2_MIN_HEAT_SETPOINT,
    S2_MIN_SWITCHPOINTS_PER_DAY,
    S2_MODEL_TYPE,
    S2_NAME,
    S2_OFFSET_MINUTES,
    S2_PERIOD,
    S2_POSTCODE,
    S2_SCHEDULE_CAPABILITIES,
    S2_SCHEDULE_CAPABILITIES_RESPONSE,
    S2_SETPOINT_CAPABILITIES,
    S2_SETPOINT_DEADBAND,
    S2_SETPOINT_VALUE_RESOLUTION,
    S2_STREET_ADDRESS,
    S2_SUPPORTS_DAYLIGHT_SAVING,
    S2_SYSTEM_ID,
    S2_SYSTEM_MODE,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    S2_TIME_ZONE,
    S2_TIME_ZONE_ID,
    S2_TIMING_MODE,
    S2_TIMING_RESOLUTION,
    S2_USE_DAYLIGHT_SAVE_SWITCHING,
    S2_USER_ID,
    S2_USERNAME,
    S2_VACATION_HOLD_CAPABILITIES,
    S2_VALUE_RESOLUTION,
    S2_ZONE_ID,
    S2_ZONE_TYPE,
    S2_ZONES,
    DhwState,
    FanMode,
    LocationType,
    SystemMode,
    TcsModelType,
    ZoneMode,
    ZoneModelType,
    ZoneType,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# These are best guess
MAX_HEAT_SETPOINT_LOWER: Final = 21.0
MAX_HEAT_SETPOINT_UPPER: Final = 35.0

MIN_HEAT_SETPOINT_LOWER: Final = 4.5
MIN_HEAT_SETPOINT_UPPER: Final = 21.0


# GET /location/installationInfo?userId={user_id} returns list of these dicts
class TccLocConfigResponseT(TypedDict):
    """Response to GET /locations?userId={user_id}&allData=True

    The response is a list of these dicts.
    """

    locationInfo: TccLocConfigEntryT
    gateways: list[TccGwyConfigResponseT]


class TccLocConfigEntryT(TypedDict):
    """Location configuration information."""

    locationId: str
    name: str
    streetAddress: str
    city: str
    state: str
    country: str
    postcode: str
    type: str
    locationType: LocationType
    useDaylightSaveSwitching: bool
    timeZone: TccTimeZoneInfoT
    locationOwner: TccLocationOwnerInfoT


class TccTimeZoneInfoT(TypedDict):
    """Time zone information."""

    timeZoneId: str
    displayName: str
    offsetMinutes: int
    currentOffsetMinutes: int
    supportsDaylightSaving: bool


class TccLocationOwnerInfoT(TypedDict):
    userId: str
    username: str
    firstname: str
    lastname: str


class TccGwyConfigResponseT(TypedDict):
    gatewayInfo: TccGwyConfigEntryT
    temperatureControlSystems: list[TccTcsConfigResponseT]


class TccGwyConfigEntryT(TypedDict):
    gatewayId: str
    mac: str
    crc: str
    isWiFi: bool


class TccTcsConfigEntryT(TypedDict):
    systemId: str
    modelType: TcsModelType
    allowedSystemModes: list[TccAllowedSystemModeResponseT]


class TccAllowedSystemModeResponseT(TypedDict):
    systemMode: SystemMode
    canBePermanent: Literal[True]
    canBeTemporary: bool
    maxDuration: NotRequired[str]
    timingResolution: NotRequired[str]
    timingMode: NotRequired[str]


class TccTcsConfigResponseT(TccTcsConfigEntryT):
    # system_id: str
    # model_type: str
    # allowed_system_modes: list[dict[str, Any]]
    zones: list[TccZonConfigResponseT]
    dhw: NotRequired[TccDhwConfigResponseT]


class TccZonConfigResponseT(TypedDict):
    zoneId: str
    modelType: ZoneModelType
    name: str
    setpointCapabilities: TccZonSetpointCapabilitiesResponseT
    scheduleCapabilities: TccZonScheduleCapabilitiesResponseT
    zoneType: ZoneType
    allowedFanModes: list[str]


class TccZonScheduleCapabilitiesResponseT(TypedDict):
    pass


class TccZonSetpointCapabilitiesResponseT(TypedDict):
    allowedSetpointModes: list[ZoneMode]
    canControlCool: bool
    canControlHeat: bool
    maxHeatSetpoint: float
    minHeatSetpoint: float
    valueResolution: float
    maxDuration: str
    timingResolution: str


class TccZonConfigEntryT(TccZonConfigResponseT):
    pass


class TccDhwConfigResponseT(TypedDict):
    dhwId: str
    scheduleCapabilitiesResponse: TccDhwScheduleCapabilitiesResponseT
    dhwStateCapabilitiesResponse: TccDhwStateCapabilitiesResponseT


class TccDhwScheduleCapabilitiesResponseT(TypedDict):
    pass


class TccDhwStateCapabilitiesResponseT(TypedDict):
    allowedStates: list[DhwState]
    allowedModes: list[ZoneMode]
    maxDuration: str
    timingResolution: str


class TccDhwConfigEntryT(TccDhwConfigResponseT):
    pass


def factory_system_mode_perm(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the permanent system modes schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_MODE)): vol.Any(
                str(SystemMode.AUTO),
                str(SystemMode.AUTO_WITH_RESET),
                str(SystemMode.HEATING_OFF),
                str(SystemMode.OFF),  # not evohome
                str(SystemMode.HEAT),  # not evohome
                str(SystemMode.COOL),  # not evohome
            ),
            vol.Required(fnc(S2_CAN_BE_PERMANENT)): True,
            vol.Required(fnc(S2_CAN_BE_TEMPORARY)): False,
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_system_mode_temp(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the temporary system modes schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_MODE)): vol.Any(
                str(SystemMode.AUTO_WITH_ECO),
                str(SystemMode.AWAY),
                str(SystemMode.CUSTOM),
                str(SystemMode.DAY_OFF),
            ),
            vol.Required(fnc(S2_CAN_BE_PERMANENT)): True,
            vol.Required(fnc(S2_CAN_BE_TEMPORARY)): True,
            vol.Required(fnc(S2_MAX_DURATION)): str,  # "99.00:00:00"
            vol.Required(fnc(S2_TIMING_RESOLUTION)): str,  # "1.00:00:00"
            vol.Required(fnc(S2_TIMING_MODE)): vol.Any(S2_DURATION, S2_PERIOD),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_schedule_capabilities_response(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the schedule_capabilities_response schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_MAX_SWITCHPOINTS_PER_DAY)): int,  # 6
            vol.Required(fnc(S2_MIN_SWITCHPOINTS_PER_DAY)): int,  # 1
            vol.Required(fnc(S2_TIMING_RESOLUTION)): vol.Datetime(
                format="00:%M:00"
            ),  # "00:10:00"
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_dhw(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the DHW schema."""

    SCH_DHW_STATE_CAPABILITIES_RESPONSE: Final = vol.Schema(
        {
            # TODO: list should be a non-empty *subset* of all possible DhwState(s)
            vol.Required(fnc(S2_ALLOWED_STATES)): [m.value for m in DhwState],
            # TODO: list should be a non-empty *subset* of all possible ZoneMode(s)
            vol.Required(fnc(S2_ALLOWED_MODES)): [m.value for m in ZoneMode],
            vol.Required(fnc(S2_MAX_DURATION)): str,
            vol.Required(fnc(S2_TIMING_RESOLUTION)): vol.Datetime(format="00:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_DHW_ID)): vol.Match(REGEX_DHW_ID),
            vol.Required(
                fnc(S2_DHW_STATE_CAPABILITIES_RESPONSE)
            ): SCH_DHW_STATE_CAPABILITIES_RESPONSE,
            vol.Required(
                fnc(S2_SCHEDULE_CAPABILITIES_RESPONSE)
            ): factory_schedule_capabilities_response(fnc),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_zone(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the zone schema."""

    SCH_FAN_MODE: Final = vol.Schema(  # noqa: F841
        {
            vol.Required(fnc(S2_FAN_MODE)): vol.In(FanMode),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_VACATION_HOLD_CAPABILITIES: Final = vol.Schema(
        {
            vol.Required(fnc(S2_IS_CHANGEABLE)): bool,
            vol.Required(fnc(S2_IS_CANCELABLE)): bool,
            vol.Optional(fnc(S2_MAX_DURATION)): str,
            vol.Optional(fnc(S2_MIN_DURATION)): str,
            vol.Optional(fnc(S2_TIMING_RESOLUTION)): vol.Datetime(format="00:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_SETPOINT_CAPABILITIES: Final = vol.Schema(  # min/max as per evohome
        {
            vol.Required(fnc(S2_CAN_CONTROL_HEAT)): bool,
            vol.Required(fnc(S2_MAX_HEAT_SETPOINT)): vol.All(
                float,
                vol.Range(min=MAX_HEAT_SETPOINT_LOWER, max=MAX_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(S2_MIN_HEAT_SETPOINT)): vol.All(
                float,
                vol.Range(min=MIN_HEAT_SETPOINT_LOWER, max=MIN_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(S2_CAN_CONTROL_COOL)): bool,
            vol.Optional(fnc(S2_MAX_COOL_SETPOINT)): float,  # TODO
            vol.Optional(fnc(S2_MIN_COOL_SETPOINT)): float,  # TODO
            # TODO: list should be a non-empty *subset* of all possible ZoneMode(s)
            vol.Required(fnc(S2_ALLOWED_SETPOINT_MODES)): [m.value for m in ZoneMode],
            vol.Required(fnc(S2_VALUE_RESOLUTION)): float,  # 0.5
            vol.Required(fnc(S2_MAX_DURATION)): str,  # "1.00:00:00"
            vol.Required(fnc(S2_TIMING_RESOLUTION)): vol.Datetime(
                format="00:%M:00"
            ),  # "00:10:00"
            vol.Optional(
                fnc(S2_VACATION_HOLD_CAPABILITIES)
            ): SCH_VACATION_HOLD_CAPABILITIES,  # non-evohome
            # vol.Optional((S2_ALLOWED_FAN_MODES)): dict,  # non-evohome
            vol.Optional(fnc(S2_SETPOINT_DEADBAND)): float,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_SCHEDULE_CAPABILITIES = factory_schedule_capabilities_response(fnc).extend(
        {
            vol.Required(fnc(S2_SETPOINT_VALUE_RESOLUTION)): float,
        },
        extra=vol.PREVENT_EXTRA,
    )

    # schedule_capabilities is required for evo, optional for FocusProWifiRetail
    return vol.Schema(
        {
            vol.Required(fnc(S2_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(S2_MODEL_TYPE)): vol.In(ZoneModelType),
            vol.Required(fnc(S2_NAME)): str,
            vol.Required(fnc(S2_SETPOINT_CAPABILITIES)): SCH_SETPOINT_CAPABILITIES,
            vol.Optional(fnc(S2_SCHEDULE_CAPABILITIES)): SCH_SCHEDULE_CAPABILITIES,
            vol.Required(fnc(S2_ZONE_TYPE)): vol.In(ZoneType),
            vol.Optional(fnc(S2_ALLOWED_FAN_MODES)): list,  # FocusProWifiRetail
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_tcs(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the TCS schema."""

    SCH_ALLOWED_SYSTEM_MODES: Final = vol.Any(
        factory_system_mode_perm(fnc), factory_system_mode_temp(fnc)
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(S2_MODEL_TYPE)): vol.In(TcsModelType),
            vol.Required(fnc(S2_ALLOWED_SYSTEM_MODES)): [SCH_ALLOWED_SYSTEM_MODES],
            vol.Required(fnc(S2_ZONES)): vol.All(
                [factory_zone(fnc)], vol.Length(min=1, max=12)
            ),
            vol.Optional(fnc(S2_DHW)): factory_dhw(fnc),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_gateway(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the gateway schema."""

    SCH_GATEWAY_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_ID)): str,
            vol.Required(fnc(S2_MAC)): str,
            vol.Required(fnc(S2_CRC)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_IS_WI_FI)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_INFO)): SCH_GATEWAY_INFO,
            vol.Required(fnc(S2_TEMPERATURE_CONTROL_SYSTEMS)): [factory_tcs(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_time_zone(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the time zone schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_TIME_ZONE_ID)): str,
            vol.Required(fnc(S2_DISPLAY_NAME)): str,
            vol.Required(fnc(S2_OFFSET_MINUTES)): int,
            vol.Required(fnc(S2_CURRENT_OFFSET_MINUTES)): int,
            vol.Required(fnc(S2_SUPPORTS_DAYLIGHT_SAVING)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_location_installation_info(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the location (config) schema."""

    SCH_LOCATION_OWNER: Final = vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), obfuscate),  # pyright: ignore[reportCallIssue]
            vol.Required(fnc(S2_FIRSTNAME)): str,
            vol.Required(fnc(S2_LASTNAME)): vol.All(str, obfuscate),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_LOCATION_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_ID)): str,
            vol.Required(fnc(S2_NAME)): str,  # e.g. "My Home"
            vol.Required(fnc(S2_STREET_ADDRESS)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_CITY)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_COUNTRY)): str,
            vol.Required(fnc(S2_POSTCODE)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_LOCATION_TYPE)): vol.In(LocationType),  # "Residential"
            vol.Required(fnc(S2_USE_DAYLIGHT_SAVE_SWITCHING)): bool,
            vol.Required(fnc(S2_TIME_ZONE)): factory_time_zone(fnc),
            vol.Required(fnc(S2_LOCATION_OWNER)): SCH_LOCATION_OWNER,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_INFO)): SCH_LOCATION_INFO,
            vol.Required(fnc(S2_GATEWAYS)): [factory_gateway(fnc)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_user_locations_installation_info(
    fnc: Callable[[str], str] = noop,
) -> vol.Schema:
    """Factory for the user locations (config) schema."""

    return vol.Schema(
        [factory_location_installation_info(fnc)],
        extra=vol.PREVENT_EXTRA,
    )
