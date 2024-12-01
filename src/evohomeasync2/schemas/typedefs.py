#!/usr/bin/env python3
"""evohomeasync schema - shared types (WIP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from .config import LocationType, SystemMode, TcsModelType, ZoneModelType, ZoneType

# TCC config, status dicts
_EvoLeafT = bool | float | int | str | list[str]  # Any
_EvoDictT = dict[str, Any]  # '_EvoDictT' | _EvoLeafT]
_EvoListT = list[_EvoDictT]
_EvoSchemaT = _EvoDictT | _EvoListT

# TCC other
_ModeT = str


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
# Entity Info/Config...


# GET /accountInfo
class EvoUsrConfigT(TypedDict):
    """Response to GET /accountInfo."""

    user_id: str


# GET /locations?userId={user_id}&allData=True
class EvoLocEntryT(TypedDict):
    """Response to GET /locations?userId={user_id}&allData=True.

    The response is a list of these dicts.
    """

    location_info: EvoLocConfigT
    gateways: list[EvoGwyEntryT]


class EvoLocConfigT(TypedDict):
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


class EvoGwyEntryT(TypedDict):
    gateway_info: EvoGwyConfigT
    temperature_control_systems: list[EvoTcsEntryT]


class EvoGwyConfigT(TypedDict):
    gateway_id: str
    mac: str
    crc: str
    is_wi_fi: str


class EvoAllowedSystemModeT(TypedDict):
    system_mode: SystemMode
    can_be_permanent: Literal[True]
    can_be_temporary: bool
    max_duration: NotRequired[str]
    timing_resolution: NotRequired[str]
    timing_mode: NotRequired[str]


class EvoTcsConfigT(TypedDict):
    system_id: str
    model_type: TcsModelType
    allowed_system_modes: list[EvoAllowedSystemModeT]


class EvoTcsEntryT(EvoTcsConfigT):
    # system_id: str
    # model_type: str
    # allowed_system_modes: list[dict[str, Any]]
    zones: list[EvoZonConfigT]
    dhw: dict[str, Any]


class EvoZonConfigT(TypedDict):
    zone_id: str
    model_type: ZoneModelType
    name: str
    setpoint_capabilities: dict[str, Any]
    schedule_capabilities: dict[str, Any]
    zone_type: ZoneType
    allowed_fan_modes: list[str]


class EvoDhwConfigT(TypedDict):
    dhw_id: str
    schedule_capabilities_response: dict[str, Any]
    dhw_state_capabilities_response: dict[str, Any]


#######################################################################################
# Tcs / Dhw / Zone Status...


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
# Dhw / Zone Schedule...


class SwitchpointDhwT(TypedDict):
    dhw_state: str
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


#######################################################################################


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


#######################################################################################


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
