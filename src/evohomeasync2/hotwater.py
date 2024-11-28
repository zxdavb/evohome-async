#!/usr/bin/env python3
"""Provides handling of TCC DHW zones."""

# TODO: add set_mode() for non-evohome modes

from __future__ import annotations

from datetime import datetime as dt
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
    from . import ControlSystem
    from .schemas import _EvoDictT
    from .schemas.typedefs import DayOfWeekDhwT, EvoDhwConfigT


class HotWater(_ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    STATUS_SCHEMA: Final = factory_dhw_status(camel_to_snake)  # type: ignore[misc]
    _TYPE: Final = EntityType.DHW  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final = factory_schedule_dhw(camel_to_snake)  # type: ignore[misc]

    def __init__(self, tcs: ControlSystem, config: EvoDhwConfigT) -> None:
        super().__init__(config[SZ_DHW_ID], tcs)

        self._config: Final[EvoDhwConfigT] = config  # type: ignore[assignment,misc]
        self._status: _EvoDictT = {}

        self._schedule: list[DayOfWeekDhwT] | None = None

    @property  # a for convenience attr
    def mode(self) -> ZoneMode | None:
        if (state_status := self.state_status) is None:
            return None
        ret: ZoneMode = state_status[SZ_MODE]
        return ret

    @property  # a convenience attr
    def modes(self) -> tuple[ZoneMode]:
        ret = tuple(self.state_capabilities[SZ_ALLOWED_MODES])
        return ret

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def schedule_capabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_SCHEDULE_CAPABILITIES_RESPONSE]
        return ret

    @property  # a convenience attr
    def state(self) -> DhwState | None:
        if (state_status := self.state_status) is None:
            return None
        ret: DhwState = state_status[SZ_STATE]
        return ret

    @property  # a convenience attr
    def states(self) -> tuple[DhwState]:
        ret: tuple[DhwState] = tuple(x.value for x in DhwState)  # type: ignore[assignment]
        return ret

    @property
    def state_capabilities(self) -> _EvoDictT:
        """
        "dhwStateCapabilitiesResponse": {
            "allowedStates": ["On", "Off"],
            "allowedModes": ["FollowSchedule", "PermanentOverride", "TemporaryOverride"],
            "maxDuration": "1.00:00:00",
            "timingResolution": "00:10:00"
        },
        """

        ret: _EvoDictT = self._config[SZ_DHW_STATE_CAPABILITIES_RESPONSE]
        return ret

    @property
    def state_status(self) -> _EvoDictT | None:
        return self._status.get(SZ_STATE_STATUS)

    @property
    def type(self) -> str:
        return "DomesticHotWater"

    def _next_setpoint(self) -> tuple[dt, str] | None:  # WIP: for convenience (new)
        """Return the datetime and state of the next setpoint."""
        raise NotImplementedError

    async def _set_state(self, mode: dict[str, str | None]) -> None:
        """Set the DHW mode (state)."""

        if mode[S2_MODE] not in self.modes:
            raise exc.InvalidParameterError(
                f"{self}: Unsupported/unknown {S2_MODE}: {mode}"
            )

        if mode[S2_STATE] not in self.states:
            raise exc.InvalidParameterError(
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

    async def get_schedule(self) -> list[DayOfWeekDhwT]:
        """Get the schedule for this DHW."""  # mypy hint
        return await super().get_schedule()  # type: ignore[return-value]

    async def set_schedule(self, schedule: list[DayOfWeekDhwT] | str) -> None:  # type: ignore[override]
        """Set the schedule for this DHW."""  # mypy hint
        await super().set_schedule(schedule)
