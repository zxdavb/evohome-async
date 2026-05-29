"""Schema for vendor's TCC v2 API - for GET/PUT schedule of Zone/DHW.

The convention for JSON keys is camelCase, but the API appears to be case-insensitive.
"""

from __future__ import annotations

from typing import Final, NotRequired, TypedDict

import voluptuous as vol

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

#######################################################################################
# GET/PUT DHW / Zone Schedules...
#


class TccDhwSwitchpointT(TypedDict):
    dhwState: TccDhwState  # "Off" | "On"
    timeOfDay: str  # "HH:MM:00"


class TccDhwDayOfWeekT(TypedDict):
    dayOfWeek: TccDayOfWeek  # "Monday" … "Sunday"
    switchpoints: list[TccDhwSwitchpointT]


class TccDhwDailySchedulesT(TypedDict):
    dailySchedules: list[TccDhwDayOfWeekT]


class TccZonSwitchpointT(TypedDict):
    coolSetpoint: NotRequired[float]  # not confirmed; included defensively
    heatSetpoint: float
    timeOfDay: str  # "HH:MM:00"


class TccZonDayOfWeekT(TypedDict):
    dayOfWeek: TccDayOfWeek  # "Monday" … "Sunday"
    switchpoints: list[TccZonSwitchpointT]


class TccZonDailySchedulesT(TypedDict):
    dailySchedules: list[TccZonDayOfWeekT]


#
# These are returned from vendor's API (GET)...
def factory_dhw_schedule(case: Case = Case.VENDOR) -> vol.Schema:
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


def factory_zon_schedule(case: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the zone schedule schema."""

    fnc = noop if case is Case.VENDOR else camel_to_snake

    SCH_GET_SWITCHPOINT_ZONE: Final = vol.Schema(
        {
            vol.Optional(fnc(S2_COOL_SETPOINT)): float,  # an extrapolation
            vol.Required(fnc(S2_HEAT_SETPOINT)): vol.All(
                float, vol.Range(min=5, max=35)
            ),
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


# GET /domesticHotWater/{dhw_id}/schedule
TCC_GET_DHW_SCHEDULE: Final = factory_dhw_schedule()

# PUT /domesticHotWater/{dhw_id}/schedule
TCC_PUT_DHW_SCHEDULE: Final = TCC_GET_DHW_SCHEDULE

# GET /temperatureZone/{zone_id}/schedule
TCC_GET_ZON_SCHEDULE: Final = factory_zon_schedule()

# PUT /temperatureZone/{zone_id}/schedule
TCC_PUT_ZON_SCHEDULE: Final = TCC_GET_ZON_SCHEDULE


# for convenience...
def factory_get_schedule(_: Case = Case.VENDOR) -> vol.Schema:
    """Factory for the schedule schema."""

    return vol.Schema(
        vol.Any(TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE),
        extra=vol.PREVENT_EXTRA,
    )


TCC_GET_SCHEDULE: Final = factory_get_schedule()
TCC_PUT_SCHEDULE: Final = TCC_GET_SCHEDULE
