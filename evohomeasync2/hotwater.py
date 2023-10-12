#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provide handling of the hot water zone."""
from datetime import datetime as dt
from typing import TYPE_CHECKING

from .const import API_STRFTIME, URL_BASE
from .zone import ZoneBase

if TYPE_CHECKING:
    from . import EvohomeClient
    from .typing import _DhwIdT


class HotWater(ZoneBase):
    """Provide handling of the hot water zone."""

    dhwId: _DhwIdT = ""
    temperatureStatus: dict  # TODO

    zone_type = "domesticHotWater"  # TODO: was at end of init, OK here?

    def __init__(self, client: EvohomeClient, config: dict) -> None:
        super().__init__(client, config)
        assert self.dhwId, "Invalid config dict"

        self.zoneId = self.dhwId

    async def _set_dhw(self, data: dict) -> None:  # TODO: deprecate
        return await self._set_dhw_state(data)

    async def _set_dhw_state(self, data: dict) -> None:
        """Set the DHW state."""

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = f"{URL_BASE}/domesticHotWater/{self.dhwId}/state"

        async with self.client._session.put(
            url, json=data, headers=headers
        ) as response:
            response.raise_for_status()

    async def set_dhw_on(self, /, *, until: None | dt = None) -> None:
        """Set the DHW on until a given time, or permanently."""

        if until is None:
            data = {"Mode": "PermanentOverride", "State": "On", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "On",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_dhw_state(data)

    async def set_dhw_off(self, /, *, until: None | dt = None) -> None:
        """Set the DHW off until a given time, or permanently."""

        if until is None:
            data = {"Mode": "PermanentOverride", "State": "Off", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "Off",
                "UntilTime": until.strftime(API_STRFTIME),
            }

        await self._set_dhw_state(data)

    async def set_dhw_auto(self) -> None:
        """Set the DHW to follow the schedule."""

        data = {"Mode": "FollowSchedule", "State": "", "UntilTime": None}

        await self._set_dhw_state(data)

    async def get_dhw_state(self) -> dict:
        """Get the DHW state."""

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = f"{URL_BASE}/domesticHotWater/{self.dhwId}/status?"

        async with self.client._session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
        return data
