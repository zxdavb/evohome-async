#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of a TCC Temperature Control System."""
from __future__ import annotations

from datetime import datetime as dt
import json
import logging
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, URL_BASE
from .hotwater import HotWater
from .schema.const import (
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DHW,
    SZ_IS_PERMANENT,
    SZ_MODE,
    SZ_MODEL_TYPE,
    SZ_SYSTEM_ID,
    SZ_ZONES,
)
from .zone import Zone

if TYPE_CHECKING:
    from . import Gateway
    from .typing import _DhwIdT, _FilePathT, _ModeT, _SystemIdT, _ZoneIdT

_LOGGER = logging.getLogger(__name__)


class ControlSystemDeprecated:
    async def set_status(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status() is deprecrated, use .set_mode()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_normal() is deprecrated, use .set_mode_auto()"
        )

    async def set_status_reset(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_reset() is deprecrated, use .reset_mode()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_custom() is deprecrated, use .set_mode_custom()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_eco() is deprecrated, use .set_mode_eco()"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_away() is deprecrated, use .set_mode_away()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_dayoff() is deprecrated, use .set_mode_dayoff()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "ControlSystem.set_status_heatingoff() is deprecrated, use .set_mode_heatingoff()"
        )

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "TCS.zone_schedules_backup() is deprecated, use .backup_schedules()"
        )

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "TCS.zone_schedules_restore() is deprecated, use .restore_schedules()"
        )


class ControlSystem(ControlSystemDeprecated):
    """Instance of a gateway's Temperature Control System."""

    def __init__(self, gateway: Gateway, tcs_config: dict) -> None:
        self.gateway = gateway  # parent
        self.location = gateway.location
        self.client = gateway.location.client
        self._client = gateway.location.client._client

        self._status: dict = {}
        self._config: Final[dict] = {
            k: v for k, v in tcs_config.items() if k not in (SZ_DHW, SZ_ZONES)
        }
        assert self.systemId, "Invalid config dict"

        self._zones: list[Zone] = []
        self.zones: dict[str, Zone] = {}  # zone by name! what to do if name changed?
        self.zones_by_id: dict[str, Zone] = {}
        self.hotwater: None | HotWater = None

        for zone_config in tcs_config[SZ_ZONES]:
            zone = Zone(self, zone_config)

            self._zones.append(zone)
            self.zones[zone.name] = zone
            self.zones_by_id[zone.zoneId] = zone

        if dhw_config := tcs_config.get(SZ_DHW):
            self.hotwater = HotWater(self, dhw_config)

    # config attrs...
    @property
    def allowedSystemModes(self) -> str:
        return self._config[SZ_ALLOWED_SYSTEM_MODES]

    @property
    def modelType(self) -> str:
        return self._config[SZ_MODEL_TYPE]

    @property
    def systemId(self) -> _SystemIdT:
        return self._config[SZ_SYSTEM_ID]

    def _update_state(self, state: dict) -> None:
        self._status = state

    # status attrs...
    @property
    def isPermanent(self) -> bool:
        return self._status[SZ_IS_PERMANENT]

    @property
    def mode(self) -> _SystemIdT:
        return self._status[SZ_MODE]

    async def _set_mode(self, mode: dict) -> None:
        """TODO"""

        url = f"temperatureControlSystem/{self.systemId}/mode"
        await self._client("PUT", f"{URL_BASE}/{url}", json=mode)

    async def reset_mode(self) -> None:
        """Reset the system into normal mode (and all zones to FollowSchedule mode)."""
        await self.set_status("AutoWithReset")

    async def set_mode(self, mode: _ModeT, /, *, until: None | dt = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        if until is None:
            status = {"SystemMode": mode, "TimeUntil": None, "Permanent": True}
        else:
            status = {
                "SystemMode": mode,
                "TimeUntil": until.strftime(API_STRFTIME),
                "Permanent": False,
            }

        await self._set_mode(status)

    async def set_mode_auto(self) -> None:
        """Set the system into normal mode."""
        await self.set_status("Auto")

    async def set_mode_custom(self, /, *, until: None | dt = None) -> None:
        """Set the system into custom mode."""
        await self.set_status("Custom", until=until)

    async def set_mode_eco(self, /, *, until: None | dt = None) -> None:
        """Set the system into eco mode."""
        await self.set_status("AutoWithEco", until=until)

    async def set_mode_away(self, /, *, until: None | dt = None) -> None:
        """Set the system into away mode."""
        await self.set_status("Away", until=until)

    async def set_mode_dayoff(self, /, *, until: None | dt = None) -> None:
        """Set the system into dayoff mode."""
        await self.set_status("DayOff", until=until)

    async def set_mode_heatingoff(self, /, *, until: None | dt = None) -> None:
        """Set the system into heating off mode."""
        await self.set_status("HeatingOff", until=until)

    async def temperatures(self) -> list[dict]:
        """A convienience function to return the latest temperatures and setpoints."""

        await self.location.refresh_status()

        result = []

        if dhw := self.hotwater:
            dhw_status = {
                "thermostat": "DOMESTIC_HOT_WATER",
                "id": dhw.dhwId,
                "name": dhw.name,
                "temp": None,
            }

            if dhw.temperatureStatus["isAvailable"]:
                dhw_status["temp"] = dhw.temperatureStatus["temperature"]

            result.append(dhw_status)

        for zone in self._zones:
            zone_status = {
                "thermostat": "EMEA_ZONE",
                "id": zone.zoneId,
                "name": zone.name,
                "temp": None,
                "setpoint": zone.setpointStatus["targetHeatTemperature"],
            }

            if zone.temperatureStatus["isAvailable"]:
                zone_status["temp"] = zone.temperatureStatus["temperature"]

            result.append(zone_status)

        return result

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the control system to the file."""

        _LOGGER.info(
            f"Backing up schedules from {self.systemId} ({self.location.name})"
            f", to {filename}"
        )

        schedules = {}

        for zone in self._zones:
            schedule = await zone.get_schedule()
            schedules[zone.zoneId] = {"name": zone.name, "schedule": schedule}

        if self.hotwater:
            schedule = await self.hotwater.get_schedule()
            schedules[self.hotwater.dhwId] = {
                "name": self.hotwater.name,
                "schedule": schedule,
            }

        with open(filename, "w") as file_output:
            file_output.write(json.dumps(schedules, indent=4))

        _LOGGER.info("Backup completed.")

    async def restore_schedules(
        self, filename: _FilePathT, match_by_name: bool = False
    ) -> None:
        """Restore all schedules from the file to the TCS.

        The default is to match a schedule to its zone/dhw by id.
        """

        async def restore_by_id(id: _ZoneIdT | _DhwIdT, schedule: dict) -> bool:
            """Restore schedule by id and return False if there was no match."""

            name = schedule.get("name")

            if self.hotwater and self.hotwater.dhwId == id:
                await self.hotwater.set_schedule(json.dumps(schedule["schedule"]))

            elif zone := self.zones_by_id.get(id):
                await zone.set_schedule(json.dumps(schedule["schedule"]))

            else:
                _LOGGER.warning(
                    f"Ignoring schedule of {id} ({name}): unknown id"
                    ", consider matching by name rather than by id"
                )
                return False

            return True

        async def restore_by_name(id: _ZoneIdT | _DhwIdT, schedule: dict) -> bool:
            """Restore schedule by name and return False if there was no match."""

            name = schedule["name"]  # don't use .get()

            if self.hotwater and name == self.hotwater.name:
                await self.hotwater.set_schedule(json.dumps(schedule["schedule"]))

            elif zone := self.zones.get(name):
                await zone.set_schedule(json.dumps(schedule["schedule"]))

            else:
                _LOGGER.warning(
                    f"Ignoring schedule of {id} ({name}): unknown name"
                    ", consider matching by id rather than by name"
                )
                return False

            return True

        _LOGGER.info(
            f"Restoring schedules (matched by {'name' if match_by_name else 'id'}) to "
            f"{self.systemId} ({self.location.name}), from {filename}"
        )

        with open(filename, "r") as file_input:
            schedule_db = file_input.read()
            schedules: dict = json.loads(schedule_db)

        with_errors = False

        for id, schedule in schedules.items():
            assert isinstance(schedule, dict)  # mypy

            if match_by_name:
                matched = await restore_by_name(id, schedule)
            else:
                matched = await restore_by_id(id, schedule)

            with_errors = with_errors and not matched

        if with_errors or len(schedules) != len(self.zones) + 1 if self.hotwater else 0:
            _LOGGER.warning("Restore completed, but with unmatched schedules.")
        else:
            _LOGGER.info("Restore completed.")
