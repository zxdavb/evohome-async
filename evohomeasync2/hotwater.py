#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of the hot water zone."""
from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING

from .const import API_STRFTIME, URL_BASE
from .zone import ZoneBase

if TYPE_CHECKING:
    from . import EvohomeClient
    from .typing import _DhwIdT


class HotWater(ZoneBase):
    """Provide handling of the hot water zone."""

    dhwId: _DhwIdT

    temperatureStatus: dict  # TODO

    _type = "domesticHotWater"

    def __init__(self, client: EvohomeClient, config: dict) -> None:
        super().__init__(client, config)
        assert self.dhwId, "Invalid config dict"

        self._id = self.dhwId

    async def _set_dhw_state(self, state: dict) -> None:
        """Set the DHW state."""

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = f"domesticHotWater/{self.dhwId}/state"

        async with self.client._session.put(
            f"{URL_BASE}/{url}", json=state, headers=headers
        ) as response:
            response.raise_for_status()

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

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = f"domesticHotWater/{self.dhwId}/status?"

        async with self.client._session.get(
            f"{URL_BASE}/{url}", headers=headers, raise_for_status=True
        ) as response:
            return await response.json()
