"""Provides handling of TCC DHW zones."""

# TODO: extend set_mode() for non-evohome modes

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Final

from _evohome.helpers import as_local_time, camel_to_snake

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ALLOWED_MODES,
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_MODE,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_STATE,
    SZ_STATE_STATUS,
)
from .schemas import (
    S2_MODE,
    S2_STATE,
    S2_UNTIL_TIME,
    DhwStateEnum,
    EntityTypeEnum,
    TccSetDhwModeT,
    ZoneModeEnum,
)
from .schemas.schedule import factory_dhw_schedule
from .schemas.status import factory_dhw_status
from .zone import _ZoneBase

if TYPE_CHECKING:
    from datetime import datetime as dt

    import voluptuous as vol

    from . import ControlSystem
    from .schemas import (
        DayOfWeekDhwT,
        EvoDhwConfigEntryT,
        EvoDhwConfigResponseT,
        EvoDhwScheduleCapabilitiesResponseT,
        EvoDhwStateCapabilitiesResponseT,
        EvoDhwStateStatusResponseT,
        EvoDhwStatusResponseT,
    )


class HotWater(_ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    _TYPE = EntityTypeEnum.DHW

    SCH_SCHEDULE: vol.Schema = factory_dhw_schedule(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_dhw_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoDhwConfigResponseT) -> None:
        super().__init__(config[SZ_DHW_ID], tcs)

        self._config: Final[EvoDhwConfigEntryT] = config  # type: ignore[misc]
        self._status: EvoDhwStatusResponseT | None = None

        self._schedule: list[DayOfWeekDhwT] | None = None  # type: ignore[assignment]

    @property  # not strictly static, but library largely assumes so
    def config(self) -> EvoDhwConfigEntryT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> EvoDhwStatusResponseT:
        """Return the latest status of the entity."""
        return super().status  # type: ignore[return-value]

    # Config attrs...

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def type(self) -> str:
        return "DomesticHotWater"

    @cached_property  # NOTE: renamed config key: was schedule_capabilities_response
    def schedule_capabilities(self) -> EvoDhwScheduleCapabilitiesResponseT:
        """
        "scheduleCapabilitiesResponse": {
          "maxSwitchpointsPerDay": 6,
          "minSwitchpointsPerDay": 1,
          "timingResolution": "00:10:00"
        }
        """

        return self._config[SZ_SCHEDULE_CAPABILITIES_RESPONSE]

    @cached_property  # NOTE: renamed config key: was dhw_state_capabilities_response
    def state_capabilities(self) -> EvoDhwStateCapabilitiesResponseT:
        """
        "dhwStateCapabilitiesResponse": {
            "allowedStates": ["On", "Off"],
            "allowedModes": ["FollowSchedule", "PermanentOverride", "TemporaryOverride"],
            "maxDuration": "1.00:00:00",
            "timingResolution": "00:10:00"
        },
        """

        return self._config[SZ_DHW_STATE_CAPABILITIES_RESPONSE]

    @cached_property
    def allowed_modes(self) -> tuple[ZoneModeEnum, ...]:
        return tuple(self.state_capabilities[SZ_ALLOWED_MODES])

    @cached_property
    def allowed_states(self) -> tuple[DhwStateEnum, ...]:
        return tuple(self.state_capabilities["allowed_states"])

    # Status (state) attrs & methods...

    @property
    def state_status(self) -> EvoDhwStateStatusResponseT:
        """
        "stateStatus": {"state": "Off", "mode": "PermanentOverride"}
        "stateStatus": {
            "state": "Off",
            "mode": "TemporaryOverride",
            until": "2023-11-30T22:10:00Z"
        }
        """

        return self.status[SZ_STATE_STATUS]

    @property
    def mode(self) -> ZoneModeEnum:
        return self.state_status[SZ_MODE]

    @property
    def state(self) -> DhwStateEnum:
        return self.state_status[SZ_STATE]

    @property
    def until(self) -> dt | None:
        if (until := self.state_status.get("until")) is None:
            return None
        return as_local_time(until, self.location.tzinfo)

    async def _set_mode(self, dhw_mode: TccSetDhwModeT, /) -> None:
        """Set the DHW mode (state)."""

        # Issue a warning if we fail some basic sanity checks...
        if dhw_mode[S2_MODE] not in self.allowed_modes:
            self._logger.warning(
                f"{self}: Attempting unsupported {S2_MODE}: {dhw_mode}..."
            )

        if not (state := dhw_mode.get(S2_STATE)):
            if dhw_mode[S2_MODE] != ZoneModeEnum.FOLLOW_SCHEDULE:
                self._logger.warning(
                    f"{self}: Attempting invalid {S2_MODE}/{S2_STATE}: {dhw_mode}..."
                )

        elif state not in self.allowed_states:
            self._logger.warning(
                f"{self}: Attempting unsupported {S2_STATE}: {dhw_mode}..."
            )

        await self._auth.put(f"{self._TYPE}/{self.id}/state", json=dict(dhw_mode))

    async def set_mode(
        self,
        mode: ZoneModeEnum,
        /,
        *,
        state: DhwStateEnum | None = None,
        until: dt | None = None,
    ) -> None:
        """Set the DHW mode, either indefinitely or until a given time."""

        if mode not in self.allowed_modes:
            raise exc.InvalidDhwModeError(f"{self}: Unsupported mode: {mode}")

        dhw_mode: TccSetDhwModeT = {S2_MODE: mode}

        if state is None:
            if mode in (
                ZoneModeEnum.PERMANENT_OVERRIDE,
                ZoneModeEnum.TEMPORARY_OVERRIDE,
            ):
                raise exc.InvalidDhwModeError(
                    f"{self}: For {mode}, state must not be None"
                )

        else:
            if mode == ZoneModeEnum.FOLLOW_SCHEDULE:  # also ZoneMode.VACATION_HOLD?
                raise exc.InvalidDhwModeError(f"{self}: For {mode}, state must be None")

            dhw_mode[S2_STATE] = state

        if until is None:
            if mode == ZoneModeEnum.TEMPORARY_OVERRIDE:  # also ZoneMode.VACATION_HOLD?
                raise exc.InvalidDhwModeError(
                    f"{self}: For {mode}, until must not be None"
                )

        else:
            if mode in (ZoneModeEnum.FOLLOW_SCHEDULE, ZoneModeEnum.PERMANENT_OVERRIDE):
                raise exc.InvalidDhwModeError(f"{self}: For {mode}, until must be None")

            dhw_mode[S2_UNTIL_TIME] = until.strftime(API_STRFTIME)

        await self._set_mode(dhw_mode)

    async def reset(self) -> None:
        """Cancel any override and allow the DHW to follow its schedule."""
        await self.set_mode(ZoneModeEnum.FOLLOW_SCHEDULE)

    async def set_off(self, /, *, until: dt | None = None) -> None:
        """Set the DHW off until a given time, or permanently."""
        await self.set_state(DhwStateEnum.OFF, until=until)

    async def set_on(self, /, *, until: dt | None = None) -> None:
        """Set the DHW on until a given time, or permanently."""
        await self.set_state(DhwStateEnum.ON, until=until)

    async def set_state(
        self, state: DhwStateEnum, /, *, until: dt | None = None
    ) -> None:
        """Set the DHW state, either indefinitely or until a given time."""

        mode = (
            ZoneModeEnum.PERMANENT_OVERRIDE
            if until is None
            else ZoneModeEnum.TEMPORARY_OVERRIDE
        )
        await self.set_mode(mode, state=state, until=until)

    # NOTE: this wrapper exists only for typing purposes
    async def get_schedule(self) -> list[DayOfWeekDhwT]:  # type: ignore[override]
        """Get the schedule for this DHW zone."""
        return await super().get_schedule()  # type: ignore[return-value]

    # NOTE: this wrapper exists only for typing purposes
    async def set_schedule(self, schedule: list[DayOfWeekDhwT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this DHW zone."""
        await super().set_schedule(schedule)  # type: ignore[arg-type]
