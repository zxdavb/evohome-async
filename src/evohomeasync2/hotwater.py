#!/usr/bin/env python3
"""Provides handling of TCC DHW zones."""

# TODO: add set_mode() for non-evohome modes

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, NoReturn

from . import exceptions as exc
from .const import API_STRFTIME
from .schema import SCH_DHW_STATUS, SCH_GET_SCHEDULE_DHW, SCH_PUT_SCHEDULE_DHW
from .schema.const import (
    SZ_ALLOWED_MODES,
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_DOMESTIC_HOT_WATER,
    SZ_MODE,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_STATE,
    SZ_STATE_STATUS,
    SZ_UNTIL_TIME,
    DhwState,
    ZoneMode,
)
from .zone import _ZoneBase

if TYPE_CHECKING:
    from datetime import datetime as dt

    import voluptuous as vol

    from . import System
    from .schema import _DhwIdT, _EvoDictT, _EvoListT


class HotWaterDeprecated:  # pragma: no cover
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def zoneId(self) -> NoReturn:  # noqa: N802
        raise exc.DeprecationError(
            f"{self}: .zoneId is deprecated, use .dhw_id (or ._id)"
        )

    async def get_dhw_state(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .get_dhw_state() is deprecated, use Location.refresh_status()"
        )

    async def set_dhw_auto(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .set_dhw_auto() is deprecated, use .reset_mode()"
        )

    async def set_dhw_off(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .set_dhw_off() is deprecated, use .set_off()"
        )

    async def set_dhw_on(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise exc.DeprecationError(
            f"{self}: .set_dhw_on() is deprecated, use .set_on()"
        )


class HotWater(HotWaterDeprecated, _ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    STATUS_SCHEMA: Final = SCH_DHW_STATUS  # type: ignore[misc]
    TYPE: Final = SZ_DOMESTIC_HOT_WATER  # type: ignore[misc]

    SCH_SCHEDULE_GET: Final[vol.Schema] = SCH_GET_SCHEDULE_DHW  # type: ignore[misc]
    SCH_SCHEDULE_PUT: Final[vol.Schema] = SCH_PUT_SCHEDULE_DHW  # type: ignore[misc]

    def __init__(self, tcs: System, config: _EvoDictT, /) -> None:
        super().__init__(config[SZ_DHW_ID], tcs, config)

    @property
    def dhw_id(self) -> _DhwIdT:
        return self._id

    @property
    def dhw_state_capabilities_esponse(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_DHW_STATE_CAPABILITIES_RESPONSE]
        return ret

    @property
    def schedule_capabilities_response(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_SCHEDULE_CAPABILITIES_RESPONSE]
        return ret

    @property  # for convenience (is not a top-level config attribute)
    def allowed_modes(self) -> _EvoListT:
        ret: _EvoListT = self.dhw_state_capabilities_esponse[SZ_ALLOWED_MODES]
        return ret

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def state_status(self) -> _EvoDictT | None:
        return self._status.get(SZ_STATE_STATUS)

    @property  # status attr for convenience (new)
    def mode(self) -> str | None:
        if self.state_status is None:
            return None
        ret: str = self.state_status[SZ_MODE]
        return ret

    @property  # status attr for convenience (new)
    def state(self) -> str | None:
        if self.state_status is None:
            return None
        ret: str = self.state_status[SZ_STATE]
        return ret

    def _next_setpoint(self) -> tuple[dt, str] | None:  # WIP: for convenience (new)
        """Return the datetime and state of the next setpoint."""
        raise NotImplementedError

    async def _set_mode(self, mode: dict[str, str | None]) -> None:
        """Set the DHW mode (state)."""
        _ = await self._broker.put(f"{self.TYPE}/{self._id}/state", json=mode)

    async def reset_mode(self) -> None:
        """Cancel any override and allow the DHW to follow its schedule."""

        mode: dict[str, str | None] = {  # NOTE: SZ_STATE was previously ""
            SZ_MODE: ZoneMode.FOLLOW_SCHEDULE,
            SZ_STATE: None,
            SZ_UNTIL_TIME: None,
        }

        await self._set_mode(mode)

    async def set_on(self, /, *, until: dt | None = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        mode: dict[str, str | None]

        if until is None:
            mode = {
                SZ_MODE: ZoneMode.PERMANENT_OVERRIDE,
                SZ_STATE: DhwState.ON,
                SZ_UNTIL_TIME: None,
            }
        else:
            mode = {
                SZ_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                SZ_STATE: DhwState.ON,
                SZ_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def set_off(self, /, *, until: dt | None = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        mode: dict[str, str | None]

        if until is None:
            mode = {
                SZ_MODE: ZoneMode.PERMANENT_OVERRIDE,
                SZ_STATE: DhwState.OFF,
                SZ_UNTIL_TIME: None,
            }
        else:
            mode = {
                SZ_MODE: ZoneMode.TEMPORARY_OVERRIDE,
                SZ_STATE: DhwState.OFF,
                SZ_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)
