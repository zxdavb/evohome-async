#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC temperature control systems."""

from __future__ import annotations

from datetime import datetime as dt
import json
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, SystemMode
from .hotwater import HotWater
from .schema import SCH_TCS_STATUS
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DHW,
    SZ_MODEL_TYPE,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TEMPERATURE_CONTROL_SYSTEM,
    SZ_ZONES,
)
from .schema.const import SYSTEM_MODES
from .zone import Zone


if TYPE_CHECKING:
    import logging

    from . import Broker, Gateway, Location
    from .schema import _DhwIdT, _EvoDictT, _EvoListT, _FilePathT, _SystemIdT, _ZoneIdT


class _ControlSystemDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

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


class ControlSystem(_ControlSystemDeprecated):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    STATUS_SCHEMA = SCH_TCS_STATUS
    _type = SZ_TEMPERATURE_CONTROL_SYSTEM

    def __init__(self, gateway: Gateway, config: _EvoDictT) -> None:
        self.gateway = gateway
        self.location: Location = gateway.location

        self._broker: Broker = gateway._broker
        self._logger: logging.Logger = gateway._logger

        self._status: _EvoDictT = {}
        self._config: Final[_EvoDictT] = {
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }

        assert self.systemId, "Invalid config dict"
        self._id = self.systemId

        self._zones: list[Zone] = []
        self.zones: dict[str, Zone] = {}  # zone by name! what to do if name changed?
        self.zones_by_id: dict[str, Zone] = {}
        self.hotwater: None | HotWater = None

        dhw_config: _EvoDictT
        zon_config: _EvoDictT

        for zon_config in config[SZ_ZONES]:
            zone = Zone(self, zon_config)

            self._zones.append(zone)
            self.zones[zone.name] = zone
            self.zones_by_id[zone.zoneId] = zone

        if dhw_config := config.get(SZ_DHW):  # type: ignore[assignment]
            self.hotwater = HotWater(self, dhw_config)

    def __str__(self) -> str:
        return f"{self._id} ({self._type})"

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

    def _update_status(self, tcs_status: _EvoDictT) -> None:
        self._status = tcs_status

    # status attrs...
    @property
    def activeFaults(self) -> None | _EvoListT:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def systemModeStatus(self) -> None | _EvoDictT:
        return self._status.get(SZ_SYSTEM_MODE_STATUS)

    async def _set_mode(self, system_mode: dict) -> None:
        _ = await self._broker.put(
            f"{self._type}/{self._id}/mode", json=system_mode  # schema=
        )  # except exceptions.FailedRequest

    async def set_mode(self, mode: SystemMode, /, *, until: None | dt = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        request: _EvoDictT

        if mode not in SYSTEM_MODES:
            raise ValueError(f"Invalid mode: {mode}")

        if until is None:
            request = {"SystemMode": mode, "TimeUntil": None, "Permanent": True}
        else:
            request = {
                "SystemMode": mode,
                "TimeUntil": until.strftime(API_STRFTIME),
                "Permanent": False,
            }

        await self._set_mode(request)

    async def reset_mode(self) -> None:
        """Reset the system into normal mode (and all zones to FollowSchedule mode)."""
        await self.set_status(SystemMode.AUTO_WITH_RESET)

    async def set_mode_auto(self) -> None:
        """Set the system into normal mode."""
        await self.set_status(SystemMode.AUTO)

    async def set_mode_custom(self, /, *, until: None | dt = None) -> None:
        """Set the system into custom mode."""
        await self.set_status(SystemMode.CUSTOM, until=until)

    async def set_mode_eco(self, /, *, until: None | dt = None) -> None:
        """Set the system into eco mode."""
        await self.set_status(SystemMode.AUTO_WITH_ECO, until=until)

    async def set_mode_away(self, /, *, until: None | dt = None) -> None:
        """Set the system into away mode."""
        await self.set_status(SystemMode.AWAY, until=until)

    async def set_mode_dayoff(self, /, *, until: None | dt = None) -> None:
        """Set the system into dayoff mode."""
        await self.set_status(SystemMode.DAY_OFF, until=until)

    async def set_mode_heatingoff(self, /, *, until: None | dt = None) -> None:
        """Set the system into heating off mode."""
        await self.set_status(SystemMode.HEATING_OFF, until=until)

    async def temperatures(self) -> _EvoListT:
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

            if (
                isinstance(dhw.temperatureStatus, dict)
                and dhw.temperatureStatus["isAvailable"]
            ):
                dhw_status["temp"] = dhw.temperatureStatus["temperature"]

            result.append(dhw_status)

        for zone in self._zones:
            zone_status = {
                "thermostat": "EMEA_ZONE",
                "id": zone.zoneId,
                "name": zone.name,
                "setpoint": None,
                "temp": None,
            }

            if isinstance(zone.setpointStatus, dict):
                zone_status["setpoint"] = zone.setpointStatus["targetHeatTemperature"]

            if (
                isinstance(zone.temperatureStatus, dict)
                and zone.temperatureStatus["isAvailable"]
            ):
                zone_status["temp"] = zone.temperatureStatus["temperature"]

            result.append(zone_status)

        return result

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the control system to the file."""

        self._logger.info(
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

        self._logger.info("Backup completed.")

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
                self._logger.warning(
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
                self._logger.warning(
                    f"Ignoring schedule of {id} ({name}): unknown name"
                    ", consider matching by id rather than by name"
                )
                return False

            return True

        self._logger.info(
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
            self._logger.warning("Restore completed, but with unmatched schedules.")
        else:
            self._logger.info("Restore completed.")
