#!/usr/bin/env python3
"""evohomeasync schema - for RESTful API Account JSON."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

import voluptuous as vol

from evohome.helpers import camel_to_pascal, noop

from .. import exceptions as exc
from .const import (
    DAYS_OF_WEEK,
    S2_COOL_SETPOINT,
    S2_DAILY_SCHEDULES,
    S2_DAY_OF_WEEK,
    S2_DHW_STATE,
    S2_HEAT_SETPOINT,
    S2_OFF,
    S2_ON,
    S2_SWITCHPOINTS,
    S2_TIME_OF_DAY,
    DayOfWeek,
)
from .typedefs import _EvoDictT, _EvoListT

_ScheduleT = dict[str, dict[str, Any]]


#
# These are returned from vendor's API (GET)...
def factory_schedule_dhw(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the DHW schedule schema."""

    SCH_GET_SWITCHPOINT_DHW: Final = vol.Schema(  # TODO: checkme
        {
            vol.Required(fnc(S2_DHW_STATE)): vol.Any(S2_ON, S2_OFF),
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


def factory_schedule_zone(fnc: Callable[[str], str] = noop) -> vol.Schema:
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
def _factory_put_schedule_dhw(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the zone schedule schema."""

    SCH_PUT_SWITCHPOINT_DHW: Final = vol.Schema(  # TODO: checkme
        {
            vol.Required(fnc(S2_DHW_STATE)): vol.Any(S2_ON, S2_OFF),
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


def _factory_put_schedule_zone(fnc: Callable[[str], str] = noop) -> vol.Schema:
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


#
# Converters (NOTE: potential for circular imports)...
def _convert_to_put_schedule(schedule: _EvoDictT) -> _EvoDictT:
    """Convert a schedule to the format used by our get/set_schedule() methods.

    The 'raw' schedule format is the one returned by the vendor's RESTful API (GET).
    """

    from . import SCH_GET_SCHEDULE

    if not schedule:
        raise exc.InvalidScheduleError(f"Null schedule: {schedule}")

    try:
        SCH_GET_SCHEDULE(schedule)
    except vol.Invalid as err:
        raise exc.InvalidScheduleError(f"Invalid schedule: {err}") from err

    put_schedule: dict[str, _EvoListT] = {}
    put_schedule[camel_to_pascal(S2_DAILY_SCHEDULES)] = []

    for day_of_week, day_schedule in enumerate(schedule[S2_DAILY_SCHEDULES]):
        put_day_schedule: _EvoDictT = {camel_to_pascal(S2_DAY_OF_WEEK): day_of_week}
        put_switchpoints: _EvoListT = []

        for get_sp in day_schedule[S2_SWITCHPOINTS]:
            if S2_HEAT_SETPOINT in get_sp:
                # NOTE: this key is not converted to PascalCase
                put_sp = {S2_HEAT_SETPOINT: get_sp[S2_HEAT_SETPOINT]}  #  camelCase
            else:
                put_sp = {camel_to_pascal(S2_DHW_STATE): get_sp[S2_DHW_STATE]}

            put_sp[camel_to_pascal(S2_TIME_OF_DAY)] = get_sp[S2_TIME_OF_DAY]
            put_switchpoints.append(put_sp)

        put_day_schedule[camel_to_pascal(S2_SWITCHPOINTS)] = put_switchpoints
        put_schedule[camel_to_pascal(S2_DAILY_SCHEDULES)].append(put_day_schedule)

    return put_schedule


def _convert_to_get_schedule(schedule: _EvoDictT) -> _EvoDictT:
    """Convert a schedule to the format returned by the vendor's RESTful API (GET)."""

    from . import SCH_PUT_SCHEDULE

    try:
        SCH_PUT_SCHEDULE(schedule)
    except vol.Invalid as err:
        raise exc.InvalidScheduleError(f"Invalid schedule: {err}") from err

    get_schedule: dict[str, _EvoListT] = {}
    get_schedule[S2_DAILY_SCHEDULES] = []

    for put_day_schedule in schedule[camel_to_pascal(S2_DAILY_SCHEDULES)]:
        day_of_week = put_day_schedule[camel_to_pascal(S2_DAY_OF_WEEK)]
        get_day_schedule: _EvoDictT = {S2_DAY_OF_WEEK: DAYS_OF_WEEK[day_of_week]}
        get_switchpoints: _EvoListT = []

        for put_sp in put_day_schedule[camel_to_pascal(S2_SWITCHPOINTS)]:
            if S2_HEAT_SETPOINT in put_sp:
                # NOTE: this key is not converted to pascal_case in evohomeclient2
                get_sp = {S2_HEAT_SETPOINT: put_sp[S2_HEAT_SETPOINT]}
            else:
                get_sp = {S2_DHW_STATE: put_sp[camel_to_pascal(S2_DHW_STATE)]}

            get_sp[S2_TIME_OF_DAY] = put_sp[camel_to_pascal(S2_TIME_OF_DAY)]
            get_switchpoints.append(get_sp)

        get_day_schedule[S2_SWITCHPOINTS] = get_switchpoints
        get_schedule[S2_DAILY_SCHEDULES].append(get_day_schedule)

    return get_schedule
