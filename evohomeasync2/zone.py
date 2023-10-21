#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of heatings zones."""

from __future__ import annotations

from datetime import datetime as dt
import json
import logging
from typing import TYPE_CHECKING, Final, NoReturn

from aiohttp.client_exceptions import ClientResponseError

from .const import API_STRFTIME, URL_BASE
from .exceptions import InvalidSchedule
from .schema import SCH_DHW_STATUS, SCH_ZONE_STATUS, SCH_SCHEDULE
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_DAILY_SCHEDULES,
    SZ_DAY_OF_WEEK,
    SZ_DHW_STATE,
    SZ_FOLLOW_SCHEDULE,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_PERMANENT_OVERRIDE,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_MODE,
    SZ_SETPOINT_STATUS,
    SZ_SWITCHPOINTS,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_STATUS,
    SZ_TEMPERATURE_ZONE,
    SZ_TEMPORARY_OVERRIDE,
    SZ_TIME_OF_DAY,
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)

if TYPE_CHECKING:
    from .controlsystem import ControlSystem
    from .typing import _ZoneIdT

_LOGGER = logging.getLogger(__name__)


CAPITALIZED_KEYS = (
    SZ_DAILY_SCHEDULES,  #
    SZ_DAY_OF_WEEK,  #
    SZ_DHW_STATE,
    SZ_SWITCHPOINTS,  #
    SZ_TEMPERATURE,  # should be SZ_HEAT_SETPOINT?
    SZ_TIME_OF_DAY,  #
)


class _ZoneBaseDeprecated:
    @property
    def zone_type(self) -> NoReturn:
        raise NotImplementedError("ZoneBase.zone_type is deprecated, use ._type")

    async def schedule(self) -> NoReturn:
        raise NotImplementedError(
            "ZoneBase.schedule() is deprecrated, use .get_schedule()"
        )


class _ZoneBase(_ZoneBaseDeprecated):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    _id: str  # .zoneId or .dhwId
    _type: str  # Literal["temperatureZone", "domesticHotWater"]

    def __init__(self, tcs: ControlSystem) -> None:
        self.tcs = tcs

        self._client = tcs.gateway.location._client

        self._status: dict = {}

    async def _refresh_status(self) -> dict:
        """Update the dhw/zone with its latest status (also returns the status).

        It will be more efficient to call Location.refresh_status().
        """

        url = f"{self._type}/{self._id}/status"
        response = await self._client("GET", f"{URL_BASE}/{url}")

        if self._type == SZ_TEMPERATURE_ZONE:
            status = SCH_ZONE_STATUS(response)
        else:
            status = SCH_DHW_STATUS(response)

        self._update_status(status)
        return status

    def _update_status(self, status: dict) -> None:
        self._status = status

    # status attrs...
    @property
    def activeFaults(self) -> None | list:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def temperatureStatus(self) -> None | dict:
        return self._status.get(SZ_TEMPERATURE_STATUS)

    async def get_schedule(self) -> dict:
        """Get the schedule for this dhw/zone object."""

        _LOGGER.debug(f"Getting schedule of {self._id} ({self._type})...")

        url = f"{self._type}/{self._id}/schedule"
        response_json = await self._client("GET", f"{URL_BASE}/{url}")

        assert SCH_SCHEDULE(response_json)

        response_text = json.dumps(response_json)  # FIXME
        for key_name in CAPITALIZED_KEYS:  # an anachronism from evohome-client
            response_text = response_text.replace(key_name, key_name.capitalize())

        result: dict = json.loads(response_text)
        # change the day name string to an ordinal (Monday = 0)
        for day_of_week, schedule in enumerate(result[SZ_DAILY_SCHEDULES.capitalize()]):
            schedule[SZ_DAY_OF_WEEK.capitalize()] = day_of_week

        return result

    async def set_schedule(self, zone_schedule: dict | str) -> None:
        """Set the schedule for this dhw/zone object."""

        _LOGGER.debug(f"Setting schedule of {self._id} ({self._type})...")

        if isinstance(zone_schedule, dict):
            json_schedule: str = json.dumps(zone_schedule)
        else:
            try:
                json.loads(zone_schedule)
            except ValueError as exc:
                raise InvalidSchedule(f"Invalid JSON: {zone_schedule}") from exc

            json_schedule = zone_schedule

        url = f"{self._type}/{self._id}/schedule"
        try:
            await self._client("PUT", f"{URL_BASE}/{url}", data=json_schedule)
        except ClientResponseError as exc:
            if exc.status == 400:  # Bad Request
                raise InvalidSchedule(f"Invalid schedule: {zone_schedule}")  # 400
            if exc.status == 401:  # Unauthorized
                raise InvalidSchedule(f"Unknown Zone/DHW Id: {self._id}")  # 401
            if exc.status == 404:  # Not Found
                raise InvalidSchedule(f"Unknown Zone/DHW Type: {self._type}")  # 404
            raise


class Zone(_ZoneBase):
    """Provide the access to an individual zone."""

    _type = SZ_TEMPERATURE_ZONE

    def __init__(self, tcs: ControlSystem, zone_config: dict) -> None:
        super().__init__(tcs)

        self._config: Final[dict] = zone_config
        assert self.zoneId, "Invalid config dict"

        self._id = self.zoneId

    # config attrs...
    @property
    def zoneId(self) -> _ZoneIdT:
        return self._config[SZ_ZONE_ID]

    @property
    def modelType(self) -> str:
        return self._config[SZ_MODEL_TYPE]

    @property
    def setpointCapabilities(self) -> dict:
        return self._config[SZ_SETPOINT_CAPABILITIES]

    @property
    def scheduleCapabilities(self) -> dict:
        return self._config[SZ_SCHEDULE_CAPABILITIES]

    @property
    def zoneType(self) -> str:
        return self._config[SZ_ZONE_TYPE]

    # status attrs...
    @property
    def name(self) -> str:
        return self._config.get(SZ_NAME) or self._config[SZ_NAME]

    @property
    def setpointStatus(self) -> None | dict:
        return self._status.get(SZ_SETPOINT_STATUS)

    async def _set_mode(self, heat_setpoint: dict) -> None:
        """TODO"""

        url = f"temperatureZone/{self.zoneId}/heatSetpoint"  # f"{_type}/{_id}/heatS..."
        await self._client("PUT", f"{URL_BASE}/{url}", json=heat_setpoint)

    async def set_temperature(
        self, temperature: float, /, *, until: None | dt = None
    ) -> None:
        """Set the temperature of the given zone."""

        if until is None:  # NOTE: beware that these may be case-sensitive
            mode = {
                SZ_SETPOINT_MODE: SZ_PERMANENT_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                SZ_TIME_UNTIL: None,
            }
        else:
            mode = {
                SZ_SETPOINT_MODE: SZ_TEMPORARY_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                SZ_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def cancel_temp_override(self) -> None:
        """Cancel an override to the zone temperature."""

        mode = {
            SZ_SETPOINT_MODE: SZ_FOLLOW_SCHEDULE,
            SZ_HEAT_SETPOINT_VALUE: 0.0,
            SZ_TIME_UNTIL: None,
        }

        await self._set_mode(mode)
