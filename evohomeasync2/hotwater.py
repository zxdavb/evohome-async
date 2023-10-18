#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of the hot water zone."""
from __future__ import annotations

from datetime import datetime as dt
import logging
from typing import TYPE_CHECKING, NoReturn

from .const import API_STRFTIME, URL_BASE
from .zone import ZoneBase

if TYPE_CHECKING:
    from .controlsystem import ControlSystem
    from .typing import _DhwIdT


_LOGGER = logging.getLogger(__name__)


class HotWater(ZoneBase):
    """Provide handling of the hot water zone."""

    dhwId: _DhwIdT

    temperatureStatus: dict  # TODO

    _type = "domesticHotWater"

    def __init__(self, tcs: ControlSystem, config: dict) -> None:
        super().__init__(tcs, config)

        self.__dict__.update(config)
        assert self.dhwId, "Invalid config dict"

        self._id = self.dhwId

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def zoneId(self) -> NoReturn:
        raise NotImplementedError("HotWater.zoneId is deprecated, use .dhwId (or ._id)")

    async def _set_dhw_state(self, state: dict) -> None:
        """Set the DHW state."""

        url = f"domesticHotWater/{self.dhwId}/state"  # f"{_type}/{_id}/state"
        await self._client("PUT", f"{URL_BASE}/{url}", json=state)

    async def set_dhw_on(self, /, *, until: None | dt = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        if until is None:
            mode = {"Mode": "PermanentOverride", "State": "On", "UntilTime": None}
        else:
            mode = {
                "Mode": "TemporaryOverride",
                "State": "On",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_dhw_state(mode)

    async def set_dhw_off(self, /, *, until: None | dt = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        if until is None:
            mode = {"Mode": "PermanentOverride", "State": "Off", "UntilTime": None}
        else:
            mode = {
                "Mode": "TemporaryOverride",
                "State": "Off",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_dhw_state(mode)

    async def set_dhw_auto(self) -> None:
        """Set the DHW to follow the schedule."""

        mode = {"Mode": "FollowSchedule", "State": "", "UntilTime": None}

        await self._set_dhw_state(mode)

    async def get_dhw_state(self) -> dict:
        """Get the DHW state."""

        url = f"domesticHotWater/{self.dhwId}/status?"
        response = await self._client("GET", f"{URL_BASE}/{url}")
        state: dict = dict(response)  # type: ignore[arg-type]  # TODO: use SCH_DHW_STATUS

        return state
