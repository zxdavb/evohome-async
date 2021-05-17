#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provide handling of the hot water zone."""
from .zone import ZoneBase


class HotWater(ZoneBase):
    """Provide handling of the hot water zone."""

    def __init__(self, client, data):
        """Initialise the class."""
        super(HotWater, self).__init__(client)

        self.dhwId = None

        self.__dict__.update(data)

        self.name = ""
        self.zoneId = self.dhwId
        self.zone_type = "domesticHotWater"

    async def _set_dhw(self, data):  # TODO: deprecate
        return await self._set_dhw_state(data)

    async def _set_dhw_state(self, data):
        """Get the DHW state."""
        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1/domesticHotWater/%s/state"
            % self.dhwId
        )

        async with self.client._session.put(
            url, json=data, headers=headers
        ) as response:
            response.raise_for_status()

    async def set_dhw_on(self, until=None):
        """Set the DHW on until a given time, or permanently."""
        if until is None:
            data = {"Mode": "PermanentOverride", "State": "On", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "On",
                "UntilTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_dhw_state(data)

    async def set_dhw_off(self, until=None):
        """Set the DHW off until a given time, or permanently."""
        if until is None:
            data = {"Mode": "PermanentOverride", "State": "Off", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "Off",
                "UntilTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_dhw_state(data)

    async def set_dhw_auto(self):
        """Set the DHW to follow the schedule."""
        data = {"Mode": "FollowSchedule", "State": "", "UntilTime": None}

        await self._set_dhw_state(data)

    async def get_dhw_state(self):
        """Get the DHW state."""
        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1/domesticHotWater/%s/status?"
            % self.dhwId
        )

        async with self.client._session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
        return data
