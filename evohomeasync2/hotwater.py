#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC DHW zones."""

from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME
from .exceptions import InvalidSchema
from .schema import SCH_DHW_STATUS
from .schema.const import (
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_DOMESTIC_HOT_WATER,
    SZ_FOLLOW_SCHEDULE,
    SZ_MODE,
    SZ_OFF,
    SZ_ON,
    SZ_PERMANENT_OVERRIDE,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_STATE,
    SZ_STATE_STATUS,
    SZ_TEMPORARY_OVERRIDE,
    SZ_UNTIL_TIME,
)
from .schema.schedule import SCH_GET_SCHEDULE_DHW, SCH_PUT_SCHEDULE_DHW
from .zone import _ZoneBase


if TYPE_CHECKING:
    from . import ControlSystem
    from .schema import _DhwIdT, _EvoDictT


class HotWaterDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def zoneId(self) -> NoReturn:
        raise NotImplementedError("HotWater.zoneId is deprecated, use .dhwId (or ._id)")

    async def get_dhw_state(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "HotWater.get_dhw_state() is deprecated, use .update_status()"
        )

    async def set_dhw_on(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError("HotWater.set_dhw_on() is deprecated, use .set_on()")

    async def set_dhw_off(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "HotWater.set_dhw_off() is deprecated, use .set_off()"
        )

    async def set_dhw_auto(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "HotWater.set_dhw_auto() is deprecated, use .set_auto()"
        )


class HotWater(HotWaterDeprecated, _ZoneBase):
    """Instance of a TCS's DHW zone (domesticHotWater)."""

    STATUS_SCHEMA = SCH_DHW_STATUS
    TYPE: Final[str] = SZ_DOMESTIC_HOT_WATER  # type: ignore[misc]

    SCH_SCHEDULE_GET = SCH_GET_SCHEDULE_DHW
    SCH_SCHEDULE_PUT = SCH_PUT_SCHEDULE_DHW

    def __init__(self, tcs: ControlSystem, config: _EvoDictT) -> None:
        super().__init__(tcs)

        self._config: Final[_EvoDictT] = config

        try:
            assert self.dhwId, "Invalid config dict"
        except AssertionError as exc:
            raise InvalidSchema(str(exc))
        self._id = self.dhwId

    # config attrs...
    @property
    def dhwId(self) -> _DhwIdT:
        return self._config[SZ_DHW_ID]

    @property
    def dhwStateCapabilitiesResponse(self) -> dict:
        return self._config[SZ_DHW_STATE_CAPABILITIES_RESPONSE]

    @property
    def scheduleCapabilitiesResponse(self) -> dict:
        return self._config[SZ_SCHEDULE_CAPABILITIES_RESPONSE]

    # status attrs...
    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def stateStatus(self) -> None | dict:
        return self._status.get(SZ_STATE_STATUS)

    async def _set_mode(self, state: dict) -> None:
        """Set the DHW state."""
        _ = await self._broker.put(f"{self.TYPE}/{self._id}/state", json=state)

    # TODO: can we use camelCase strings?
    async def set_on(self, /, *, until: None | dt = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        if until is None:
            mode = {
                SZ_MODE: SZ_PERMANENT_OVERRIDE,
                SZ_STATE: SZ_ON,
                SZ_UNTIL_TIME: None,
            }
        else:
            mode = {
                SZ_MODE: SZ_TEMPORARY_OVERRIDE,
                SZ_STATE: SZ_ON,
                SZ_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def set_off(self, /, *, until: None | dt = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        if until is None:
            mode = {
                SZ_MODE: SZ_PERMANENT_OVERRIDE,
                SZ_STATE: SZ_OFF,
                SZ_UNTIL_TIME: None,
            }
        else:
            mode = {
                SZ_MODE: SZ_TEMPORARY_OVERRIDE,
                SZ_STATE: SZ_OFF,
                SZ_UNTIL_TIME: until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def set_auto(self) -> None:
        """Set the DHW to follow the schedule."""

        # NOTE: SZ_STATE was ""
        mode = {SZ_MODE: SZ_FOLLOW_SCHEDULE, SZ_STATE: None, SZ_UNTIL_TIME: None}

        await self._set_mode(mode)
