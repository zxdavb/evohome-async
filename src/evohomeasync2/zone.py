#!/usr/bin/env python3
"""Provides handling of TCC zones (heating and DHW)."""

# TODO: add provision for cooling zones, when vendor's API adds support for such
# TODO: add set_mode() for non-evohome modes (e.g. "VacationHold")

from __future__ import annotations

import json
from datetime import datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, NoReturn

import voluptuous as vol

from . import exceptions as exc
from .const import API_STRFTIME, ZoneMode
from .schema import (
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE_ZONE,
    SCH_ZONE_STATUS,
    convert_keys_to_snake_case,
    convert_to_put_schedule,
)
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_FAULT_TYPE,
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
    SZ_SINCE,
    SZ_TARGET_COOL_TEMPERATURE,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_STATUS,
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
    ZONE_MODEL_TYPES,
    ZONE_TYPES,
    EntityType,
    ZoneModelType,
    ZoneType,
)

if TYPE_CHECKING:
    import logging

    from . import Auth, ControlSystem
    from .schema import _EvoDictT, _EvoListT


_ONE_DAY = td(days=1)


class EntityBase:
    TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

    def __init__(self, id: str, broker: Auth, logger: logging.Logger) -> None:
        self._id: Final = id

        self._broker = broker
        self._logger = logger

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}')"

    @property
    def id(self) -> str:
        return self._id


class ActiveFaultsBase(EntityBase):
    def __init__(self, id: str, broker: Auth, logger: logging.Logger) -> None:
        super().__init__(id, broker, logger)

        self._active_faults: _EvoListT = []
        self._last_logged: dict[str, dt] = {}

    @property
    def active_faults(self) -> _EvoListT:
        return self._active_faults

    @active_faults.setter
    def active_faults(self, value: _EvoListT) -> None:
        self._active_faults = value

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

        self.active_faults = status[SZ_ACTIVE_FAULTS]
        self._last_logged |= last_logged


class _ZoneBaseDeprecated:  # pragma: no cover
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def zoneId(self) -> NoReturn:
        raise exc.DeprecationError(f"{self}: .zoneId is deprecated, use .id")

    @property
    def activeFaults(self) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .activeFaults is deprecated, use .active_faults"
        )

    async def schedule(self) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .schedule() is deprecrated, use .get_schedule()"
        )


class _ZoneBase(ActiveFaultsBase, _ZoneBaseDeprecated):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    STATUS_SCHEMA: Final[vol.Schema]  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final[vol.Schema]  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final[vol.Schema]  # type: ignore[misc]

    def __init__(self, id: str, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(id, tcs._broker, tcs._logger)

        self.tcs = tcs  # parent

        self._config: Final[_EvoDictT] = config
        self._schedule: _EvoDictT = {}
        self._status: _EvoDictT = {}

    async def _refresh_status(self) -> _EvoDictT:
        """Update the DHW/zone with its latest status (also returns the status).

        It is more efficient to call Location.refresh_status() as all zones are updated
        with a single GET.
        """

        status: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self.id}/status", schema=self.STATUS_SCHEMA
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

    @property
    def temperature_status(self) -> _EvoDictT | None:
        return convert_keys_to_snake_case(self._status.get(SZ_TEMPERATURE_STATUS))

    @property  # status attr for convenience (new)
    def temperature(self) -> float | None:
        if (
            not (status := self._status.get(SZ_TEMPERATURE_STATUS))
            or not status[SZ_IS_AVAILABLE]
        ):
            return None

        # assert isinstance(status[SZ_TEMPERATURE], float)  # mypy check
        ret: float = status[SZ_TEMPERATURE]
        return ret

    async def get_schedule(self) -> _EvoDictT:
        """Get the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Getting schedule...")

        try:
            schedule: _EvoDictT = await self._broker.get(
                f"{self.TYPE}/{self.id}/schedule", schema=self.SCH_SCHEDULE_GET
            )  # type: ignore[assignment]

        except exc.RequestFailed as err:
            if err.status == HTTPStatus.BAD_REQUEST:
                raise exc.InvalidSchedule(
                    f"{self}: No Schedule / Schedule is invalid"
                ) from err
            raise exc.RequestFailed(f"{self}: Unexpected error") from err

        except vol.Invalid as err:
            raise exc.InvalidSchedule(
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
                raise exc.InvalidSchedule(f"{self}: Invalid schedule: {err}") from err

        elif isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError as err:
                raise exc.InvalidSchedule(f"{self}: Invalid schedule: {err}") from err

        else:
            raise exc.InvalidSchedule(
                f"{self}: Invalid schedule type: {type(schedule)}"
            )

        assert isinstance(schedule, dict)  # mypy check

        _ = await self._broker.put(
            f"{self.TYPE}/{self.id}/schedule",
            json=schedule,
            schema=self.SCH_SCHEDULE_PUT,
        )

        self._schedule = schedule


class _ZoneDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def cancel_temp_override(self) -> None:
        raise exc.DeprecationError(
            f"{self}: .cancel_temp_override() is deprecrated, use .reset_mode()"
        )


class Zone(_ZoneDeprecated, _ZoneBase):
    """Instance of a TCS's heating zone (temperatureZone)."""

    STATUS_SCHEMA: Final = SCH_ZONE_STATUS  # type: ignore[misc]
    TYPE: Final = EntityType.ZON  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final = SCH_GET_SCHEDULE_ZONE  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final = SCH_PUT_SCHEDULE_ZONE  # type: ignore[misc]

    def __init__(self, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(config[SZ_ZONE_ID], tcs, config)

        if not self.model_type or self.model_type == ZoneModelType.UNKNOWN:
            raise exc.InvalidSchema(
                f"{self}: Invalid model type '{self.model_type}' (is it a ghost zone?)"
            )
        if not self.zone_type or self.zone_type == ZoneType.UNKNOWN:
            raise exc.InvalidSchema(
                f"{self}: Invalid zone type '{self.zone_type}' (is it a ghost zone?)"
            )

        if self.model_type not in ZONE_MODEL_TYPES:
            self._logger.warning(
                "%s: Unknown model type '%s' (YMMV)", self, self.model_type
            )
        if self.zone_type not in ZONE_TYPES:
            self._logger.warning(
                "%s: Unknown zone type '%s' (YMMV)", self, self.zone_type
            )

    @property
    def model_type(self) -> str:
        ret: str = self._config[SZ_MODEL_TYPE]
        return ret

    @property
    def setpoint_capabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_SETPOINT_CAPABILITIES]
        return convert_keys_to_snake_case(ret)

    @property  # for convenience (is not a top-level config attribute)
    def allowed_setpoint_modes(self) -> _EvoListT:
        ret: _EvoListT = self._config[SZ_SETPOINT_CAPABILITIES][
            SZ_ALLOWED_SETPOINT_MODES
        ]
        return convert_keys_to_snake_case(ret)

    @property
    def schedule_capabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_SCHEDULE_CAPABILITIES]
        return convert_keys_to_snake_case(ret)

    @property  # config attr for convenience (new)
    def max_heat_setpoint(self) -> float:
        ret: float = self._config[SZ_SETPOINT_CAPABILITIES][SZ_MAX_HEAT_SETPOINT]
        return ret

    @property  # config attr for convenience (new)
    def min_heat_setpoint(self) -> float:
        ret: float = self._config[SZ_SETPOINT_CAPABILITIES][SZ_MIN_HEAT_SETPOINT]
        return ret

    @property
    def zone_type(self) -> str:
        ret: str = self._config[SZ_ZONE_TYPE]
        return ret

    @property
    def name(self) -> str:
        ret: str = self._status.get(SZ_NAME) or self._config[SZ_NAME]
        return ret

    @property
    def setpoint_status(self) -> _EvoDictT | None:
        return self._status.get(SZ_SETPOINT_STATUS)

    @property  # status attr for convenience (new)
    def mode(self) -> str | None:
        if not self.setpoint_status:
            return None
        ret: str = self.setpoint_status[SZ_SETPOINT_MODE]
        return ret

    @property  # status attr for convenience (new)
    def target_cool_temperature(self) -> float | None:
        if not self.setpoint_status:
            return None
        ret: float | None = self.setpoint_status.get(SZ_TARGET_COOL_TEMPERATURE)
        return ret

    @property  # status attr for convenience (new)
    def target_heat_temperature(self) -> float | None:
        if not self.setpoint_status:
            return None
        ret: float = self.setpoint_status[SZ_TARGET_HEAT_TEMPERATURE]
        return ret

    # TODO: no provision for cooling
    async def _set_mode(self, mode: dict[str, str | float]) -> None:
        """Set the zone mode (heat_setpoint, cooling is TBD)."""
        # TODO: also coolSetpoint
        _ = await self._broker.put(f"{self.TYPE}/{self.id}/heatSetpoint", json=mode)

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
