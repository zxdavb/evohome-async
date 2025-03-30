"""Provides handling of TCC DHW zones."""

# TODO: extend set_mode() for non-evohome modes

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Final, NotRequired, TypedDict

from evohome.helpers import as_local_time, camel_to_snake

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
from .schemas import factory_dhw_schedule, factory_dhw_status
from .schemas.const import (
    S2_MODE,
    S2_STATE,
    S2_UNTIL_TIME,
    DhwState,
    EntityType,
    ZoneMode,
)
from .zone import _ZoneBase

if TYPE_CHECKING:
    from datetime import datetime as dt

    import voluptuous as vol

    from . import ControlSystem
    from .schemas.typedefs import (
        DayOfWeekDhwT,
        EvoDhwConfigEntryT,
        EvoDhwConfigResponseT,
        EvoDhwScheduleCapabilitiesResponseT,
        EvoDhwStateCapabilitiesResponseT,
        EvoDhwStateStatusResponseT,
        EvoDhwStatusResponseT,
    )


class TccSetDhwModeT(TypedDict):  # TODO: timeUntil?
    """PUT /domesticHotWater/{dhw_id}/state"""

    mode: ZoneMode
    state: NotRequired[DhwState | None]  # not required for FollowSchedule
    untilTime: NotRequired[str | None]  # only required for TemporaryOverride


class HotWater(_ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    _TYPE = EntityType.DHW

    SCH_SCHEDULE: vol.Schema = factory_dhw_schedule(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_dhw_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoDhwConfigResponseT) -> None:
        super().__init__(config[SZ_DHW_ID], tcs)

        self._config: Final[EvoDhwConfigEntryT] = config  # type: ignore[misc]
        self._status: EvoDhwStatusResponseT | None = None

        self._schedule: list[DayOfWeekDhwT] | None = None  # type: ignore[assignment]

    @property
    def config(self) -> EvoDhwConfigEntryT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> EvoDhwStatusResponseT:
        """Return the latest status of the entity."""
        return super().status  # type: ignore[return-value]

    # Config attrs...

    @cached_property
    def name(self) -> str:
        return "Domestic Hot Water"

    @cached_property
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
    def allowed_modes(self) -> tuple[ZoneMode, ...]:
        return tuple(self.state_capabilities[SZ_ALLOWED_MODES])

    @cached_property
    def allowed_states(self) -> tuple[DhwState, ...]:
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

        if self._status is None:
            raise exc.InvalidStatusError(f"{self} has no state, has it been fetched?")
        return self._status[SZ_STATE_STATUS]

    @property
    def mode(self) -> ZoneMode:
        return self.state_status[SZ_MODE]

    @property
    def state(self) -> DhwState:
        return self.state_status[SZ_STATE]

    @property
    def until(self) -> dt | None:
        if (until := self.state_status.get("until")) is None:
            return None
        return as_local_time(until, self.location.tzinfo)

    async def _set_mode(self, mode: TccSetDhwModeT) -> None:
        """Set the DHW mode (state)."""

        # Do some basic sanity checks...
        if mode[S2_MODE] not in self.allowed_modes:
            self._logger.warning(f"{self}: Unsupported/unknown {S2_MODE}: {mode}")

        if not (state := mode.get(S2_STATE)):
            if mode[S2_MODE] != ZoneMode.FOLLOW_SCHEDULE:
                self._logger.warning(f"{self}: Missing/invalid {S2_STATE}: {mode}")

        elif state not in self.allowed_states:
            self._logger.warning(f"{self}: Unsupported/unknown {S2_STATE}: {mode}")

        # Call the API...
        await self._auth.put(f"{self._TYPE}/{self.id}/state", json=dict(mode))

    async def set_mode(self, state: DhwState, /, *, until: dt | None = None) -> None:
        """Set the DHW mode (state)."""

        mode: TccSetDhwModeT

        if until is None:
            mode = {
                S2_MODE: ZoneMode.PERMANENT_OVERRIDE,
                S2_STATE: state,
                S2_UNTIL_TIME: None,
            }
        else:
            mode = {
                S2_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                S2_STATE: state,
                S2_UNTIL_TIME: until.strftime(API_STRFTIME),  # TODO: S2_TIME_UNTIL?
            }

        await self._set_mode(mode)

    async def reset(self) -> None:
        """Cancel any override and allow the DHW to follow its schedule."""

        mode: TccSetDhwModeT = {
            S2_MODE: ZoneMode.FOLLOW_SCHEDULE,
            S2_STATE: None,  # NOTE: was "state": ""
            S2_UNTIL_TIME: None,
        }

        await self._set_mode(mode)

    async def off(self, /, *, until: dt | None = None) -> None:
        """Set the DHW off until a given time, or permanently."""
        await self.set_mode(DhwState.OFF, until=until)

    async def on(self, /, *, until: dt | None = None) -> None:
        """Set the DHW on until a given time, or permanently."""
        await self.set_mode(DhwState.ON, until=until)

    # NOTE: this wrapper exists only for typing purposes
    async def get_schedule(self) -> list[DayOfWeekDhwT]:  # type: ignore[override]
        """Get the schedule for this DHW zone."""
        return await super().get_schedule()  # type: ignore[return-value]

    # NOTE: this wrapper exists only for typing purposes
    async def set_schedule(self, schedule: list[DayOfWeekDhwT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this DHW zone."""
        await super().set_schedule(schedule)  # type: ignore[arg-type]
