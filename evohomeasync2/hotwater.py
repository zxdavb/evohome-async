#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of the hot water zone."""

from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, URL_BASE
from .schema.const import (
    SZ_DHW_ID,
    SZ_DHW_STATE_CAPABILITIES_RESPONSE,
    SZ_DOMESTIC_HOT_WATER,
    SZ_SCHEDULE_CAPABILITIES_RESPONSE,
    SZ_STATE_STATUS,
)
from .zone import _ZoneBase


if TYPE_CHECKING:
    from .controlsystem import ControlSystem
    from .typing import _DhwIdT

# _LOGGER = logging.getLogger(__name__)


class HotWaterDeprecated:
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
    """Provide handling of the hot water zone."""

    _type = SZ_DOMESTIC_HOT_WATER

    def __init__(self, tcs: ControlSystem, dhw_config: dict) -> None:
        super().__init__(tcs)

        self._config: Final[dict] = dhw_config
        assert self.dhwId, "Invalid config dict"

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

        url = f"domesticHotWater/{self.dhwId}/state"  # f"{_type}/{_id}/state"
        await self._client("PUT", f"{URL_BASE}/{url}", json=state)

    async def set_on(self, /, *, until: None | dt = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        if until is None:
            mode = {"Mode": "PermanentOverride", "State": "On", "UntilTime": None}
        else:
            mode = {
                "Mode": "TemporaryOverride",
                "State": "On",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def set_off(self, /, *, until: None | dt = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        if until is None:
            mode = {"Mode": "PermanentOverride", "State": "Off", "UntilTime": None}
        else:
            mode = {
                "Mode": "TemporaryOverride",
                "State": "Off",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_mode(mode)

    async def set_auto(self) -> None:
        """Set the DHW to follow the schedule."""

        mode = {"Mode": "FollowSchedule", "State": "", "UntilTime": None}

        await self._set_mode(mode)
