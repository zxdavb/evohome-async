#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC zones (heating and DHW)."""

from __future__ import annotations

from datetime import datetime as dt
import json
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, ZoneMode
from .exceptions import InvalidSchedule, InvalidSchema
from .schema import SCH_ZONE_STATUS
from .schema.schedule import (
    SCH_GET_SCHEDULE,
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE,
    SCH_PUT_SCHEDULE_ZONE,
    convert_to_put_schedule,
)
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_MODE,
    SZ_SETPOINT_STATUS,
    SZ_TEMPERATURE_STATUS,
    SZ_TEMPERATURE_ZONE,
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)

if TYPE_CHECKING:
    import logging

    from . import Broker, ControlSystem
    from .schema import _EvoDictT, _EvoListT, _ZoneIdT


class _ZoneBaseDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def zone_type(self) -> NoReturn:
        raise NotImplementedError("ZoneBase.zone_type is deprecated, use .TYPE")

    async def schedule(self) -> NoReturn:
        raise NotImplementedError(
            "ZoneBase.schedule() is deprecrated, use .get_schedule()"
        )


class _ZoneBase(_ZoneBaseDeprecated):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    STATUS_SCHEMA = dict

    SCH_SCHEDULE_GET = SCH_GET_SCHEDULE
    SCH_SCHEDULE_PUT = SCH_PUT_SCHEDULE

    _id: str  # .zoneId or .dhwId
    TYPE: str  # "temperatureZone", "domesticHotWater"

    def __init__(self, tcs: ControlSystem) -> None:
        self.tcs = tcs

        self._broker: Broker = tcs._broker
        self._logger: logging.Logger = tcs._logger

        self._status: _EvoDictT = {}

    def __str__(self) -> str:
        return f"{self._id} ({self.TYPE})"

    async def _refresh_status(self) -> _EvoDictT:
        """Update the dhw/zone with its latest status (also returns the status).

        It will be more efficient to call Location.refresh_status().
        """

        self._logger.debug(f"Getting status of {self._id} ({self.TYPE})...")

        status: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self._id}/status", schema=self.STATUS_SCHEMA
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: _EvoDictT) -> None:
        self._status = status

    # status attrs...
    @property
    def activeFaults(self) -> None | _EvoListT:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def temperatureStatus(self) -> None | _EvoDictT:
        return self._status.get(SZ_TEMPERATURE_STATUS)

    async def get_schedule(self) -> _EvoDictT:
        """Get the schedule for this dhw/zone object."""

        self._logger.debug(f"Getting schedule of {self._id} ({self.TYPE})...")

        schedule: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self._id}/schedule", schema=self.SCH_SCHEDULE_GET
        )  # type: ignore[assignment]

        return convert_to_put_schedule(schedule)

    async def set_schedule(self, schedule: _EvoDictT | str) -> None:
        """Set the schedule for this dhw/zone object."""

        self._logger.debug(f"Setting schedule of {self._id} ({self.TYPE})...")

        if isinstance(schedule, dict):
            try:
                json.dumps(schedule)
            except (OverflowError, TypeError, ValueError) as exc:
                raise InvalidSchedule(f"Invalid schedule: {exc}")

        elif isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError as exc:
                raise InvalidSchedule(f"Invalid schedule: {exc}")

        else:
            raise InvalidSchedule(f"Invalid schedule type: {type(schedule)}")

        _ = await self._broker.put(
            f"{self.TYPE}/{self._id}/schedule",
            json=schedule,
            schema=self.SCH_SCHEDULE_PUT,
        )


class Zone(_ZoneBase):
    """Instance of a TCS's heating zone (temperatureZone)."""

    STATUS_SCHEMA = SCH_ZONE_STATUS
    TYPE: Final[str] = SZ_TEMPERATURE_ZONE  # type: ignore[misc]

    SCH_SCHEDULE_GET = SCH_GET_SCHEDULE_ZONE
    SCH_SCHEDULE_PUT = SCH_PUT_SCHEDULE_ZONE

    def __init__(self, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(tcs)

        self._config: Final[_EvoDictT] = config

        try:
            assert self.zoneId, "Invalid config dict"
        except AssertionError as exc:
            raise InvalidSchema(str(exc))
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

    async def _set_heat_setpoint(self, heat_setpoint: dict) -> None:
        """TODO"""

        _ = await self._broker.put(
            f"{self.TYPE}/{self._id}/heatSetpoint", json=heat_setpoint  # schema=
        )

    async def set_temperature(
        self, temperature: float, /, *, until: dt | None = None
    ) -> None:
        """Set the temperature of the given zone."""

        mode: dict[str, str | float | None]

        if until is None:  # NOTE: beware that these may be case-sensitive
            mode = {
                SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                SZ_TIME_UNTIL: None,
            }
        else:
            mode = {
                SZ_SETPOINT_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                SZ_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_heat_setpoint(mode)

    async def cancel_temp_override(self) -> None:
        """Cancel an override to the zone temperature."""

        mode: dict[str, str | float | None] = {
            SZ_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
            SZ_HEAT_SETPOINT_VALUE: 0.0,
            SZ_TIME_UNTIL: None,
        }

        await self._set_heat_setpoint(mode)
