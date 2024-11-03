#!/usr/bin/env python3
"""Provides handling of TCC DHW zones."""

# TODO: add set_mode() for non-evohome modes

from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Final

from .const import API_STRFTIME
from .schema import (
    SCH_DHW_STATUS,
    SCH_GET_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_DHW,
    convert_keys_to_snake_case,
)
from .schema.const import (
    S2_ALLOWED_MODES,
    S2_DHW_ID,
    S2_DHW_STATE_CAPABILITIES_RESPONSE,
    S2_MODE,
    S2_SCHEDULE_CAPABILITIES_RESPONSE,
    S2_STATE,
    S2_STATE_STATUS,
    S2_UNTIL_TIME,
    DhwState,
    EntityType,
    ZoneMode,
)
from .zone import _ZoneBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import ControlSystem
    from .schema import _EvoDictT, _EvoListT


class HotWater(_ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    STATUS_SCHEMA: Final = SCH_DHW_STATUS  # type: ignore[misc]
    TYPE: Final = EntityType.DHW  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final[vol.Schema] = SCH_GET_SCHEDULE_DHW  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final[vol.Schema] = SCH_PUT_SCHEDULE_DHW  # type: ignore[misc]

    def __init__(self, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(config[S2_DHW_ID], tcs, config)

    @property
    def state_capabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[S2_DHW_STATE_CAPABILITIES_RESPONSE]
        return convert_keys_to_snake_case(ret)

    @property
    def schedule_capabilities(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[S2_SCHEDULE_CAPABILITIES_RESPONSE]
        return convert_keys_to_snake_case(ret)

    @property  # for convenience (is not a top-level config attribute)
    def allowed_modes(self) -> _EvoListT:
        ret: _EvoListT = self._config[S2_DHW_STATE_CAPABILITIES_RESPONSE][
            S2_ALLOWED_MODES
        ]
        return convert_keys_to_snake_case(ret)

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def state_status(self) -> _EvoDictT | None:
        return self._status.get(S2_STATE_STATUS)

    @property  # status attr for convenience (new)
    def mode(self) -> str | None:
        if (state_status := self._status.get(S2_STATE_STATUS)) is None:
            return None
        ret: str = state_status[S2_MODE]
        return ret

    @property  # status attr for convenience (new)
    def state(self) -> str | None:
        if (state_status := self._status.get(S2_STATE_STATUS)) is None:
            return None
        ret: str = state_status[S2_STATE]
        return ret

    def _next_setpoint(self) -> tuple[dt, str] | None:  # WIP: for convenience (new)
        """Return the datetime and state of the next setpoint."""
        raise NotImplementedError

    async def _set_mode(self, mode: dict[str, str | None]) -> None:
        """Set the DHW mode (state)."""
        _ = await self._broker.put(f"{self.TYPE}/{self.id}/state", json=mode)

    async def reset_mode(self) -> None:
        """Cancel any override and allow the DHW to follow its schedule."""

        mode: dict[str, str | None] = {  # NOTE: S2_STATE was previously ""
            S2_MODE: ZoneMode.FOLLOW_SCHEDULE,
            S2_STATE: None,
            S2_UNTIL_TIME: None,
        }

        await self._set_mode(mode)

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

        await self._set_mode(mode)

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

        await self._set_mode(mode)
