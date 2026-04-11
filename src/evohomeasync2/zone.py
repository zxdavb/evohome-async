"""Provides handling of TCC zones (heating and DHW)."""

from __future__ import annotations

import json
from datetime import UTC, datetime as dt, timedelta as td
from functools import cached_property
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from _evohome.helpers import as_local_time, camel_to_snake

from . import exceptions as exc
from .const import (
    _ERR_NOT_AVAILABLE,
    API_STRFTIME,
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SETPOINT_MODES,
    SZ_DAILY_SCHEDULES,
    SZ_DHW_STATE,
    SZ_FAULT_TYPE,
    SZ_HEAT_SETPOINT,
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
    SZ_TIME_OF_DAY,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)
from .schemas import (
    S2_HEAT_SETPOINT_VALUE,
    S2_SETPOINT_MODE,
    S2_SWITCHPOINTS,
    S2_TIME_UNTIL,
    DayOfWeekEnum,
    EntityTypeEnum,
    TccSetZonModeT,
    ZoneModeEnum,
    ZoneModelTypeEnum,
    ZoneTypeEnum,
)
from .schemas.schedule import factory_zon_schedule
from .schemas.status import factory_zon_status

if TYPE_CHECKING:
    import logging
    from datetime import tzinfo

    import voluptuous as vol

    from . import ControlSystem, Location
    from .auth import Auth
    from .schemas import (
        DailySchedulesT,
        DayOfWeekT,
        DayOfWeekZoneT,
        EvoActiveFaultResponseT,
        EvoDhwConfigEntryT,
        EvoDhwStatusResponseT,
        EvoGwyConfigEntryT,
        EvoGwyStatusResponseT,
        EvoLocConfigEntryT,
        EvoLocStatusResponseT,
        EvoTcsConfigEntryT,
        EvoTcsStatusResponseT,
        EvoTemperatureStatusResponseT,
        EvoZonConfigEntryT,
        EvoZonConfigResponseT,
        EvoZonScheduleCapabilitiesResponseT,
        EvoZonSetpointCapabilitiesResponseT,
        EvoZonSetpointStatusResponseT,
        EvoZonStatusResponseT,
        SwitchpointT,
    )

    _ScheduleT = list[DayOfWeekT]
    _SwitchPoint = tuple[dt, float | str]


_ONE_DAY = td(days=1)


class EntityBase:
    _TYPE: EntityTypeEnum  # e.g. "temperatureControlSystem", "domesticHotWater"
    _STATUS_EXCLUDES: tuple[str, ...] = ()  # child keys to exclude from own status

    _config: (
        EvoLocConfigEntryT
        | EvoGwyConfigEntryT
        | EvoTcsConfigEntryT
        | EvoZonConfigEntryT
        | EvoDhwConfigEntryT
    )

    _status: (
        EvoDhwStatusResponseT
        | EvoGwyStatusResponseT
        | EvoLocStatusResponseT
        | EvoTcsStatusResponseT
        | EvoZonStatusResponseT
        | None
    )

    def __init__(self, entity_id: str) -> None:
        self._id: Final = entity_id

    def __str__(self) -> str:
        """Return a string representation of the entity."""
        return f"{self.__class__.__name__}(id='{self._id}')"

    @property
    def _auth(self) -> Auth:
        raise NotImplementedError

    @property
    def _logger(self) -> logging.Logger:
        raise NotImplementedError

    # Config attrs...

    @cached_property
    def id(self) -> str:
        return self._id

    @property  # not strictly static, but library largely assumes so
    def config(
        self,
    ) -> (
        EvoLocConfigEntryT
        | EvoGwyConfigEntryT
        | EvoTcsConfigEntryT
        | EvoZonConfigEntryT
        | EvoDhwConfigEntryT
    ):
        """Return the latest config of the entity."""
        return self._config

    # Status (state) attrs & methods...

    @property
    def status(
        self,
    ) -> (
        EvoLocStatusResponseT
        | EvoGwyStatusResponseT
        | EvoTcsStatusResponseT
        | EvoZonStatusResponseT
        | EvoDhwStatusResponseT
    ):
        """Return the latest status of the entity."""
        if self._status is None:
            raise exc.InvalidStatusError(_ERR_NOT_AVAILABLE.format(self))
        return self._status


class ActiveFaultsBase(EntityBase):
    """Provide the base for active faults."""

    location: Location  # used to get tzinfo

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._active_faults: list[EvoActiveFaultResponseT] = []
        self._last_logged: dict[str, dt] = {}  # OK to use a tz=UTC datetimes

    # Status (state) attrs & methods...

    def _update_faults(
        self,
        active_faults: list[EvoActiveFaultResponseT],
    ) -> None:
        """Maintain self._active_faults list and self._last_logged dict."""

        def hash_(fault: EvoActiveFaultResponseT) -> str:
            return f"{fault[SZ_SINCE]}_{fault[SZ_FAULT_TYPE]}"

        def log_as_active(fault: EvoActiveFaultResponseT) -> None:
            self._logger.warning(
                f"{self}: Active fault: {fault[SZ_SINCE]} {fault[SZ_FAULT_TYPE]}"
            )
            self._last_logged[hash_(fault)] = dt.now(tz=UTC)  # aware dtm not required

        def log_as_resolved(fault: EvoActiveFaultResponseT) -> None:
            self._logger.info(
                f"{self}: Fault cleared: {fault[SZ_SINCE]} {fault[SZ_FAULT_TYPE]}"
            )
            del self._last_logged[hash_(fault)]

        # Remove resolved (non-active) faults
        for fault in [f for f in self._active_faults if f not in active_faults]:
            log_as_resolved(fault)
            self._active_faults.remove(fault)

        # Add new (active) faults
        for fault in [f for f in active_faults if f not in self._active_faults]:
            log_as_active(fault)
            self._active_faults.append(fault)

        # Re-log active faults if necessary
        for fault in self._active_faults:
            if dt.now(tz=UTC) - self._last_logged[hash_(fault)] > _ONE_DAY:
                log_as_active(fault)

    @property
    def active_faults(self) -> tuple[EvoActiveFaultResponseT, ...]:
        """
        "activeFaults": [
            {
            "faultType": "GatewayCommunicationLost",
            "since": "2023-05-04T18:47:36.7727046"
            }
        ]
        """

        return tuple(self._active_faults)


def _dt_to_dow_and_tod(dtm: dt, tzinfo: tzinfo) -> tuple[DayOfWeekEnum, str]:
    """Return a pair of strings representing the local day of week and time of day."""
    dtm = as_local_time(dtm, tzinfo)
    day_of_week = list(DayOfWeekEnum)[dtm.weekday()]  # locale-independent
    return DayOfWeekEnum(day_of_week), dtm.strftime(
        "%H:%M"
    )  # TODO: localize, e.g. Montag?


def _find_switchpoints(
    schedule: _ScheduleT,
    day_of_week: DayOfWeekEnum,
    time_of_day: str,
) -> tuple[SwitchpointT, int, SwitchpointT, int]:
    """Find this/next switchpoints for a given day of week and time of day."""

    if not schedule:
        raise exc.InvalidScheduleError("No schedule (daily schedules are empty)")

    # assumes 1+ switchpoint per day, which could be this_sp or next_sp only

    try:
        day_idx = list(DayOfWeekEnum).index(day_of_week)
    except ValueError as err:
        raise TypeError(f"Invalid parameter: {day_of_week}") from err

    this_sp: SwitchpointT | None = None
    next_sp: SwitchpointT | None = None

    this_offset = 0
    next_offset = 0

    # Check the switchpoints of the given day of week
    for sp in schedule[day_idx][S2_SWITCHPOINTS]:
        if sp[SZ_TIME_OF_DAY] <= time_of_day:
            this_sp = sp
            continue

        if sp[SZ_TIME_OF_DAY] > time_of_day:
            if this_sp is None:
                if not (prev_day := schedule[(day_idx + 6) % 7][S2_SWITCHPOINTS]):
                    raise exc.InvalidScheduleError("No switchpoints for previous day")
                this_sp = prev_day[-1]
                this_offset = -1

            next_sp = sp
            break

    else:
        assert this_sp is not None  # mypy

        if next_sp is None:
            if not (next_day := schedule[(day_idx + 1) % 7][S2_SWITCHPOINTS]):
                raise exc.InvalidScheduleError("No switchpoints for next day")
            next_sp = next_day[0]
            next_offset = +1

    return this_sp, this_offset, next_sp, next_offset


class _ScheduleBase(ActiveFaultsBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    SCH_SCHEDULE: vol.Schema

    _schedule: _ScheduleT | None

    _this_switchpoint: _SwitchPoint  # is float for zones...
    _next_switchpoint: _SwitchPoint  # and str for DHW

    location: Location  # used to get tzinfo

    # Status (state) attrs & methods...

    @property
    def schedule(self) -> _ScheduleT:
        """Return the schedule (assumes it is current)."""

        if not self._schedule:
            raise exc.InvalidScheduleError(f"{self}: No Schedule, or is invalid")

        return self._schedule

    @property
    def this_switchpoint(self) -> _SwitchPoint:
        """Return the start datetime and setpoint of the current switchpoint."""

        if not self._schedule:
            raise exc.InvalidScheduleError(f"{self}: No Schedule, or is invalid")

        if self._next_switchpoint[0] > (dt_now := dt.now(tz=UTC)):
            return self._this_switchpoint

        self._this_switchpoint, self._next_switchpoint = self._find_switchpoints(dt_now)
        return self._this_switchpoint

    @property
    def next_switchpoint(self) -> _SwitchPoint:
        """Return the start datetime and setpoint of the next switchpoint."""

        if not self._schedule:
            raise exc.InvalidScheduleError(f"{self}: No Schedule, or is invalid")

        if self._next_switchpoint[0] > (dt_now := dt.now(tz=UTC)):
            return self._next_switchpoint

        self._this_switchpoint, self._next_switchpoint = self._find_switchpoints(dt_now)

        return self._next_switchpoint

    async def get_schedule(self) -> _ScheduleT:
        """Get the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Getting schedule...")

        try:
            schedule: DailySchedulesT = await self._auth.get(
                f"{self._TYPE}/{self.id}/schedule",
                schema=self.SCH_SCHEDULE,
            )  # type: ignore[assignment]

        except exc.ApiCallFailedError as err:
            if err.status == HTTPStatus.BAD_REQUEST:  # 400
                raise exc.InvalidScheduleError(
                    f"{self}: No Schedule, or is invalid"
                ) from err
            raise

        self._schedule = schedule[SZ_DAILY_SCHEDULES]

        self._this_switchpoint, self._next_switchpoint = self._find_switchpoints(
            dt.now(tz=UTC)
        )

        return self._schedule

    def _find_switchpoints(self, dtm: dt) -> tuple[_SwitchPoint, _SwitchPoint]:
        """Find the current (this) and next switchpoints for a given datetime.

        FYI: HA has traditionally exposed (as an extended_state_attr):
        {
            "this_sp_from": "2024-07-10T08:00:00+01:00",
            "this_sp_temp": 16.0,
            "next_sp_from": "2024-07-10T22:10:00+01:00",
            "next_sp_temp": 18.6,
        }
        """

        dtm = as_local_time(dtm, self.location.tzinfo)

        this_sp, this_offset, next_sp, next_offset = _find_switchpoints(
            self.schedule, *_dt_to_dow_and_tod(dtm, self.location.tzinfo)
        )

        this_tod = dt.strptime(this_sp[SZ_TIME_OF_DAY], "%H:%M:00").time()  # noqa: DTZ007
        next_tod = dt.strptime(next_sp[SZ_TIME_OF_DAY], "%H:%M:00").time()  # noqa: DTZ007

        this_dtm = dt.combine(dtm + td(days=this_offset), this_tod)
        next_dtm = dt.combine(dtm + td(days=next_offset), next_tod)

        # exactly one of "dhw_state" (str) or "heat_setpoint" (float) will be present
        this_val = (
            this_sp[SZ_DHW_STATE]
            if SZ_DHW_STATE in this_sp
            else this_sp[SZ_HEAT_SETPOINT]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        )
        next_val = (
            next_sp[SZ_DHW_STATE]
            if SZ_DHW_STATE in next_sp
            else next_sp[SZ_HEAT_SETPOINT]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        )

        return (
            (this_dtm.replace(tzinfo=self.location.tzinfo), this_val),
            (next_dtm.replace(tzinfo=self.location.tzinfo), next_val),
        )

    async def set_schedule(
        self,
        schedule: _ScheduleT | str,
    ) -> None:
        """Set the schedule for this DHW/zone object."""

        self._logger.debug(f"{self}: Setting schedule...")

        if isinstance(schedule, list):
            try:
                json.dumps(schedule)
            except (OverflowError, TypeError, ValueError) as err:
                raise exc.BadScheduleUploadedError(
                    f"{self}: Invalid schedule: {err}"
                ) from err

        elif isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError as err:
                raise exc.BadScheduleUploadedError(
                    f"{self}: Invalid schedule: {err}"
                ) from err

            assert isinstance(schedule, list)  # mypy

        else:
            raise exc.BadScheduleUploadedError(
                f"{self}: Invalid schedule: {type(schedule)} is not JSON serializable"
            )

        _ = await self._auth.put(
            f"{self._TYPE}/{self.id}/schedule",
            json={"daily_schedules": schedule},
            schema=self.SCH_SCHEDULE,
        )

        # TODO: check the status of the task

        self._schedule = schedule


class _ZoneBase(_ScheduleBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    SCH_STATUS: vol.Schema

    _status: EvoDhwStatusResponseT | EvoZonStatusResponseT | None

    def __init__(self, entity_id: str, tcs: ControlSystem) -> None:
        super().__init__(entity_id)

        self.location = tcs.location
        self.tcs = tcs

    @cached_property
    def _auth(self) -> Auth:
        return self.location.client.auth

    @cached_property
    def _logger(self) -> logging.Logger:
        return self.location.client.logger

    # Status (state) attrs & methods...

    @property
    def status(self) -> EvoDhwStatusResponseT | EvoZonStatusResponseT:
        """Return the latest status of the entity."""
        return super().status  # type: ignore[return-value]

    async def _get_status(self) -> EvoDhwStatusResponseT | EvoZonStatusResponseT:
        """Get the latest state of this entity (DHW/zone) and update its status.

        This is a working vendor API endpoint, retained for use by the test suite.
        For normal use, prefer Location.update() as a single GET updates all
        descendants more efficiently. Returns the raw JSON of the latest state.
        """

        self._logger.warning(
            f"{self}: prefer Location.update() for more efficient status retrieval"
        )

        status: EvoDhwStatusResponseT | EvoZonStatusResponseT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status",
            schema=self.SCH_STATUS,
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(
        self, status: EvoDhwStatusResponseT | EvoZonStatusResponseT
    ) -> None:
        """Update the DHW/ZON's status."""

        self._update_faults(status[SZ_ACTIVE_FAULTS])
        self._status = status

    @property
    def temperature_status(self) -> EvoTemperatureStatusResponseT:
        """
        "temperatureStatus": {
            "temperature": 20.0,
            "isAvailable": true
        }
        """

        return self.status[SZ_TEMPERATURE_STATUS]

    @property  # a convenience attr
    def temperature(self) -> float | None:
        if not (status := self.temperature_status) or not status[SZ_IS_AVAILABLE]:
            return None

        assert SZ_TEMPERATURE in status  # mypy hint
        return status[SZ_TEMPERATURE]


class Zone(_ZoneBase):
    """Instance of a TCS's heating Zone (temperatureZone)."""

    _TYPE = EntityTypeEnum.ZON

    SCH_SCHEDULE: vol.Schema = factory_zon_schedule(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_zon_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoZonConfigResponseT) -> None:
        super().__init__(config[SZ_ZONE_ID], tcs)

        self._config: Final[EvoZonConfigResponseT] = config  # type: ignore[misc]
        self._status: EvoZonStatusResponseT | None = None

        self._schedule: list[DayOfWeekZoneT] | None = None  # type: ignore[assignment]

        if not self.model or self.model == ZoneModelTypeEnum.UNKNOWN:
            raise exc.InvalidConfigError(
                f"{self}: Invalid model type '{self.model}' (is it a ghost zone?)"
            )
        if not self.type or self.type == ZoneTypeEnum.UNKNOWN:
            raise exc.InvalidConfigError(
                f"{self}: Invalid Zone type '{self.type}' (is it a ghost zone?)"
            )

        if self.model not in ZoneModelTypeEnum:
            self._logger.warning("%s: Unknown model type '%s' (YMMV)", self, self.model)
        if self.type not in ZoneTypeEnum:
            self._logger.warning("%s: Unknown Zone type '%s' (YMMV)", self, self.type)

    @property  # not strictly static, but library largely assumes so
    def config(self) -> EvoZonConfigEntryT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> EvoZonStatusResponseT:
        """Return the latest status of the entity."""
        return super().status  # type: ignore[return-value]

    # Config attrs...

    @cached_property
    def model(self) -> ZoneModelTypeEnum:
        return self._config[SZ_MODEL_TYPE]

    @property
    def name(self) -> str:
        if self._status is not None:
            return self._status[SZ_NAME]
        return self._config[SZ_NAME]

    @cached_property
    def type(self) -> ZoneTypeEnum:
        return self._config[SZ_ZONE_TYPE]

    @cached_property
    def schedule_capabilities(self) -> EvoZonScheduleCapabilitiesResponseT:
        """
        "scheduleCapabilities": {
            "maxSwitchpointsPerDay": 6,
            "minSwitchpointsPerDay": 1,
            "timingResolution": "00:10:00",
            "setpointValueResolution": 0.5
        }
        """

        return self._config[SZ_SCHEDULE_CAPABILITIES]

    @property
    def setpoint_capabilities(self) -> EvoZonSetpointCapabilitiesResponseT:
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

        return self._config[SZ_SETPOINT_CAPABILITIES]

    @cached_property
    def allowed_modes(self) -> tuple[ZoneModeEnum, ...]:
        return tuple(self.setpoint_capabilities[SZ_ALLOWED_SETPOINT_MODES])

    @property  # convenience attr
    def max_heat_setpoint(self) -> float:
        # consider: if not self.setpoint_capabilities["can_control_heat"]: return None
        return self.setpoint_capabilities[SZ_MAX_HEAT_SETPOINT]

    @property  # convenience attr
    def min_heat_setpoint(self) -> float:
        # consider: if not self.setpoint_capabilities["can_control_heat"]: return None
        return self.setpoint_capabilities[SZ_MIN_HEAT_SETPOINT]

    # Status (state) attrs & methods...

    @property
    def setpoint_status(self) -> EvoZonSetpointStatusResponseT:
        """
        "setpointStatus": {
            "targetHeatTemperature": 17.0,
            "setpointMode": "FollowSchedule"
        }
        "setpointStatus": {
            "targetHeatTemperature": 20.5,
            "setpointMode": "TemporaryOverride",
            "until": "2023-11-30T22:10:00Z"
        }
        """

        return self.status[SZ_SETPOINT_STATUS]

    @property
    def mode(self) -> ZoneModeEnum:
        return self.setpoint_status[SZ_SETPOINT_MODE]

    @property
    def target_heat_temperature(self) -> float:
        return self.setpoint_status[SZ_TARGET_HEAT_TEMPERATURE]

    @property
    def until(self) -> dt | None:
        if (until := self.setpoint_status.get("until")) is None:
            return None
        return as_local_time(until, self.location.tzinfo)

    async def _set_mode(self, zon_mode: TccSetZonModeT, /) -> None:
        """Set the Zone mode (heating only; cooling is not exposed by the API)."""

        # Issue a warning if we fail some basic sanity checks...
        if zon_mode[S2_SETPOINT_MODE] not in self.allowed_modes:
            self._logger.warning(
                f"{self}: Attempting unsupported {S2_SETPOINT_MODE}: {zon_mode}..."
            )

        if (temp := zon_mode.get(S2_HEAT_SETPOINT_VALUE)) is None:
            if zon_mode[S2_SETPOINT_MODE] != ZoneModeEnum.FOLLOW_SCHEDULE:
                self._logger.warning(
                    f"{self}: Attempting missing {S2_HEAT_SETPOINT_VALUE}: {zon_mode}..."
                )

        elif not self.min_heat_setpoint <= temp <= self.max_heat_setpoint:
            self._logger.warning(
                f"{self}: Attempting invalid {S2_HEAT_SETPOINT_VALUE}: {zon_mode}..."
            )

        await self._auth.put(
            f"{self._TYPE}/{self.id}/heatSetpoint", json=dict(zon_mode)
        )

    async def set_mode(
        self,
        mode: ZoneModeEnum,
        /,
        *,
        temperature: float | None = None,
        until: dt | None = None,
    ) -> None:
        """Set the Zone mode (heating setpoint mode)."""

        if mode not in self.allowed_modes:
            raise exc.InvalidZoneModeError(f"{self}: Unsupported mode: {mode}")

        zone_mode: TccSetZonModeT = {S2_SETPOINT_MODE: mode}

        if temperature is None:
            if mode in (
                ZoneModeEnum.PERMANENT_OVERRIDE,
                ZoneModeEnum.TEMPORARY_OVERRIDE,
            ):
                raise exc.InvalidZoneModeError(
                    f"{self}: For {mode}, temperature must not be None"
                )

        else:
            if mode == ZoneModeEnum.FOLLOW_SCHEDULE:  # also ZoneMode.VACATION_HOLD?
                raise exc.InvalidZoneModeError(
                    f"{self}: For {mode}, temperature must be None"
                )

            if not self.min_heat_setpoint <= temperature <= self.max_heat_setpoint:
                raise exc.InvalidZoneModeError(
                    f"{self}: Invalid temperature: {temperature} (out of range)"
                )

            zone_mode[S2_HEAT_SETPOINT_VALUE] = temperature

        if until is None:
            if mode == ZoneModeEnum.TEMPORARY_OVERRIDE:  # also ZoneMode.VACATION_HOLD?
                raise exc.InvalidZoneModeError(
                    f"{self}: For {mode}, until must not be None"
                )

        else:
            if mode in (ZoneModeEnum.FOLLOW_SCHEDULE, ZoneModeEnum.PERMANENT_OVERRIDE):
                raise exc.InvalidZoneModeError(
                    f"{self}: For {mode}, until must be None"
                )

            zone_mode[S2_TIME_UNTIL] = until.strftime(API_STRFTIME)

        await self._set_mode(zone_mode)

    async def reset(self) -> None:
        """Cancel any override and allow the Zone to follow its schedule."""
        await self.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE)

    # NOTE: no provision for cooling (not supported by API)
    async def set_temperature(
        self,
        temperature: float,
        /,
        *,
        until: dt | None = None,
    ) -> None:
        """Set the temperature of the zone (no provision for cooling)."""

        mode = (
            ZoneModeEnum.PERMANENT_OVERRIDE
            if until is None
            else ZoneModeEnum.TEMPORARY_OVERRIDE
        )
        await self.set_mode(mode, temperature=temperature, until=until)

    # NOTE: this wrapper exists only for typing purposes
    async def get_schedule(self) -> list[DayOfWeekZoneT]:  # type: ignore[override]
        """Get the schedule for this heating zone."""
        return await super().get_schedule()  # type: ignore[return-value]

    # NOTE: this wrapper exists only for typing purposes
    async def set_schedule(self, schedule: list[DayOfWeekZoneT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this heating zone."""
        await super().set_schedule(schedule)  # type: ignore[arg-type]
