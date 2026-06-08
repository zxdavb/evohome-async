"""Schema for the vendor's TCC v2 API - for GET config of user's Installation.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the voluptuous
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import Final, Literal, NotRequired, TypedDict

import voluptuous as vol

from _evohome.helpers import camel_to_snake, noop, redact

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
    TccDhwState,
    TccFanMode,
    TccLocationType,
    TccSystemMode,
    TccTcsModelType,
    TccTimingMode,
    TccZoneMode,
    TccZoneModelType,
    TccZoneType,
)
from .helpers import Case, factory_enum

# These are best guess, mostly based upon evohome
_MAX_HEAT_SETPOINT_LOWER: Final = 21.0
_MAX_HEAT_SETPOINT_UPPER: Final = 35.0

_MIN_HEAT_SETPOINT_LOWER: Final = 4.5
_MIN_HEAT_SETPOINT_UPPER: Final = 21.0

_MAX_NUM_ZONES_PER_TCS: Final = 12  # unused; some non-evohome systems supported 16
_MIN_NUM_ZONES_PER_TCS: Final = 1


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
    locationType: TccLocationType
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
    modelType: TccTcsModelType
    allowedSystemModes: list[TccAllowedSystemModeResponseT]


class TccAllowedSystemModeResponseT(TypedDict):
    systemMode: TccSystemMode
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
    modelType: TccZoneModelType
    name: str
    setpointCapabilities: TccZonSetpointCapabilitiesResponseT
    scheduleCapabilities: TccZonScheduleCapabilitiesResponseT
    zoneType: TccZoneType
    allowedFanModes: list[str]


class TccZonScheduleCapabilitiesResponseT(TypedDict):
    maxSwitchpointsPerDay: int
    minSwitchpointsPerDay: int
    timingResolution: str
    setpointValueResolution: float


class TccZonSetpointCapabilitiesResponseT(TypedDict):
    allowedSetpointModes: list[TccZoneMode]
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
    maxSwitchpointsPerDay: int
    minSwitchpointsPerDay: int
    timingResolution: str


class TccDhwStateCapabilitiesResponseT(TypedDict):
    allowedStates: list[TccDhwState]
    allowedModes: list[TccZoneMode]
    maxDuration: str
    timingResolution: str


class TccDhwConfigEntryT(TccDhwConfigResponseT):
    pass


def factory_system_mode(case: Case = Case.VENDOR) -> vol.All:
    """Factory for the allowed system mode schema.

    The duration-related keys are required when canBeTemporary is True, and must be
    absent when it is False.

    An example:
        "allowedSystemModes": [
            {"systemMode": "HeatingOff",    "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "Auto",          "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "AutoWithReset", "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "AutoWithEco",   "canBePermanent": true, "canBeTemporary": true, "maxDuration":  "1.00:00:00", "timingResolution":   "01:00:00", "timingMode": "Duration"},
            {"systemMode": "Away",          "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"},
            {"systemMode": "DayOff",        "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"},
            {"systemMode": "Custom",        "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"}
        ]
    """

    fnc = noop if case is Case.VENDOR else camel_to_snake

    system_mode = fnc(S2_SYSTEM_MODE)
    can_be_permanent = fnc(S2_CAN_BE_PERMANENT)
    can_be_temporary = fnc(S2_CAN_BE_TEMPORARY)
    max_duration = fnc(S2_MAX_DURATION)
    timing_resolution = fnc(S2_TIMING_RESOLUTION)
    timing_mode = fnc(S2_TIMING_MODE)

    def check_can_be_one_of(config: dict[str, object]) -> dict[str, object]:
        if not (config[can_be_permanent] or config[can_be_temporary]):
            raise vol.Invalid(
                f"at least one of {can_be_permanent}, {can_be_temporary} must be true"
            )
        return config

    def check_duration_keys(config: dict[str, object]) -> dict[str, object]:
        duration_keys = (max_duration, timing_resolution, timing_mode)
        if config[can_be_temporary]:
            if missing := [k for k in duration_keys if k not in config]:
                raise vol.Invalid("required key not provided", path=[missing[0]])
        elif extra := [k for k in duration_keys if k in config]:
            raise vol.Invalid("extra keys not allowed", path=[extra[0]])
        return config

    return vol.All(
        vol.Schema(
            {
                vol.Required(system_mode): factory_enum(case, TccSystemMode),
                vol.Required(can_be_permanent): bool,
                vol.Required(can_be_temporary): bool,
                vol.Optional(max_duration): str,  # "99.00:00:00"
                vol.Optional(timing_resolution): str,  # "1.00:00:00"
                vol.Optional(timing_mode): factory_enum(case, TccTimingMode),
            },
            extra=vol.PREVENT_EXTRA,
        ),
        check_can_be_one_of,
        check_duration_keys,
    )


def factory_schedule_capabilities_response(
    case: Case = Case.VENDOR,
) -> vol.Schema:
    """Factory for the schedule_capabilities_response schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

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


def factory_dhw(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the DHW schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_DHW_STATE_CAPABILITIES_RESPONSE: Final = vol.Schema(
        {
            # TODO: list should be a non-empty *subset* of all possible TccDhwState(s)
            vol.Required(fnc(S2_ALLOWED_STATES)): [factory_enum(case, TccDhwState)],
            # TODO: list should be a non-empty *subset* of all possible TccZoneMode(s)
            vol.Required(fnc(S2_ALLOWED_MODES)): [factory_enum(case, TccZoneMode)],
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
            ): factory_schedule_capabilities_response(case),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_zone(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the zone schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_FAN_MODE: Final = vol.Schema(  # noqa: F841
        {
            vol.Required(fnc(S2_FAN_MODE)): factory_enum(case, TccFanMode),
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
                vol.Range(min=_MAX_HEAT_SETPOINT_LOWER, max=_MAX_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(S2_MIN_HEAT_SETPOINT)): vol.All(
                float,
                vol.Range(min=_MIN_HEAT_SETPOINT_LOWER, max=_MIN_HEAT_SETPOINT_UPPER),
            ),
            vol.Required(fnc(S2_CAN_CONTROL_COOL)): bool,
            vol.Optional(fnc(S2_MAX_COOL_SETPOINT)): float,  # TODO
            vol.Optional(fnc(S2_MIN_COOL_SETPOINT)): float,  # TODO
            # TODO: list should be a non-empty *subset* of all possible TccZoneMode(s)
            vol.Required(fnc(S2_ALLOWED_SETPOINT_MODES)): [
                factory_enum(case, TccZoneMode)
            ],
            vol.Required(fnc(S2_VALUE_RESOLUTION)): float,  # 0.5
            vol.Required(fnc(S2_MAX_DURATION)): str,  # "1.00:00:00"
            vol.Required(fnc(S2_TIMING_RESOLUTION)): vol.Datetime(
                format="00:%M:00"
            ),  # "00:10:00"
            vol.Optional(
                fnc(S2_VACATION_HOLD_CAPABILITIES)
            ): SCH_VACATION_HOLD_CAPABILITIES,  # non-evohome
            vol.Optional(fnc(S2_ALLOWED_FAN_MODES)): factory_enum(
                case, TccFanMode
            ),  # non-evohome
            vol.Optional(fnc(S2_SETPOINT_DEADBAND)): float,  # non-evohome
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_SCHEDULE_CAPABILITIES = factory_schedule_capabilities_response(case).extend(
        {
            vol.Required(fnc(S2_SETPOINT_VALUE_RESOLUTION)): float,
        },
        extra=vol.PREVENT_EXTRA,
    )

    # schedule_capabilities is required for evo, optional for FocusProWifiRetail
    return vol.Schema(
        {
            vol.Required(fnc(S2_ZONE_ID)): vol.Match(REGEX_ZONE_ID),
            vol.Required(fnc(S2_MODEL_TYPE)): factory_enum(case, TccZoneModelType),
            vol.Required(fnc(S2_NAME)): str,
            vol.Required(fnc(S2_SETPOINT_CAPABILITIES)): SCH_SETPOINT_CAPABILITIES,
            vol.Optional(fnc(S2_SCHEDULE_CAPABILITIES)): SCH_SCHEDULE_CAPABILITIES,
            vol.Required(fnc(S2_ZONE_TYPE)): factory_enum(case, TccZoneType),
            vol.Optional(fnc(S2_ALLOWED_FAN_MODES)): list,  # FocusProWifiRetail
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_tcs(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the TCS schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    return vol.Schema(
        {
            vol.Required(fnc(S2_SYSTEM_ID)): vol.Match(REGEX_SYSTEM_ID),
            vol.Required(fnc(S2_MODEL_TYPE)): factory_enum(case, TccTcsModelType),
            vol.Required(fnc(S2_ALLOWED_SYSTEM_MODES)): [factory_system_mode(case)],
            vol.Required(fnc(S2_ZONES)): vol.All(
                [factory_zone(case)], vol.Length(min=_MIN_NUM_ZONES_PER_TCS)
            ),
            vol.Optional(fnc(S2_DHW)): factory_dhw(case),
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_gateway(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the gateway schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_GATEWAY_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_ID)): str,
            vol.Required(fnc(S2_MAC)): str,
            vol.Required(fnc(S2_CRC)): vol.All(str, redact),
            vol.Required(fnc(S2_IS_WI_FI)): bool,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_GATEWAY_INFO)): SCH_GATEWAY_INFO,
            vol.Required(fnc(S2_TEMPERATURE_CONTROL_SYSTEMS)): [factory_tcs(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_time_zone(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the time zone schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

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
    case: Case = Case.VENDOR,
) -> vol.Schema:
    """Factory for the location (config) schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_LOCATION_OWNER: Final = vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), redact),  # pyright: ignore[reportCallIssue]
            vol.Required(fnc(S2_FIRSTNAME)): str,
            vol.Required(fnc(S2_LASTNAME)): vol.All(str, redact),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_LOCATION_INFO: Final = vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_ID)): str,
            vol.Required(fnc(S2_NAME)): str,  # e.g. "My Home"
            vol.Required(fnc(S2_STREET_ADDRESS)): vol.All(str, redact),
            vol.Required(fnc(S2_CITY)): vol.All(str, redact),
            vol.Required(fnc(S2_COUNTRY)): str,
            vol.Required(fnc(S2_POSTCODE)): vol.All(str, redact),
            vol.Required(fnc(S2_LOCATION_TYPE)): factory_enum(
                case, TccLocationType
            ),  # "Residential"
            vol.Required(fnc(S2_USE_DAYLIGHT_SAVE_SWITCHING)): bool,
            vol.Required(fnc(S2_TIME_ZONE)): factory_time_zone(case),
            vol.Required(fnc(S2_LOCATION_OWNER)): SCH_LOCATION_OWNER,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_LOCATION_INFO)): SCH_LOCATION_INFO,
            vol.Required(fnc(S2_GATEWAYS)): [factory_gateway(case)],
        },
        extra=vol.PREVENT_EXTRA,
    )


def factory_user_locations_installation_info(
    case: Case = Case.VENDOR,
) -> vol.Schema:
    """Factory for the user locations (config) schema."""

    return vol.Schema(
        [factory_location_installation_info(case)],
        extra=vol.PREVENT_EXTRA,
    )


# GET /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
TCC_GET_USR_LOCATIONS: Final = factory_user_locations_installation_info()

# GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True
TCC_GET_LOC_INSTALLATION_INFO: Final = factory_location_installation_info()
