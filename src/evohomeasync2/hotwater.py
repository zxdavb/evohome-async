"""Provides handling of TCC DHW zones."""

# TODO: extend set_mode() for non-evohome modes

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

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
from .schemas import factory_dhw_status, factory_schedule_dhw
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


class HotWater(_ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    _TYPE = EntityType.DHW

    SCH_SCHEDULE: vol.Schema = factory_schedule_dhw(camel_to_snake)
    SCH_STATUS: vol.Schema = factory_dhw_status(camel_to_snake)

    def __init__(self, tcs: ControlSystem, config: EvoDhwConfigResponseT) -> None:
        super().__init__(config[SZ_DHW_ID], tcs)

        self._config: Final[EvoDhwConfigEntryT] = config  # type: ignore[misc]
        self._status: EvoDhwStatusResponseT | None = None

        self._schedule: list[DayOfWeekDhwT] | None = None  # type: ignore[assignment]

    @property  # TODO: deprecate in favour of .id attr
    def dhwId(self) -> str:  # noqa: N802
        return self._id

    @property  # a for convenience attr
    def mode(self) -> ZoneMode | None:
        if self.state_status is None:
            return None
        return self.state_status[SZ_MODE]

    @property  # a convenience attr
    def modes(self) -> tuple[ZoneMode, ...]:
        return tuple(self.state_capabilities[SZ_ALLOWED_MODES])

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def schedule_capabilities(self) -> EvoDhwScheduleCapabilitiesResponseT:
        return self._config[SZ_SCHEDULE_CAPABILITIES_RESPONSE]

    @property  # a convenience attr
    def state(self) -> DhwState | None:
        if self.state_status is None:
            return None
        return self.state_status[SZ_STATE]

    @property  # a convenience attr
    def states(self) -> tuple[DhwState, ...]:
        return tuple(self.state_capabilities["allowed_states"])

    @property
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

    @property
    def state_status(self) -> EvoDhwStateStatusResponseT | None:
        if self._status is None:
            return None
        return self._status[SZ_STATE_STATUS]

    @property
    def type(self) -> str:
        return "DomesticHotWater"

    def _next_setpoint(self) -> tuple[dt, str] | None:  # WIP: for convenience (new)
        """Return the datetime and state of the next setpoint."""
        raise NotImplementedError

    async def _set_state(self, mode: dict[str, str | None]) -> None:
        """Set the DHW mode (state)."""

        if mode[S2_MODE] not in self.modes:
            raise exc.BadApiRequestError(
                f"{self}: nsupported/unknown {S2_MODE}: {mode}"
            )

        if mode[S2_STATE] not in self.states:
            raise exc.BadApiRequestError(
                f"{self}: Unsupported/unknown {S2_STATE}: {mode}"
            )

        await self._auth.put(f"{self._TYPE}/{self.id}/state", json=mode)

    async def reset(self) -> None:
        """Cancel any override and allow the DHW to follow its schedule."""

        mode: dict[str, str | None] = {
            S2_MODE: ZoneMode.FOLLOW_SCHEDULE,
            S2_STATE: None,  # NOTE: was "state": ""
            S2_UNTIL_TIME: None,
        }

        await self._set_state(mode)

    async def set_on(self, /, *, until: dt | None = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        mode: dict[str, str | None]

        if until is None:
            mode = {
                S2_MODE: ZoneMode.PERMANENT_OVERRIDE,
                S2_STATE: DhwState.ON,
                S2_UNTIL_TIME: None,
            }
        else:
            mode = {
                S2_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                S2_STATE: DhwState.ON,
                S2_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_state(mode)

    async def set_off(self, /, *, until: dt | None = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        mode: dict[str, str | None]

        if until is None:
            mode = {
                S2_MODE: ZoneMode.PERMANENT_OVERRIDE,
                S2_STATE: DhwState.OFF,
                S2_UNTIL_TIME: None,
            }
        else:
            mode = {
                S2_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                S2_STATE: DhwState.OFF,
                S2_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_state(mode)

    # NOTE: this wrapper exists for typing purposes
    async def get_schedule(self) -> list[DayOfWeekDhwT]:  # type: ignore[override]
        """Get the schedule for this DHW zone."""
        return await super().get_schedule()  # type: ignore[return-value]

    # NOTE: this wrapper exists for typing purposes
    async def set_schedule(self, schedule: list[DayOfWeekDhwT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this DHW zone."""
        await super().set_schedule(schedule)  # type: ignore[arg-type]
