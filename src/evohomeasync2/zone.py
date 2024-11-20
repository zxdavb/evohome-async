#!/usr/bin/env python3
"""Provides handling of TCC zones (heating and DHW)."""

# TODO: add provision for cooling zones, when vendor's API adds support for such
# TODO: add set_mode() for non-evohome modes (e.g. "VacationHold")

from __future__ import annotations

import json
from datetime import datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import voluptuous as vol

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_FAULT_TYPE,
    SZ_IS_AVAILABLE,
    SZ_MAX_HEAT_SETPOINT,
    SZ_MIN_HEAT_SETPOINT,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_MODE,
    SZ_SETPOINT_STATUS,
    SZ_SINCE,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_STATUS,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)
from .schema import (
    camel_to_snake,
    convert_to_put_schedule,
    factory_put_schedule_zone,
    factory_schedule_zone,
    factory_zone_status,
)
from .schema.const import (
    S2_HEAT_SETPOINT_VALUE,
    S2_SETPOINT_MODE,
    S2_TIME_UNTIL,
    ZONE_MODEL_TYPES,
    ZONE_TYPES,
    EntityType,
    ZoneMode,
    ZoneModelType,
    ZoneType,
)

if TYPE_CHECKING:
    import logging

    from . import ControlSystem
    from .auth import Auth
    from .schema import _EvoDictT, _EvoListT


_ONE_DAY = td(days=1)


class EntityBase:
    _TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

    _config: _EvoDictT
    _status: _EvoDictT

    def __init__(self, id: str, auth: Auth, logger: logging.Logger) -> None:
        self._id: Final = id

        self._auth = auth
        self._logger = logger

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}')"

    @property
    def id(self) -> str:
        return self._id

    @property
    def config(self) -> _EvoDictT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> _EvoDictT | None:
        """Return the latest status of the entity."""
        return self._status


class ActiveFaultsBase(EntityBase):
    def __init__(self, id: str, broker: Auth, logger: logging.Logger) -> None:
        super().__init__(id, broker, logger)

        self._active_faults: _EvoListT = []
        self._last_logged: dict[str, dt] = {}

    def _update_status(self, status: _EvoDictT) -> None:
        last_logged = {}

        def hash(fault: _EvoDictT) -> str:
            return f"{fault[SZ_FAULT_TYPE]}_{fault[SZ_SINCE]}"

        def log_as_active(fault: _EvoDictT) -> None:
            self._logger.warning(
                f"Active fault: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            last_logged[hash(fault)] = dt.now()

        def log_as_resolved(fault: _EvoDictT) -> None:
            self._logger.info(
                f"Fault cleared: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            del self._last_logged[hash(fault)]

        for fault in status[SZ_ACTIVE_FAULTS]:
            if fault not in self.active_faults:  # new active fault
                log_as_active(fault)

        for fault in self.active_faults:
            if fault not in status[SZ_ACTIVE_FAULTS]:  # fault resolved
                log_as_resolved(fault)

            elif dt.now() - self._last_logged[hash(fault)] > _ONE_DAY:
                log_as_active(fault)

        self._active_faults = status[SZ_ACTIVE_FAULTS]
        self._last_logged |= last_logged

    @property
    def active_faults(self) -> _EvoListT:
        """
        "activeFaults": [
            {
            "faultType": "GatewayCommunicationLost",
            "since": "2023-05-04T18:47:36.7727046"
            }
        ]
        """

        return self._active_faults


class _ZoneBase(ActiveFaultsBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    STATUS_SCHEMA: Final  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final  # type: ignore[misc]

    def __init__(self, id: str, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(id, tcs._auth, tcs._logger)

        self.tcs = tcs  # parent

        self._config: Final[_EvoDictT] = config  # type: ignore[misc]
        self._schedule: _EvoDictT = {}
        self._status: _EvoDictT = {}

    async def _update(self) -> _EvoDictT:
        """Get the latest state of the DHW/zone and update its status.

        It is more efficient to call Location.update() as all zones are updated
        with a single GET.

        Returns the raw JSON of the latest state.
        """

        status: _EvoDictT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status", schema=self.STATUS_SCHEMA
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

    @property
    def temperature_status(self) -> _EvoDictT | None:
        """
        "temperatureStatus": {
            "temperature": 20.0,
            "isAvailable": true
        }
        """

        ret: _EvoDictT | None = self._status.get(SZ_TEMPERATURE_STATUS)
        return ret

    @property  # a convenience attr
    def temperature(self) -> float | None:
        if not (status := self.temperature_status) or not status[SZ_IS_AVAILABLE]:
            return None

        ret: float = status[SZ_TEMPERATURE]
        return ret

    async def get_schedule(self) -> _EvoDictT:
        """Get the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Getting schedule...")

        try:
            schedule: _EvoDictT = await self._auth.get(
                f"{self._TYPE}/{self.id}/schedule", schema=self.SCH_SCHEDULE_GET
            )  # type: ignore[assignment]

        except exc.RequestFailedError as err:
            if err.status == HTTPStatus.BAD_REQUEST:
                raise exc.InvalidScheduleError(
                    f"{self}: No Schedule / Schedule is invalid"
                ) from err
            raise exc.RequestFailedError(f"{self}: Unexpected error") from err

        except vol.Invalid as err:
            raise exc.InvalidScheduleError(
                f"{self}: No Schedule / Schedule is invalid"
            ) from err

        self._schedule = convert_to_put_schedule(schedule)
        return self._schedule

    async def set_schedule(self, schedule: _EvoDictT | str) -> None:
        """Set the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Setting schedule...")

        if isinstance(schedule, dict):
            try:
                json.dumps(schedule)
            except (OverflowError, TypeError, ValueError) as err:
                raise exc.InvalidScheduleError(
                    f"{self}: Invalid schedule: {err}"
                ) from err

        elif isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError as err:
                raise exc.InvalidScheduleError(
                    f"{self}: Invalid schedule: {err}"
                ) from err

        else:
            raise exc.InvalidScheduleError(
                f"{self}: Invalid schedule type: {type(schedule)}"
            )

        assert isinstance(schedule, dict)  # mypy check

        await self._auth.put(
            f"{self._TYPE}/{self.id}/schedule",
            json=schedule,
            schema=self.SCH_SCHEDULE_PUT,
        )

        self._schedule = schedule


# Currently, cooling (e.g. target_heat_temperature) is not supported by the API
class Zone(_ZoneBase):
    """Instance of a TCS's heating zone (temperatureZone)."""

    STATUS_SCHEMA: Final = factory_zone_status(camel_to_snake)  # type: ignore[misc]
    _TYPE: Final = EntityType.ZON  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final = factory_schedule_zone(camel_to_snake)  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final = factory_put_schedule_zone(camel_to_snake)  # type: ignore[misc]

    def __init__(self, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(config[SZ_ZONE_ID], tcs, config)

        if not self.model or self.model == ZoneModelType.UNKNOWN:
            raise exc.InvalidSchemaError(
                f"{self}: Invalid model type '{self.model}' (is it a ghost zone?)"
            )
        if not self.type or self.type == ZoneType.UNKNOWN:
            raise exc.InvalidSchemaError(
                f"{self}: Invalid zone type '{self.type}' (is it a ghost zone?)"
            )

        if self.model not in ZONE_MODEL_TYPES:
            self._logger.warning("%s: Unknown model type '%s' (YMMV)", self, self.model)
        if self.type not in ZONE_TYPES:
            self._logger.warning("%s: Unknown zone type '%s' (YMMV)", self, self.type)

    @property  # convenience attr
    def max_heat_setpoint(self) -> float:
        ret: float = self.setpoint_capabilities[SZ_MAX_HEAT_SETPOINT]
        return ret

    @property  # convenience attr
    def min_heat_setpoint(self) -> float:
        ret: float = self.setpoint_capabilities[SZ_MIN_HEAT_SETPOINT]
        return ret

    @property
    def model(self) -> ZoneModelType:
        ret: ZoneModelType = self._config[SZ_MODEL_TYPE]
        return ret

    @property  # a convenience attr
    def mode(self) -> ZoneMode | None:
        if not self.setpoint_status:
            return None
        ret: ZoneMode = self.setpoint_status[SZ_SETPOINT_MODE]
        return ret

    @property  # a convenience attr
    def modes(self) -> tuple[ZoneMode]:
        """
        "allowedSetpointModes": [
            "PermanentOverride", "FollowSchedule", "TemporaryOverride"
        ]
        """

        ret = tuple(self.setpoint_capabilities[SZ_ALLOWED_SETPOINT_MODES])
        return ret

    @property
    def name(self) -> str:
        ret: str = self._status.get(SZ_NAME) or self._config[SZ_NAME]
        return ret

    @property
    def schedule_capabilities(self) -> _EvoDictT:
        """
        "scheduleCapabilities": {
            "maxSwitchpointsPerDay": 6,
            "minSwitchpointsPerDay": 1,
            "timingResolution": "00:10:00",
            "setpointValueResolution": 0.5
        }
        """

        ret: _EvoDictT = self._config[SZ_SCHEDULE_CAPABILITIES]
        return ret

    @property
    def setpoint_capabilities(self) -> _EvoDictT:
        """
        "setpointCapabilities": {
            "maxHeatSetpoint": 35.0,
            "minHeatSetpoint": 5.0,
            "valueResolution": 0.5,
            "canControlHeat": true,
            "canControlCool": false,
            "allowedSetpointModes": ["PermanentOverride", "FollowSchedule", "TemporaryOverride"],
            "maxDuration": "1.00:00:00",
            "timingResolution": "00:10:00"
        }
        """

        ret: _EvoDictT = self._config[SZ_SETPOINT_CAPABILITIES]
        return ret

    @property
    def setpoint_status(self) -> _EvoDictT | None:
        """
        "setpointStatus": {
            "targetHeatTemperature": 17.0,
            "setpointMode": "FollowSchedule"
        }
        """
        ret: _EvoDictT | None = self._status.get(SZ_SETPOINT_STATUS)
        return ret

    @property  # a convenience attr
    def target_heat_temperature(self) -> float | None:
        if self.setpoint_status is None:
            return None
        ret: float = self.setpoint_status[SZ_TARGET_HEAT_TEMPERATURE]
        return ret

    @property
    def type(self) -> ZoneType:
        ret: ZoneType = self._config[SZ_ZONE_TYPE]
        return ret

    async def _set_mode(self, mode: dict[str, str | float]) -> None:
        """Set the zone mode (heat_setpoint, cooling is TBD)."""

        if mode[S2_SETPOINT_MODE] not in self.modes:
            raise exc.InvalidParameterError(
                f"{self}: Unsupported/unknown {S2_SETPOINT_MODE}: {mode}"
            )

        temp: float | None = mode.get(S2_HEAT_SETPOINT_VALUE)  # type: ignore[assignment]
        if temp is not None and self.min_heat_setpoint > temp > self.max_heat_setpoint:
            raise exc.InvalidParameterError(
                f"{self}: Unsupported/invalid {S2_HEAT_SETPOINT_VALUE}: {mode}"
            )

        await self._auth.put(f"{self._TYPE}/{self.id}/heatSetpoint", json=mode)

    async def reset(self) -> None:
        """Cancel any override and allow the zone to follow its schedule"""

        mode: dict[str, str | float] = {
            S2_SETPOINT_MODE: ZoneMode.FOLLOW_SCHEDULE,
            # S2_HEAT_SETPOINT_VALUE: 0.0,
            # S2_TIME_UNTIL: None,
        }

        await self._set_mode(mode)

    # NOTE: no provision for cooling (not supported by API)
    async def set_temperature(  # aka. set_mode()
        self, temperature: float, /, *, until: dt | None = None
    ) -> None:
        """Set the temperature of the given zone (no provision for cooling)."""

        mode: dict[str, str | float]

        if until is None:  # NOTE: beware that these may be case-sensitive
            mode = {
                S2_SETPOINT_MODE: ZoneMode.PERMANENT_OVERRIDE,
                S2_HEAT_SETPOINT_VALUE: temperature,
                # S2_TIME_UNTIL: None,
            }
        else:
            mode = {
                S2_SETPOINT_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                S2_HEAT_SETPOINT_VALUE: temperature,
                S2_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)
