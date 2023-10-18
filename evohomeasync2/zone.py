#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of heatings zones."""

from __future__ import annotations

from datetime import datetime as dt
import json
import logging
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, URL_BASE
from .exceptions import InvalidSchedule
from .schema import SCH_DHW_STATUS, SCH_ZONE_STATUS
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SCHEDULE_CAPABILITIES,
    SZ_SETPOINT_CAPABILITIES,
    SZ_SETPOINT_STATUS,
    SZ_TEMPERATURE_STATUS,
    SZ_ZONE_ID,
    SZ_ZONE_TYPE,
)

if TYPE_CHECKING:
    from .controlsystem import ControlSystem
    from .typing import _ZoneIdT

_LOGGER = logging.getLogger(__name__)


MAPPING = [
    ("dailySchedules", "DailySchedules"),
    ("dayOfWeek", "DayOfWeek"),
    ("temperature", "TargetTemperature"),
    ("timeOfDay", "TimeOfDay"),
    ("switchpoints", "Switchpoints"),
    ("dhwState", "DhwState"),
]


class _ZoneBase:
    """Provide the base for temperatureZone / domesticHotWater Zones."""

    _id: str  # .zoneId or .dhwId
    _type: str  # "temperatureZone" or "domesticHotWater"

    def __init__(self, tcs: ControlSystem):
        self.tcs = tcs  # parent
        self.client = tcs.gateway.location.client
        self._client = tcs.gateway.location.client._client

        self._status = {}

    @property
    def zone_type(self) -> NoReturn:
        raise NotImplementedError("ZoneBase.zone_type is deprecated, use ._type")

    async def refresh_status(self) -> dict:
        """Update the dhw/zone with its latest status (also returns the status).

        It will be more efficient to call Location.refresh_status().
        """

        url = f"{self._type}/{self._id}/status"
        response = await self._client("GET", f"{URL_BASE}/{url}")
        if self._type == "temperatureZone":
            status = SCH_ZONE_STATUS(response)
        else:
            status = SCH_DHW_STATUS(response)

        self._update_state(status)
        return status

    def _update_state(self, state: dict) -> None:
        self._status = state

    # status attrs...
    @property
    def activeFaults(self) -> list:
        return self._status[SZ_ACTIVE_FAULTS]

    @property
    def temperatureStatus(self) -> dict:
        return self._status[SZ_TEMPERATURE_STATUS]

    async def schedule(self) -> NoReturn:
        raise NotImplementedError(
            "ZoneBase.schedule() is deprecrated, use .get_schedule()"
        )

    async def get_schedule(self) -> dict:
        """Get the schedule for this dhw/zone object."""

        _LOGGER.debug(f"Getting schedule of {self._id} ({self._type})...")

        url = f"{self._type}/{self._id}/schedule"
        response_json = await self._client("GET", f"{URL_BASE}/{url}")

        response_text = json.dumps(response_json)  # FIXME
        for from_val, to_val in MAPPING:  # an anachronism from evohome-client
            response_text = response_text.replace(from_val, to_val)

        result: dict = json.loads(response_text)
        # change the day name string to a number offset (0 = Monday)
        for day_of_week, schedule in enumerate(result["DailySchedules"]):
            schedule["DayOfWeek"] = day_of_week

        return result

    async def set_schedule(self, zone_schedule: str) -> None:
        """Set the schedule for this dhw/zone object."""

        _LOGGER.debug(f"Setting schedule of {self._id} ({self._type})...")

        try:
            json.loads(zone_schedule)

        except ValueError as exc:
            raise InvalidSchedule(f"zone_schedule must be valid JSON: {exc}")

        url = f"{self._type}/{self._id}/schedule"
        await self._client("PUT", f"{URL_BASE}/{url}", json=zone_schedule)


class Zone(_ZoneBase):
    """Provide the access to an individual zone."""

    _type = "temperatureZone"

    def __init__(self, tcs: ControlSystem, zone_config: dict) -> None:
        super().__init__(tcs)

        self._config: Final[dict] = zone_config
        assert self.zoneId, "Invalid config dict"

        self._id = self.zoneId

    # config attrs...
    @property
    def zoneId(self) -> _ZoneIdT:
        return self._config[SZ_ZONE_ID]

    @property
    def modelType(self) -> str:
        return self._config[SZ_MODEL_TYPE]

    @property
    def setpointCapabilities(self) -> dict:
        return self._config[SZ_SETPOINT_CAPABILITIES]

    @property
    def scheduleCapabilities(self) -> dict:
        return self._config[SZ_SCHEDULE_CAPABILITIES]

    @property
    def zoneType(self) -> str:
        return self._config[SZ_ZONE_TYPE]

    # status attrs...
    @property
    def name(self) -> str:
        return self._config.get(SZ_NAME) or self._config[SZ_NAME]

    @property
    def setpointStatus(self) -> dict:
        return self._status[SZ_SETPOINT_STATUS]

    async def _set_mode(self, heat_setpoint: dict) -> None:
        """TODO"""

        url = f"temperatureZone/{self.zoneId}/heatSetpoint"  # f"{_type}/{_id}/heatS..."
        await self._client("PUT", f"{URL_BASE}/{url}", json=heat_setpoint)

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

        await self._set_mode(mode)

    async def cancel_temp_override(self) -> None:
        """Cancel an override to the zone temperature."""

        mode = {
            "SetpointMode": "FollowSchedule",
            "HeatSetpointValue": 0.0,
            "TimeUntil": None,
        }

        await self._set_mode(mode)
