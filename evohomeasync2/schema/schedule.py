#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Account JSON."""
from __future__ import annotations

from .const import (
    SZ_DAILY_SCHEDULES,
    SZ_DAY_OF_WEEK,
    SZ_DHW_STATE,
    SZ_HEAT_SETPOINT,
    SZ_OFF,
    SZ_ON,
    SZ_SWITCHPOINTS,
    SZ_TEMPERATURE,
    SZ_TIME_OF_DAY,
)
from .const import DAYS_OF_WEEK
from .helpers import vol, pascal_case  # voluptuous
from .typing import _EvoDictT, _EvoListT


#
# These are returned from vendor's API (GET)...
SCH_GET_SWITCHPOINT_DHW = vol.Schema(  # TODO: checkme
    {
        vol.Required(SZ_DHW_STATE): vol.Any(SZ_ON, SZ_OFF),
        vol.Required(SZ_TIME_OF_DAY): vol.Datetime(format="%H:%M:00"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_SWITCHPOINT_ZONE = vol.Schema(
    {
        vol.Required(SZ_HEAT_SETPOINT): vol.All(float, vol.Range(min=5, max=35)),
        vol.Required(SZ_TIME_OF_DAY): vol.Datetime(format="%H:%M:00"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_DAY_OF_WEEK_DHW = vol.Schema(
    {
        vol.Required(SZ_DAY_OF_WEEK): vol.Any(*DAYS_OF_WEEK),
        vol.Required(SZ_SWITCHPOINTS): [SCH_GET_SWITCHPOINT_DHW],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_DAY_OF_WEEK_ZONE = vol.Schema(
    {
        vol.Required(SZ_DAY_OF_WEEK): vol.Any(*DAYS_OF_WEEK),
        vol.Required(SZ_SWITCHPOINTS): [SCH_GET_SWITCHPOINT_ZONE],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_SCHEDULE_DHW = vol.Schema(
    {
        vol.Required(SZ_DAILY_SCHEDULES): [SCH_GET_DAY_OF_WEEK_DHW],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_SCHEDULE_ZONE = vol.Schema(
    {
        vol.Required(SZ_DAILY_SCHEDULES): [SCH_GET_DAY_OF_WEEK_ZONE],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_GET_SCHEDULE = vol.Schema(  # PUT /{self._type}/{self._id}/schedule
    vol.Any(SCH_GET_SCHEDULE_DHW, SCH_GET_SCHEDULE_ZONE),
    extra=vol.PREVENT_EXTRA,
)


#
# These are as to be provided to the vendor's API (PUT)...
# This is after modified by evohome-client (PUT), an evohome-client anachronism?
SCH_PUT_SWITCHPOINT_DHW = vol.Schema(  # TODO: checkme
    {
        vol.Required(pascal_case(SZ_DHW_STATE)): vol.Any(SZ_ON, SZ_OFF),
        vol.Required(pascal_case(SZ_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_SWITCHPOINT_ZONE = vol.Schema(
    {  # NOTE: SZ_HEAT_SETPOINT is not .capitalized()
        vol.Required(SZ_HEAT_SETPOINT): vol.All(float, vol.Range(min=5, max=35)),
        vol.Required(pascal_case(SZ_TIME_OF_DAY)): vol.Datetime(format="%H:%M:00"),
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_DAY_OF_WEEK_DHW = vol.Schema(
    {
        vol.Required(pascal_case(SZ_DAY_OF_WEEK)): vol.Any(
            vol.All(int, vol.Range(min=0, max=6)),  # 0 is Monday
        ),
        vol.Required(pascal_case(SZ_SWITCHPOINTS)): [SCH_PUT_SWITCHPOINT_DHW],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_DAY_OF_WEEK_ZONE = vol.Schema(
    {
        vol.Required(pascal_case(SZ_DAY_OF_WEEK)): vol.Any(
            vol.All(int, vol.Range(min=0, max=6)),  # 0 is Monday
        ),
        vol.Required(pascal_case(SZ_SWITCHPOINTS)): [SCH_PUT_SWITCHPOINT_ZONE],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_SCHEDULE_DHW = vol.Schema(
    {
        vol.Required(pascal_case(SZ_DAILY_SCHEDULES)): [SCH_PUT_DAY_OF_WEEK_DHW],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_SCHEDULE_ZONE = vol.Schema(
    {
        vol.Required(pascal_case(SZ_DAILY_SCHEDULES)): [SCH_PUT_DAY_OF_WEEK_ZONE],
    },
    extra=vol.PREVENT_EXTRA,
)

SCH_PUT_SCHEDULE = vol.Schema(  # PUT /{self._type}/{self._id}/schedule
    vol.Any(SCH_PUT_SCHEDULE_DHW, SCH_PUT_SCHEDULE_ZONE),
    extra=vol.PREVENT_EXTRA,
)


#
#
def _convert_to_put_schedule_classic(raw_schedule: _EvoDictT) -> _EvoDictT:
    """Convert a schedule as per evohomeclient2.schedule()."""

    import json

    MAPPINGS = [
        (SZ_DAILY_SCHEDULES, "DailySchedules"),
        (SZ_DAY_OF_WEEK, "DayOfWeek"),
        (SZ_DHW_STATE, "DhwState"),
        (SZ_SWITCHPOINTS, "Switchpoints"),
        (SZ_TEMPERATURE, "TargetTemperature"),  # should have been SZ_HEAT_SETPOINT?
        (SZ_TIME_OF_DAY, "TimeOfDay"),
    ]

    response_data = json.dumps(raw_schedule)

    for from_key, to_key in MAPPINGS:  # an anachronism from evohome-client
        response_data = response_data.replace(from_key, to_key)

    data: _EvoDictT = json.loads(response_data)

    # change the day name string to an ordinal (Monday = 0)
    for day_of_week, setpoints in enumerate(data[pascal_case(SZ_DAILY_SCHEDULES)]):
        setpoints[pascal_case(SZ_DAY_OF_WEEK)] = day_of_week

    return data


def convert_to_put_schedule(get_schedule: _EvoDictT) -> _EvoDictT:
    """Convert a schedule to the format used by our get/set_schedule() methods.

    The 'raw' schedule format is the one returned by the vendor's RESTful API (GET).
    """

    put_schedule: dict[str, _EvoListT] = {}
    put_schedule[pascal_case(SZ_DAILY_SCHEDULES)] = []

    for day_of_week, get_schedule in enumerate(get_schedule[SZ_DAILY_SCHEDULES]):
        put_day_schedule: _EvoDictT = {pascal_case(SZ_DAY_OF_WEEK): day_of_week}
        put_switchpoints: _EvoListT = []

        for get_sp in get_schedule[SZ_SWITCHPOINTS]:
            if SZ_HEAT_SETPOINT in get_sp:
                # NOTE: this key is not converted to pascal_case in evohomeclient2
                put_sp = {SZ_HEAT_SETPOINT: get_sp[SZ_HEAT_SETPOINT]}
            else:
                put_sp = {pascal_case(SZ_DHW_STATE): get_sp[SZ_DHW_STATE]}

            put_sp[pascal_case(SZ_TIME_OF_DAY)] = get_sp[SZ_TIME_OF_DAY]
            put_switchpoints.append(put_sp)

        put_day_schedule[pascal_case(SZ_SWITCHPOINTS)] = put_switchpoints
        put_schedule[pascal_case(SZ_DAILY_SCHEDULES)].append(put_day_schedule)

    return put_schedule


def convert_to_get_schedule(put_schedule: _EvoDictT) -> _EvoDictT:
    """Convert a schedule to the format returned by the vendor's RESTful API (GET)."""

    get_schedule: dict[str, _EvoListT] = {}
    get_schedule[SZ_DAILY_SCHEDULES] = []

    for put_day_schedule in put_schedule[pascal_case(SZ_DAILY_SCHEDULES)]:
        day_of_week = put_day_schedule[pascal_case(SZ_DAY_OF_WEEK)]
        get_day_schedule: _EvoDictT = {SZ_DAY_OF_WEEK: DAYS_OF_WEEK[day_of_week]}
        get_switchpoints: _EvoListT = []

        for put_sp in put_day_schedule[pascal_case(SZ_SWITCHPOINTS)]:
            if SZ_HEAT_SETPOINT in put_sp:
                # NOTE: this key is not converted to pascal_case in evohomeclient2
                get_sp = {SZ_HEAT_SETPOINT: put_sp[SZ_HEAT_SETPOINT]}
            else:
                get_sp = {SZ_DHW_STATE: put_sp[pascal_case(SZ_DHW_STATE)]}

            get_sp[SZ_TIME_OF_DAY] = put_sp[pascal_case(SZ_TIME_OF_DAY)]
            get_switchpoints.append(get_sp)

        get_day_schedule[SZ_SWITCHPOINTS] = get_switchpoints
        get_schedule[SZ_DAILY_SCHEDULES].append(get_day_schedule)

    return get_schedule
