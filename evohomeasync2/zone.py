#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of individual zones."""
from __future__ import annotations

from datetime import datetime as dt
import json
from typing import TYPE_CHECKING

from . import exceptions
from .const import API_STRFTIME, URL_BASE

if TYPE_CHECKING:
    from . import EvohomeClient
    from .typing import _ZoneIdT


MAPPING = [
    ("dailySchedules", "DailySchedules"),
    ("dayOfWeek", "DayOfWeek"),
    ("temperature", "TargetTemperature"),
    ("timeOfDay", "TimeOfDay"),
    ("switchpoints", "Switchpoints"),
    ("dhwState", "DhwState"),
]


class ZoneBase:
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    zoneId: _ZoneIdT
    name: str = ""  # TODO: check if is OK here
    temperatureStatus: dict  # TODO

    zone_type: str

    def __init__(self, client: EvohomeClient, config: dict):
        self.client = client

        self.__dict__.update(config)

    async def schedule(self) -> dict:
        """Get the schedule for the given zone."""

        async with self.client._session.get(
            f"{URL_BASE}/{self.zone_type}/{self.zoneId}/schedule",
            headers=await self.client._headers(),
        ) as response:
            response.raise_for_status()

            response_text = await response.text()

        for from_val, to_val in MAPPING:
            response_text = response_text.replace(from_val, to_val)

        result: dict = json.loads(response_text)
        # change the day name string to a number offset (0 = Monday)
        for day_of_week, schedule in enumerate(result["DailySchedules"]):
            schedule["DayOfWeek"] = day_of_week

        return result

    async def set_schedule(self, zone_schedule: str) -> dict:
        """Set the schedule for this zone."""
        # must only POST json, otherwise server API handler raises exceptions

        try:
            json.loads(zone_schedule)

        except ValueError as exc:
            raise exceptions.InvalidSchedule(f"zone_info must be valid JSON: {exc}")

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        async with self.client._session.put(
            f"{URL_BASE}/{self.zone_type}/{self.zoneId}/schedule",
            data=zone_schedule,
            headers=headers,
        ) as response:
            response.raise_for_status()

            return await response.json()


class Zone(ZoneBase):
    """Provide the access to an individual zone."""

    setpointStatus: dict  # TODO
    zone_type = "temperatureZone"  # TODO: was at end of init, OK here?

    def __init__(self, client: EvohomeClient, config: dict) -> None:
        super().__init__(client, config)
        assert self.zoneId, "Invalid config dict"

    async def _set_heat_setpoint(self, heat_setpoint: dict) -> None:
        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = f"temperatureZone/{self.zoneId}/heatSetpoint"

        async with self.client._session.put(
            f"{URL_BASE}/{url}", json=heat_setpoint, headers=headers
        ) as response:
            response.raise_for_status()

    async def set_temperature(
        self, temperature: float, /, *, until: None | dt = None
    ) -> None:
        """Set the temperature of the given zone."""
        if until is None:
            mode = {
                "SetpointMode": "PermanentOverride",
                "HeatSetpointValue": temperature,
                "TimeUntil": None,
            }
        else:
            mode = {
                "SetpointMode": "TemporaryOverride",
                "HeatSetpointValue": temperature,
                "TimeUntil": until.strftime(API_STRFTIME),
            }

        await self._set_heat_setpoint(mode)

    async def cancel_temp_override(self) -> None:
        """Cancel an override to the zone temperature."""

        mode = {
            "SetpointMode": "FollowSchedule",
            "HeatSetpointValue": 0.0,
            "TimeUntil": None,
        }

        await self._set_heat_setpoint(mode)
