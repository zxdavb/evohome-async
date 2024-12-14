#!/usr/bin/env python3
"""Provides handling of TCC zones (heating and DHW)."""

# TODO: add provision for cooling zones, when vendor's API adds support for such
# TODO: add set_mode() for non-evohome modes (e.g. "VacationHold")

from __future__ import annotations

import json
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_DAILY_SCHEDULES,
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
from .schemas import factory_schedule_zone, factory_zone_status
from .schemas.const import (
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
from .schemas.schedule import DayOfWeek

if TYPE_CHECKING:
    import logging
    from datetime import tzinfo

    import voluptuous as vol

    from . import ControlSystem
    from .auth import Auth
    from .schemas import _EvoDictT, _EvoListT
    from .schemas.typedefs import (
        DailySchedulesT,
        DayOfWeekT,
        DayOfWeekZoneT,
        EvoDhwConfigT,
        EvoGwyConfigT,
        EvoLocConfigT,
        EvoTcsConfigT,
        EvoTcsStatusT,
        EvoZonConfigT,
        SwitchpointT,
    )

    ScheduleT = list[DayOfWeekT]

    _EvoConfigDictT = (
        EvoLocConfigT | EvoGwyConfigT | EvoTcsConfigT | EvoZonConfigT | EvoDhwConfigT
    )
    _EvoStatusDictT = EvoTcsStatusT


_ONE_DAY = td(days=1)


class EntityBase:
    _TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

    _config: _EvoConfigDictT
    _status: _EvoStatusDictT

    def __init__(self, entity_id: str, auth: Auth, logger: logging.Logger) -> None:
        self._id: Final = entity_id

        self._auth = auth
        self._logger = logger

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self._id}')"

    @property
    def id(self) -> str:
        return self._id

    @property
    def config(self) -> _EvoConfigDictT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> _EvoStatusDictT | None:
        """Return the latest status of the entity."""
        return self._status


class ActiveFaultsBase(EntityBase):
    def __init__(self, entity_id: str, broker: Auth, logger: logging.Logger) -> None:
        super().__init__(entity_id, broker, logger)

        self._active_faults: _EvoListT = []
        self._last_logged: dict[str, dt] = {}

    def _update_status(self, status: _EvoDictT) -> None:
        last_logged = {}

        def hash_(fault: _EvoDictT) -> str:
            return f"{fault[SZ_FAULT_TYPE]}_{fault[SZ_SINCE]}"

        def log_as_active(fault: _EvoDictT) -> None:
            self._logger.warning(
                f"Active fault: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            last_logged[hash_(fault)] = dt.now(tz=UTC)  # aware dtm not required

        def log_as_resolved(fault: _EvoDictT) -> None:
            self._logger.info(
                f"Fault cleared: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            del self._last_logged[hash_(fault)]

        for fault in status[SZ_ACTIVE_FAULTS]:
            if fault not in self.active_faults:  # new active fault
                log_as_active(fault)

        for fault in self.active_faults:
            if fault not in status[SZ_ACTIVE_FAULTS]:  # fault resolved
                log_as_resolved(fault)

            elif dt.now(tz=UTC) - self._last_logged[hash_(fault)] > _ONE_DAY:
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


def as_local_time(dtm: dt, tzinfo: tzinfo) -> dt:
    """Convert a datetime into a aware datetime in the given TZ."""
    return dtm.replace(tzinfo=tzinfo) if dtm.tzinfo is None else dtm.astimezone(tzinfo)


def dt_to_dow_and_tod(dtm: dt, tzinfo: tzinfo) -> tuple[DayOfWeek, str]:
    """Return a pair of strings representing the local day of week and time of day."""
    dtm = as_local_time(dtm, tzinfo)
    return dtm.strftime("%A"), dtm.strftime("%H:%M")  # type: ignore[return-value]


def _find_switchpoints(
    schedule: ScheduleT,
    day_of_week: DayOfWeek,
    time_of_day: str,
) -> tuple[SwitchpointT, int, SwitchpointT, int]:
    """Find this/next switchpoints for a given day of week and time of day."""

    # assumes >1 switchpoint per day, which could be this_sp or next_sp only

    try:
        day_idx = list(DayOfWeek).index(day_of_week)
    except ValueError as err:
        raise TypeError(f"Invalid parameter: {day_of_week}") from err

    this_sp: SwitchpointT | None = None
    next_sp: SwitchpointT | None = None

    this_offset = 0
    next_offset = 0

    # Check the switchpoints of the given day of week
    for sp in schedule[day_idx]["switchpoints"]:
        if sp["time_of_day"] <= time_of_day:
            this_sp = sp
            continue

        if sp["time_of_day"] > time_of_day:
            if this_sp is None:
                this_sp = schedule[(day_idx + 6) % 7]["switchpoints"][-1]
                this_offset = -1

            next_sp = sp
            break

    else:
        if next_sp is None:
            next_sp = schedule[(day_idx + 1) % 7]["switchpoints"][0]
            next_offset = +1

        assert this_sp is not None  # mypy

    return this_sp, this_offset, next_sp, next_offset


class _ScheduleBase(ActiveFaultsBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    SCH_SCHEDULE: vol.Schema

    _schedule: ScheduleT | None

    def __init__(self, entity_id: str, tcs: ControlSystem) -> None:
        super().__init__(entity_id, tcs._auth, tcs._logger)

        self.location = tcs.location

    async def get_schedule(self) -> ScheduleT:
        """Get the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Getting schedule...")

        try:
            schedule: DailySchedulesT = await self._auth.get(
                f"{self._TYPE}/{self.id}/schedule", schema=self.SCH_SCHEDULE
            )  # type: ignore[assignment]

        except exc.ApiRequestFailedError as err:
            if err.status == HTTPStatus.BAD_REQUEST:  # 400
                raise exc.InvalidScheduleError(
                    f"{self}: No Schedule / Schedule is invalid"
                ) from err
            raise exc.ApiRequestFailedError(f"{self}: Unexpected error") from err

        self._schedule = schedule[SZ_DAILY_SCHEDULES]
        return self._schedule

    async def set_schedule(
        self,
        schedule: ScheduleT | str,
    ) -> None:
        """Set the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Setting schedule...")

        if isinstance(schedule, list):
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

        assert isinstance(schedule, list)  # mypy check

        _ = await self._auth.put(
            f"{self._TYPE}/{self.id}/schedule",
            json={"daily_schedules": schedule},
            schema=self.SCH_SCHEDULE,
        )

        # TODO: check the status of the task

        self._schedule = schedule

    def _find_switchpoints(self, dtm: dt | str) -> dict[dt, float | str]:
        """Find the current and next switchpoints for a given day and time of day."""

        if not self._schedule:
            raise exc.InvalidScheduleError("No schedule available")

        if isinstance(dtm, str):
            dtm = dt.fromisoformat(dtm)

        dtm = as_local_time(dtm, self.location.tzinfo)

        this_sp, this_offset, next_sp, next_offset = _find_switchpoints(
            self._schedule, *dt_to_dow_and_tod(dtm, self.location.tzinfo)
        )

        this_tod = dt.strptime(this_sp["time_of_day"], "%H:%M").time()  # noqa: DTZ007
        next_tod = dt.strptime(next_sp["time_of_day"], "%H:%M").time()  # noqa: DTZ007

        this_dtm = dt.combine(dtm + td(days=this_offset), this_tod)
        next_dtm = dt.combine(dtm + td(days=next_offset), next_tod)

        this_val = this_sp.get("dhw_state") or this_sp["heat_setpoint"]
        next_val = next_sp.get("dhw_state") or next_sp["heat_setpoint"]

        # NOTE: this is a convenience return...
        # this_dtm, this_val = next(iter(result.items()))
        # next_dtm, next_val = next(islice(result.items(), 1, 2))

        return {
            this_dtm: this_val,
            next_dtm: next_val,
        }


class _ZoneBase(_ScheduleBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    SCH_STATUS: vol.Schema

    def __init__(self, entity_id: str, tcs: ControlSystem) -> None:
        super().__init__(entity_id, tcs)

        self.location = tcs.location

    async def _update(self) -> _EvoDictT:
        """Get the latest state of the DHW/zone and update its status.

        It is more efficient to call Location.update() as all zones are updated
        with a single GET.

        Returns the raw JSON of the latest state.
        """

        status: _EvoDictT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status", schema=self.SCH_STATUS
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


# Currently, cooling (e.g. target_heat_temperature) is not supported by the API
class Zone(_ZoneBase):
    """Instance of a TCS's heating zone (temperatureZone)."""

    _TYPE = EntityType.ZON

    SCH_SCHEDULE: vol.Schema = factory_schedule_zone(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_zone_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoZonConfigT) -> None:
        super().__init__(config[SZ_ZONE_ID], tcs)

        self._config: Final[EvoZonConfigT] = config  # type: ignore[assignment,misc]
        self._status: _EvoDictT = {}

        self._schedule: list[DayOfWeekZoneT] | None = None  # type: ignore[assignment]

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

        return tuple(self.setpoint_capabilities[SZ_ALLOWED_SETPOINT_MODES])

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

    # NOTE: this wrapper exists for typing purposes
    async def get_schedule(self) -> list[DayOfWeekZoneT]:  # type: ignore[override]
        """Get the schedule for this heating zone."""
        return await super().get_schedule()  # type: ignore[return-value]

    # NOTE: this wrapper exists for typing purposes
    async def set_schedule(self, schedule: list[DayOfWeekZoneT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this heating zone."""
        await super().set_schedule(schedule)  # type: ignore[arg-type]
