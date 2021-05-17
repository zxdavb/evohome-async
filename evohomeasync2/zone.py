#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provide handling of individual zones."""
import json


class ZoneBase(object):
    """Provide the base for Zones."""

    def __init__(self, client):
        """Initialise the class."""
        self.client = client
        self.name = None
        self.zoneId = None
        self.zone_type = None

    async def schedule(self):
        """Get the schedule for the given zone."""
        url = "https://tccna.honeywell.com/WebAPI/emea/api/v1/%s/%s/schedule" % (
            self.zone_type,
            self.zoneId,
        )

        async with self.client._session.get(
            url, headers=await self.client._headers()
        ) as response:
            response.raise_for_status()
            response_data = await response.text()

        mapping = [
            ("dailySchedules", "DailySchedules"),
            ("dayOfWeek", "DayOfWeek"),
            ("temperature", "TargetTemperature"),
            ("timeOfDay", "TimeOfDay"),
            ("switchpoints", "Switchpoints"),
            ("dhwState", "DhwState"),
        ]

        for from_val, to_val in mapping:
            response_data = response_data.replace(from_val, to_val)

        data = json.loads(response_data)
        # change the day name string to a number offset (0 = Monday)
        for day_of_week, schedule in enumerate(data["DailySchedules"]):
            schedule["DayOfWeek"] = day_of_week
        return data

    async def set_schedule(self, zone_info):
        """Set the schedule for this zone."""
        # must only POST json, otherwise server API handler raises exceptions
        try:
            json.loads(zone_info)

        except ValueError as error:
            raise ValueError("zone_info must be valid JSON: ", error)

        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = "https://tccna.honeywell.com/WebAPI/emea/api/v1/%s/%s/schedule" % (
            self.zone_type,
            self.zoneId,
        )

        async with self.client._session.put(
            url, data=zone_info, headers=headers
        ) as response:
            response.raise_for_status()

            return await response.json()


class Zone(ZoneBase):
    """Provide the access to an individual zone."""

    def __init__(self, client, data):
        """Initialise the class."""
        super(Zone, self).__init__(client)

        self.__dict__.update(data)

        self.zone_type = "temperatureZone"

    async def set_temperature(self, temperature, until=None):
        """Set the temperature of the given zone."""
        if until is None:
            data = {
                "SetpointMode": "PermanentOverride",
                "HeatSetpointValue": temperature,
                "TimeUntil": None,
            }
        else:
            data = {
                "SetpointMode": "TemporaryOverride",
                "HeatSetpointValue": temperature,
                "TimeUntil": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_heat_setpoint(data)

    async def _set_heat_setpoint(self, data):
        headers = dict(await self.client._headers())
        headers["Content-Type"] = "application/json"

        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1"
            "/temperatureZone/%s/heatSetpoint" % self.zoneId
        )

        async with self.client._session.put(
            url, json=data, headers=headers
        ) as response:
            response.raise_for_status()

    async def cancel_temp_override(self):
        """Cancel an override to the zone temperature."""
        data = {
            "SetpointMode": "FollowSchedule",
            "HeatSetpointValue": 0.0,
            "TimeUntil": None,
        }

        await self._set_heat_setpoint(data)
