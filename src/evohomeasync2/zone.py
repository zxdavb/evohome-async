#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC zones (heating and DHW)."""

# TODO: add provision for cooling zones
# TODO: add set_mode() for non-evohome modes (e.g. "VacationHold")

from __future__ import annotations

import json
from datetime import datetime as dt
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, ZoneMode
from .exceptions import DeprecationError, InvalidSchedule, InvalidSchema
from .schema import SCH_ZONE_STATUS
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_HEAT_SETPOINT_VALUE,
    SZ_IS_AVAILABLE,
    SZ_MAX_HEAT_SETPOINT,
    SZ_MIN_HEAT_SETPOINT,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_MODE,
    SZ_SETPOINT_STATUS,
    SZ_TARGET_COOL_TEMPERATURE,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_STATUS,
    SZ_TEMPERATURE_ZONE,
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)
from .schema.schedule import (
    SCH_GET_SCHEDULE,
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE,
    SCH_PUT_SCHEDULE_ZONE,
    convert_to_put_schedule,
)

if TYPE_CHECKING:
    import logging

    from . import Broker, ControlSystem
    from .schema import _EvoDictT, _EvoListT, _ZoneIdT


class _ZoneBaseDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def zone_type(self) -> NoReturn:
        raise DeprecationError("ZoneBase.zone_type is deprecated, use .TYPE")

    async def schedule(self) -> NoReturn:
        raise DeprecationError(
            "_ZoneBase.schedule() is deprecrated, use .get_schedule()"
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
        self._schedule: _EvoDictT = {}

    def __str__(self) -> str:
        return f"{self._id} ({self.TYPE})"

    async def _refresh_status(self) -> _EvoDictT:
        """Update the DHW/zone with its latest status (also returns the status).

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

    @property
    def activeFaults(self) -> _EvoListT | None:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def temperatureStatus(self) -> _EvoDictT | None:
        return self._status.get(SZ_TEMPERATURE_STATUS)

    @property  # status attr for convenience (new)
    def temperature(self) -> float | None:
        if not self.temperatureStatus or not self.temperatureStatus[SZ_IS_AVAILABLE]:
            return None

        assert isinstance(self.temperatureStatus[SZ_TEMPERATURE], float)  # mypy check
        temperature: float = self.temperatureStatus[SZ_TEMPERATURE]
        return temperature

    async def get_schedule(self) -> _EvoDictT:
        """Get the schedule for this DHW/zone object."""

        self._logger.debug(f"Getting schedule of {self._id} ({self.TYPE})...")

        schedule: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self._id}/schedule", schema=self.SCH_SCHEDULE_GET
        )  # type: ignore[assignment]

        self._schedule = convert_to_put_schedule(schedule)
        return self._schedule

    async def set_schedule(self, schedule: _EvoDictT | str) -> None:
        """Set the schedule for this DHW/zone object."""

        self._logger.debug(f"Setting schedule of {self._id} ({self.TYPE})...")

        if isinstance(schedule, dict):
            try:
                json.dumps(schedule)
            except (OverflowError, TypeError, ValueError) as exc:
                raise InvalidSchedule(f"Invalid schedule: {exc}") from exc

        elif isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError as exc:
                raise InvalidSchedule(f"Invalid schedule: {exc}") from exc

        else:
            raise InvalidSchedule(f"Invalid schedule type: {type(schedule)}")

        assert isinstance(schedule, dict)  # mypy check

        _ = await self._broker.put(
            f"{self.TYPE}/{self._id}/schedule",
            json=schedule,
            schema=self.SCH_SCHEDULE_PUT,
        )

        self._schedule = schedule


class _ZoneDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def cancel_temp_override(self) -> None:
        raise DeprecationError(
            "Zone.cancel_temp_override() is deprecrated, use .reset_mode()"
        )


class Zone(_ZoneDeprecated, _ZoneBase):
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
            raise InvalidSchema(str(exc)) from exc
        self._id = self.zoneId

    @property
    def zoneId(self) -> _ZoneIdT:
        ret: _ZoneIdT = self._config[SZ_ZONE_ID]
        return ret

    @property
    def modelType(self) -> str:
        ret: str = self._config[SZ_MODEL_TYPE]
        return ret

    @property
    def setpointCapabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_SETPOINT_CAPABILITIES]
        return ret

    @property  # for convenience (is not a top-level config attribute)
    def allowedSetpointModes(self) -> _EvoListT:
        ret: _EvoListT = self.setpointCapabilities[SZ_ALLOWED_SETPOINT_MODES]
        return ret

    @property
    def scheduleCapabilities(self) -> _EvoDictT:
        result: _EvoDictT = self._config[SZ_SCHEDULE_CAPABILITIES]
        return result

    @property  # config attr for convenience (new)
    def max_heat_setpoint(self) -> float:
        ret: float = self.setpointCapabilities[SZ_MAX_HEAT_SETPOINT]
        return ret

    @property  # config attr for convenience (new)
    def min_heat_setpoint(self) -> float:
        ret: float = self.setpointCapabilities[SZ_MIN_HEAT_SETPOINT]
        return ret

    @property
    def zoneType(self) -> str:
        ret: str = self._config[SZ_ZONE_TYPE]
        return ret

    @property
    def name(self) -> str:
        ret: str = self._status.get(SZ_NAME) or self._config[SZ_NAME]
        return ret

    @property
    def setpointStatus(self) -> _EvoDictT | None:
        return self._status.get(SZ_SETPOINT_STATUS)

    @property  # status attr for convenience (new)
    def mode(self) -> str | None:
        return self.setpointStatus[SZ_SETPOINT_MODE] if self.setpointStatus else None

    @property  # status attr for convenience (new)
    def target_cool_temperature(self) -> float | None:
        if not self.setpointStatus:
            return None
        return self.setpointStatus.get(SZ_TARGET_COOL_TEMPERATURE)

    @property  # status attr for convenience (new)
    def target_heat_temperature(self) -> float | None:
        if not self.setpointStatus:
            return None
        ret: float = self.setpointStatus[SZ_TARGET_HEAT_TEMPERATURE]
        return ret

    # TODO: no provision for cooling
    async def _set_mode(self, mode: dict[str, str | float]) -> None:
        """Set the zone mode (heat_setpoint, cooling is TBD)."""
        _ = await self._broker.put(f"{self.TYPE}/{self._id}/heatSetpoint", json=mode)

    async def reset_mode(self) -> None:
        """Cancel any override and allow the zone to follow its schedule"""

        mode: dict[str, str | float] = {
            SZ_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
            # SZ_HEAT_SETPOINT_VALUE: 0.0,
            # SZ_TIME_UNTIL: None,
        }

        await self._set_mode(mode)

    async def set_temperature(  # NOTE: no provision for cooling
        self, temperature: float, /, *, until: dt | None = None
    ) -> None:
        """Set the temperature of the given zone (no provision for cooling)."""

        mode: dict[str, str | float]

        if until is None:  # NOTE: beware that these may be case-sensitive
            mode = {
                SZ_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                # SZ_TIME_UNTIL: None,
            }
        else:
            mode = {
                SZ_SETPOINT_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                SZ_HEAT_SETPOINT_VALUE: temperature,
                SZ_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)
