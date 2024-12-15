#!/usr/bin/env python3
"""evohomeasync schema - shared types (WIP)."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

from .config import (  # noqa: TC001
    DhwState,
    LocationType,
    SystemMode,
    TcsModelType,
    ZoneMode,
    ZoneModelType,
    ZoneType,
)


class TccAuthTokensResponseT(TypedDict):
    """Response to POST /Auth/OAuth/Token."""

    access_token: str
    expires_in: int
    scope: str
    refresh_token: str
    token_type: str


class EvoAuthTokensDictT(TypedDict):
    access_token: str
    access_token_expires: str  # dt.isoformat()
    refresh_token: str


#######################################################################################
# GET Entity Info/Config...
# NOTE: dicts are not completely typed, but all referenced keys should be present


# GET /accountInfo returns this dict
class EvoUsrConfigResponseT(TypedDict):
    """Response to GET /accountInfo."""

    user_id: str


# GET /locations?userId={user_id}&allData=True returns list of these dicts
class EvoLocConfigResponseT(TypedDict):
    """Response to GET /locations?userId={user_id}&allData=True.

    The response is a list of these dicts.
    """

    location_info: EvoLocConfigEntryT
    gateways: list[EvoGwyConfigResponseT]


class EvoLocConfigEntryT(TypedDict):
    """Location configuration information."""

    location_id: str
    name: str
    street_address: str
    city: str
    state: str
    country: str
    postcode: str
    type: str
    location_type: LocationType
    use_daylight_save_switching: bool
    time_zone: EvoTimeZoneInfoT
    location_owner: EvoLocationOwnerInfoT


class EvoTimeZoneInfoT(TypedDict):
    """Time zone information."""

    time_zone_id: str
    display_name: str
    offset_minutes: int
    current_offset_minutes: int
    supports_daylight_saving: bool


class EvoLocationOwnerInfoT(TypedDict):
    user_id: str
    username: str
    firstname: str
    lastname: str


class EvoGwyConfigResponseT(TypedDict):
    gateway_info: EvoGwyConfigEntryT
    temperature_control_systems: list[EvoTcsConfigResponseT]


class EvoGwyConfigEntryT(TypedDict):
    gateway_id: str
    mac: str
    crc: str
    is_wi_fi: bool


class EvoTcsConfigEntryT(TypedDict):
    system_id: str
    model_type: TcsModelType
    allowed_system_modes: list[EvoAllowedSystemModeT]


class EvoAllowedSystemModeT(TypedDict):
    system_mode: SystemMode
    can_be_permanent: Literal[True]
    can_be_temporary: bool
    max_duration: NotRequired[str]
    timing_resolution: NotRequired[str]
    timing_mode: NotRequired[str]


class EvoTcsConfigResponseT(EvoTcsConfigEntryT):
    # system_id: str
    # model_type: str
    # allowed_system_modes: list[dict[str, Any]]
    zones: list[EvoZonConfigResponseT]
    dhw: EvoDhwConfigResponseT


class EvoZonConfigResponseT(TypedDict):
    zone_id: str
    model_type: ZoneModelType
    name: str
    setpoint_capabilities: EvoZonSetpointCapabilitiesResponseT
    schedule_capabilities: EvoZonScheduleCapabilitiesResponseT
    zone_type: ZoneType
    allowed_fan_modes: list[str]


class EvoZonScheduleCapabilitiesResponseT(TypedDict):
    pass


class EvoZonSetpointCapabilitiesResponseT(TypedDict):
    allowed_setpoint_modes: list[ZoneMode]
    max_heat_setpoint: float
    min_heat_setpoint: float


class EvoZonConfigEntryT(EvoZonConfigResponseT):
    pass


class EvoDhwConfigResponseT(TypedDict):
    dhw_id: str
    schedule_capabilities_response: dict[str, Any]
    dhw_state_capabilities_response: dict[str, Any]


class EvoDhwConfigEntryT(EvoDhwConfigResponseT):
    pass


#######################################################################################
# GET Entity Status...
# NOTE: dicts are not completely typed, but all referenced keys should be present


# GET /location/{loc_id}/status?includeTemperatureControlSystems=True returns this dict
class EvoLocStatusResponseT(TypedDict):
    location_id: str
    gateways: list[EvoGwyStatusResponseT]


class EvoGwyStatusResponseT(TypedDict):
    gateway_id: str
    active_faults: list[EvoActiveFaultResponseT]
    temperature_control_systems: list[EvoTcsStatusResponseT]


class EvoActiveFaultResponseT(TypedDict):
    fault_type: str
    since: str


class EvoTcsStatusResponseT(TypedDict):
    system_id: str
    active_faults: list[EvoActiveFaultResponseT]
    system_mode_status: EvoSystemModeStatusResponseT
    zones: list[EvoZonStatusResponseT]
    dhw: NotRequired[EvoDhwStatusResponseT]


class EvoSystemModeStatusResponseT(TypedDict):
    mode: SystemMode
    is_permanent: bool
    until: NotRequired[str]


class EvoZonStatusResponseT(TypedDict):
    zone_id: str
    active_faults: list[EvoActiveFaultResponseT]
    setpoint_status: EvoZonSetpointStatusResponseT
    temperature_status: EvoTemperatureStatusResponseT
    name: str


class EvoZonSetpointStatusResponseT(TypedDict):
    setpoint_mode: ZoneMode
    target_heat_temperature: int
    until: NotRequired[str]


class EvoTemperatureStatusResponseT(TypedDict):
    is_available: bool
    temperature: NotRequired[int]


class EvoDhwStatusResponseT(TypedDict):
    dhw_id: str
    active_faults: list[EvoActiveFaultResponseT]
    state_status: EvoDhwStateStatusResponseT
    temperature_status: EvoTemperatureStatusResponseT


class EvoDhwStateStatusResponseT(TypedDict):
    mode: ZoneMode
    state: DhwState


# namespace for the above GET status responses
class EvoStatusResponse:
    LOC: TypeAlias = EvoLocStatusResponseT
    GWY: TypeAlias = EvoGwyStatusResponseT
    TCS: TypeAlias = EvoTcsStatusResponseT
    ZON: TypeAlias = EvoZonStatusResponseT
    DHW: TypeAlias = EvoDhwStatusResponseT


#######################################################################################


class EvoZoneStatusT(TypedDict):
    mode: str
    is_permanent: bool


class EvoSystemModeStatusT(TypedDict):
    mode: SystemMode
    is_permanent: bool


class EvoTcsStatusT(TypedDict):
    system_id: str
    system_mode_status: dict[str, Any]


#######################################################################################
# GET/PUT DHW / Zone Schedules...
#


class SwitchpointDhwT(TypedDict):
    dhw_state: DhwState
    time_of_day: str


class DayOfWeekDhwT(TypedDict):
    day_of_week: str
    switchpoints: list[SwitchpointDhwT]


class DailySchedulesDhwT(TypedDict):
    daily_schedules: list[DayOfWeekDhwT]


# for export/import to/from file
class EvoScheduleDhwT(DailySchedulesDhwT):
    dhw_id: str
    name: NotRequired[str]


#


class SwitchpointZoneT(TypedDict):
    heat_setpoint: float
    time_of_day: str


class DayOfWeekZoneT(TypedDict):
    day_of_week: str
    switchpoints: list[SwitchpointZoneT]


class DailySchedulesZoneT(TypedDict):
    daily_schedules: list[DayOfWeekZoneT]


# for export/import to/from file
class EvoScheduleZoneT(DailySchedulesZoneT):
    zone_id: str
    name: NotRequired[str]


#


class SwitchpointT(TypedDict):
    time_of_day: str
    dhw_state: NotRequired[str]  # mutex with heat_setpoint
    heat_setpoint: NotRequired[float]


class DayOfWeekT(TypedDict):
    day_of_week: str
    switchpoints: list[SwitchpointT]


class DailySchedulesT(TypedDict):
    daily_schedules: list[DayOfWeekT]


# for export/import to/from file
class EvoScheduleT(DailySchedulesT):
    dhw_id: str
    name: NotRequired[str]
