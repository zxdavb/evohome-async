"""Schema for vendor's TCC v2 API - for GET/PUT schedule of Zone/DHW.

The convention for JSON keys is camelCase, but the API appears to be case-insensitive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypedDict

import voluptuous as vol

from evohome.helpers import noop

from .const import (
    S2_COOL_SETPOINT,
    S2_DAILY_SCHEDULES,
    S2_DAY_OF_WEEK,
    S2_DHW_STATE,
    S2_HEAT_SETPOINT,
    S2_SWITCHPOINTS,
    S2_TIME_OF_DAY,
    DayOfWeek,
    DhwState,
)

if TYPE_CHECKING:
    from collections.abc import Callable


#######################################################################################
# GET/PUT DHW / Zone Schedules...
#


class TccDhwSwitchpointT(TypedDict):
    dhwState: DhwState  # Off, On
    timeOfDay: str


class TccDhwDayOfWeekT(TypedDict):
    dayOfWeek: str
    switchpoints: list[TccDhwSwitchpointT]


class TccDhwDailySchedulesT(TypedDict):
    dailySchedules: list[TccDhwDayOfWeekT]


class TccZonSwitchpointT(TypedDict):
    heatSetpoint: float
    timeOfDay: str


class TccZonDayOfWeekT(TypedDict):
    dayOfWeek: str
    switchpoints: list[TccZonSwitchpointT]


class TccZonDailySchedulesT(TypedDict):
    dailySchedules: list[TccZonDayOfWeekT]


#
# These are returned from vendor's API (GET)...
def factory_dhw_schedule(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the DHW schedule schema."""

    SCH_GET_SWITCHPOINT_DHW: Final = vol.Schema(  # TODO: checkme
        {
            vol.Required(fnc(S2_DHW_STATE)): vol.In(DhwState),
            vol.Required(fnc(S2_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_GET_DAY_OF_WEEK_DHW: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DAY_OF_WEEK)): vol.In(DayOfWeek),
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


def factory_zon_schedule(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the zone schedule schema."""

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
            # l.Required(fnc(S2_DAY_OF_WEEK)): vol.All(int, vol.Range(min=0, max=6)),  # 0 is Monday
            vol.Required(fnc(S2_DAY_OF_WEEK)): vol.In(DayOfWeek),
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
# These are as to be provided to the vendor's API (PUT)...
# This is after modified by evohome-client (PUT), an evohome-client anachronism?
def _out_factory_put_schedule_dhw(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the zone schedule schema."""

    SCH_PUT_SWITCHPOINT_DHW: Final = vol.Schema(  # TODO: checkme
        {
            vol.Required(fnc(S2_DHW_STATE)): vol.In(DhwState),
            vol.Required(fnc(S2_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_PUT_DAY_OF_WEEK_DHW: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DAY_OF_WEEK)): vol.All(
                int, vol.Range(min=0, max=6)
            ),  # 0 is Monday
            vol.Required(fnc(S2_SWITCHPOINTS)): [SCH_PUT_SWITCHPOINT_DHW],
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_DAILY_SCHEDULES)): [SCH_PUT_DAY_OF_WEEK_DHW],
        },
        extra=vol.PREVENT_EXTRA,
    )


def _out_factory_put_schedule_zone(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the zone schedule schema."""

    SCH_PUT_SWITCHPOINT_ZONE: Final = vol.Schema(
        {  # NOTE: S2_HEAT_SETPOINT is not .capitalized()
            #
            vol.Required(S2_HEAT_SETPOINT): vol.All(float, vol.Range(min=5, max=35)),
            vol.Required(fnc(S2_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
        },
        extra=vol.PREVENT_EXTRA,
    )

    SCH_PUT_DAY_OF_WEEK_ZONE: Final = vol.Schema(
        {
            vol.Required(fnc(S2_DAY_OF_WEEK)): vol.All(
                int, vol.Range(min=0, max=6)
            ),  # 0 is Monday
            vol.Required(fnc(S2_SWITCHPOINTS)): [SCH_PUT_SWITCHPOINT_ZONE],
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(
        {
            vol.Required(fnc(S2_DAILY_SCHEDULES)): [SCH_PUT_DAY_OF_WEEK_ZONE],
        },
        extra=vol.PREVENT_EXTRA,
    )
