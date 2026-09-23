"""Schema for the vendor's TCC v2 API - for GET/PUT schedule of Zone/DHW.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the probatio
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Literal, NotRequired, TypedDict, overload

import probatio as vol

from _evohome.helpers import camel_to_snake, noop

from .const import (
    S2_COOL_SETPOINT,
    S2_DAILY_SCHEDULES,
    S2_DAY_OF_WEEK,
    S2_DHW_STATE,
    S2_HEAT_SETPOINT,
    S2_SWITCHPOINTS,
    S2_TIME_OF_DAY,
    TccDayOfWeek,
    TccDhwState,
)
from .helpers import Case, factory_enum

if TYPE_CHECKING:
    from _evohome.helpers import Validator
    from evohomeasync2.typedefs import EvoDhwScheduleResponseT, EvoZonScheduleResponseT


#
# Vendor-native typed dicts for schedule URLs
# - this is the 'truth', as understood, for this undocumented API


# GET /domesticHotWater/{dhw_id}/schedule
class TccDhwDailySchedulesT(TypedDict):
    dailySchedules: list[TccDhwDayOfWeekT]


class TccDhwDayOfWeekT(TypedDict):
    dayOfWeek: TccDayOfWeek  # "Monday" … "Sunday"
    switchpoints: list[TccDhwSwitchpointT]


class TccDhwSwitchpointT(TypedDict):
    dhwState: TccDhwState  # "Off" | "On"
    timeOfDay: str  # "HH:MM:00"


# GET /temperatureZone/{zone_id}/schedule
class TccZonDailySchedulesT(TypedDict):
    dailySchedules: list[TccZonDayOfWeekT]


class TccZonDayOfWeekT(TypedDict):
    dayOfWeek: TccDayOfWeek  # "Monday" … "Sunday"
    switchpoints: list[TccZonSwitchpointT]


class TccZonSwitchpointT(TypedDict):
    coolSetpoint: NotRequired[float]  # not confirmed; included defensively
    heatSetpoint: float
    timeOfDay: str  # "HH:MM:00"


#
# Vendor-native schema factories for schedule URLs
# - used to validate / coerce data at runtime


# domesticHotWater (DHW) schedule schema factories
@overload
def factory_dhw_schedule(case: Literal[Case.VENDOR] = ...) -> Validator[TccDhwDailySchedulesT]: ...


@overload
def factory_dhw_schedule(case: Literal[Case.PYTHONIC]) -> Validator[EvoDhwScheduleResponseT]: ...


@overload
def factory_dhw_schedule(case: Case) -> Validator[TccDhwDailySchedulesT] | Validator[EvoDhwScheduleResponseT]: ...


def factory_dhw_schedule(
    case: Case = Case.VENDOR,
) -> Validator[TccDhwDailySchedulesT] | Validator[EvoDhwScheduleResponseT]:
    """Factory for the DHW schedule schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_GET_SWITCHPOINT_DHW: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DHW_STATE)): factory_enum(case, TccDhwState),
            vol.Required(fnc(S2_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_GET_DAY_OF_WEEK_DHW: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DAY_OF_WEEK)): factory_enum(case, TccDayOfWeek),
            vol.Required(fnc(S2_SWITCHPOINTS)): [SCH_GET_SWITCHPOINT_DHW],
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_DAILY_SCHEDULES)): [SCH_GET_DAY_OF_WEEK_DHW],
        },
        extra=vol.PREVENT_EXTRA,
    )


# temperatureZone (Zon) schedule schema factories
@overload
def factory_zon_schedule(case: Literal[Case.VENDOR] = ...) -> Validator[TccZonDailySchedulesT]: ...


@overload
def factory_zon_schedule(case: Literal[Case.PYTHONIC]) -> Validator[EvoZonScheduleResponseT]: ...


@overload
def factory_zon_schedule(case: Case) -> Validator[TccZonDailySchedulesT] | Validator[EvoZonScheduleResponseT]: ...


def factory_zon_schedule(
    case: Case = Case.VENDOR,
) -> Validator[TccZonDailySchedulesT] | Validator[EvoZonScheduleResponseT]:
    """Factory for the zone schedule schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_GET_SWITCHPOINT_ZONE: Final = vol.Schema(
        {
            vol.Optional(fnc(S2_COOL_SETPOINT)): float,  # an extrapolation
            vol.Required(fnc(S2_HEAT_SETPOINT)): vol.All(float, vol.Range(min=5, max=35)),
            vol.Required(fnc(S2_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_GET_DAY_OF_WEEK_ZONE: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DAY_OF_WEEK)): factory_enum(case, TccDayOfWeek),
            vol.Required(fnc(S2_SWITCHPOINTS)): [SCH_GET_SWITCHPOINT_ZONE],
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_DAILY_SCHEDULES)): [SCH_GET_DAY_OF_WEEK_ZONE],
        },
        extra=vol.PREVENT_EXTRA,
    )


#
# Vendor-native schemas for schedule URLs

# GET /domesticHotWater/{dhw_id}/schedule
TCC_GET_DHW_SCHEDULE: Final[Validator[TccDhwDailySchedulesT]] = factory_dhw_schedule()
TCC_PUT_DHW_SCHEDULE: Final = TCC_GET_DHW_SCHEDULE

# GET /temperatureZone/{zone_id}/schedule
TCC_GET_ZON_SCHEDULE: Final[Validator[TccZonDailySchedulesT]] = factory_zon_schedule()
TCC_PUT_ZON_SCHEDULE: Final = TCC_GET_ZON_SCHEDULE
