"""Provides handling of TCC zones (heating and DHW)."""

# TODO: extend set_mode() for non-evohome modes (e.g. "VacationHold")

from __future__ import annotations

import json
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .const import (
    API_STRFTIME,
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
from .schemas import factory_zon_schedule, factory_zon_status
from .schemas.const import (
    S2_HEAT_SETPOINT_VALUE,
    S2_SETPOINT_MODE,
    S2_TIME_UNTIL,
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

    from . import ControlSystem, Location
    from .auth import Auth
    from .schemas.typedefs import (
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

    ScheduleT = list[DayOfWeekT]


_ONE_DAY = td(days=1)


class EntityBase:
    _TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

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
            raise exc.InvalidStatusError(
                "No status available (have not invoked Location.update()?)"
            )
        return self._status


class ActiveFaultsBase(EntityBase):
    """Provide the base for active faults."""

    location: Location

    def __init__(self, entity_id: str, broker: Auth, logger: logging.Logger) -> None:
        super().__init__(entity_id, broker, logger)

        self._active_faults: list[EvoActiveFaultResponseT] = []
        self._last_logged: dict[str, dt] = {}  # OK to use a tz=UTC datetimes

    def _update_faults(
        self,
        active_faults: list[EvoActiveFaultResponseT],
    ) -> None:
        last_logged = {}

        def hash_(fault: EvoActiveFaultResponseT) -> str:
            return f"{fault[SZ_FAULT_TYPE]}_{fault[SZ_SINCE]}"

        def log_as_active(fault: EvoActiveFaultResponseT) -> None:
            self._logger.warning(
                f"Active fault: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            last_logged[hash_(fault)] = dt.now(tz=UTC)  # aware dtm not required

        def log_as_resolved(fault: EvoActiveFaultResponseT) -> None:
            self._logger.info(
                f"Fault cleared: {self}: {fault[SZ_FAULT_TYPE]}, since {fault[SZ_SINCE]}"
            )
            del self._last_logged[hash_(fault)]

        for fault in active_faults:
            if fault not in self.active_faults:  # new active fault
                log_as_active(fault)

        for fault in self.active_faults:
            if fault not in active_faults:  # fault resolved
                log_as_resolved(fault)

            elif dt.now(tz=UTC) - self._last_logged[hash_(fault)] > _ONE_DAY:
                log_as_active(fault)

        # self._active_faults = [
        #     {**fault, "since": as_local_time(fault["since"], self.location.tzinfo)}
        #     for fault in active_faults
        # ]
        self._active_faults = active_faults
        self._last_logged |= last_logged

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


def as_local_time(dtm: dt | str, tzinfo: tzinfo) -> dt:
    """Convert a datetime into a aware datetime in the given TZ."""
    if isinstance(dtm, str):
        dtm = dt.fromisoformat(dtm)
    return dtm.replace(tzinfo=tzinfo) if dtm.tzinfo is None else dtm.astimezone(tzinfo)


def _dt_to_dow_and_tod(dtm: dt, tzinfo: tzinfo) -> tuple[DayOfWeek, str]:
    """Return a pair of strings representing the local day of week and time of day."""
    dtm = as_local_time(dtm, tzinfo)
    return dtm.strftime("%A"), dtm.strftime("%H:%M")  # type: ignore[return-value]


def _find_switchpoints(
    schedule: ScheduleT,
    day_of_week: DayOfWeek,
    time_of_day: str,
) -> tuple[SwitchpointT, int, SwitchpointT, int]:
    """Find this/next switchpoints for a given day of week and time of day."""

    # TODO: schedule can be [], i.e. response was {'DailySchedules': []}

    # assumes 1+ switchpoint per day, which could be this_sp or next_sp only

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
        assert this_sp is not None  # mypy (internal hint)

        if next_sp is None:
            next_sp = schedule[(day_idx + 1) % 7]["switchpoints"][0]
            next_offset = +1

    return this_sp, this_offset, next_sp, next_offset


class _ScheduleBase(ActiveFaultsBase):
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    SCH_SCHEDULE: vol.Schema

    _config: EvoDhwConfigEntryT | EvoZonConfigEntryT | None  # type: ignore[assignment]
    _status: EvoDhwStatusResponseT | EvoZonStatusResponseT | None

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

            assert isinstance(schedule, list)  # mypy (internal hint)

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

    def _find_switchpoints(self, dtm: dt | str) -> dict[dt, float | str]:
        """Find the current and next switchpoints for a given day and time of day."""

        if not self._schedule:
            raise exc.InvalidScheduleError("No schedule available")

        if isinstance(dtm, str):
            dtm = dt.fromisoformat(dtm)

        dtm = as_local_time(dtm, self.location.tzinfo)

        this_sp, this_offset, next_sp, next_offset = _find_switchpoints(
            self._schedule, *_dt_to_dow_and_tod(dtm, self.location.tzinfo)
        )

        this_tod = dt.strptime(this_sp["time_of_day"], "%H:%M").time()  # noqa: DTZ007
        next_tod = dt.strptime(next_sp["time_of_day"], "%H:%M").time()  # noqa: DTZ007

        this_dtm = dt.combine(dtm + td(days=this_offset), this_tod)
        next_dtm = dt.combine(dtm + td(days=next_offset), next_tod)

        # either "dhw_state" or "heat_setpoint" _will_ be present...
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
        self.tcs = tcs

    async def _update(self) -> EvoDhwStatusResponseT | EvoZonStatusResponseT:
        """Get the latest state of the DHW/zone and update its status.

        It is more efficient to call Location.update() as all zones are updated
        with a single GET.

        Returns the raw JSON of the latest state.
        """

        status: EvoDhwStatusResponseT | EvoZonStatusResponseT = await self._auth.get(  # type: ignore[assignment]
            f"{self._TYPE}/{self.id}/status", schema=self.SCH_STATUS
        )

        self._update_status(status)
        return status

    def _update_status(
        self, status: EvoDhwStatusResponseT | EvoZonStatusResponseT
    ) -> None:
        self._update_faults(status["active_faults"])
        self._status = status

    @property
    def temperature_status(self) -> EvoTemperatureStatusResponseT | None:
        """
        "temperatureStatus": {
            "temperature": 20.0,
            "isAvailable": true
        }
        """
        if self._status is None:
            return None
        return self._status[SZ_TEMPERATURE_STATUS]

    @property  # a convenience attr
    def temperature(self) -> float | None:
        if not (status := self.temperature_status) or not status[SZ_IS_AVAILABLE]:
            return None

        return status[SZ_TEMPERATURE]


class Zone(_ZoneBase):
    """Instance of a TCS's heating zone (temperatureZone)."""

    _TYPE = EntityType.ZON

    SCH_SCHEDULE: vol.Schema = factory_zon_schedule(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_zon_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoZonConfigResponseT) -> None:
        super().__init__(config[SZ_ZONE_ID], tcs)

        self._config: Final[EvoZonConfigResponseT] = config  # type: ignore[misc]
        self._status: EvoZonStatusResponseT | None = None

        self._schedule: list[DayOfWeekZoneT] | None = None  # type: ignore[assignment]

        if not self.model or self.model == ZoneModelType.UNKNOWN:
            raise exc.InvalidConfigError(
                f"{self}: Invalid model type '{self.model}' (is it a ghost zone?)"
            )
        if not self.type or self.type == ZoneType.UNKNOWN:
            raise exc.InvalidConfigError(
                f"{self}: Invalid zone type '{self.type}' (is it a ghost zone?)"
            )

        if self.model not in ZoneModelType:
            self._logger.warning("%s: Unknown model type '%s' (YMMV)", self, self.model)
        if self.type not in ZoneType:
            self._logger.warning("%s: Unknown zone type '%s' (YMMV)", self, self.type)

    @property  # TODO: deprecate in favour of .id attr
    def zoneId(self) -> str:  # noqa: N802
        return self._id

    @property
    def model(self) -> ZoneModelType:
        return self._config[SZ_MODEL_TYPE]

    @property
    def type(self) -> ZoneType:
        return self._config[SZ_ZONE_TYPE]

    @property
    def name(self) -> str:
        if self._status is not None:
            return self._status[SZ_NAME]
        return self._config[SZ_NAME]

    @property
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

    @property  # convenience attr
    def max_heat_setpoint(self) -> float:
        # consider: if not self.setpoint_capabilities["can_control_heat"]: return None
        return self.setpoint_capabilities[SZ_MAX_HEAT_SETPOINT]

    @property  # convenience attr
    def min_heat_setpoint(self) -> float:
        # consider: if not self.setpoint_capabilities["can_control_heat"]: return None
        return self.setpoint_capabilities[SZ_MIN_HEAT_SETPOINT]

    @property  # a convenience attr
    def modes(self) -> tuple[ZoneMode, ...]:
        """
        "allowedSetpointModes": [
            "PermanentOverride", "FollowSchedule", "TemporaryOverride"
        ]
        """

        return tuple(self.setpoint_capabilities[SZ_ALLOWED_SETPOINT_MODES])

    @property
    def setpoint_status(self) -> EvoZonSetpointStatusResponseT | None:
        """
        "setpointStatus": {
            "targetHeatTemperature": 17.0,
            "setpointMode": "FollowSchedule"
        }
        """
        if self._status is None:
            return None
        return self._status[SZ_SETPOINT_STATUS]

    @property  # a convenience attr
    def mode(self) -> ZoneMode | None:
        if not self.setpoint_status:
            return None
        return self.setpoint_status[SZ_SETPOINT_MODE]

    @property  # a convenience attr (one day a target_cool_temperature may be added?)
    def target_heat_temperature(self) -> float | None:
        if self.setpoint_status is None:
            return None
        return self.setpoint_status[SZ_TARGET_HEAT_TEMPERATURE]

    async def _set_mode(self, mode: dict[str, str | float]) -> None:
        """Set the zone mode (heat_setpoint, cooling is TBD)."""

        if mode[S2_SETPOINT_MODE] not in self.modes:
            raise exc.BadApiRequestError(
                f"{self}: Unsupported/unknown {S2_SETPOINT_MODE}: {mode}"
            )

        temp: float | None = mode.get(S2_HEAT_SETPOINT_VALUE)  # type: ignore[assignment]
        if temp is not None and self.min_heat_setpoint > temp > self.max_heat_setpoint:
            raise exc.BadApiRequestError(
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
