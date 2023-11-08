#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC temperature control systems."""

# TODO: add provision for cooling
# TODO: add set_mode() for non-evohome modes (e.g. "Heat", "Off")

from __future__ import annotations

from datetime import datetime as dt
import json
from typing import TYPE_CHECKING, Final, NoReturn

from .const import API_STRFTIME, SystemMode
from .exceptions import DeprecationError, InvalidParameter, InvalidSchema
from .hotwater import HotWater
from .schema import SCH_TCS_STATUS
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DHW,
    SZ_IS_AVAILABLE,
    SZ_MODEL_TYPE,
    SZ_PERMANENT,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_CONTROL_SYSTEM,
    SZ_TIME_UNTIL,
    SZ_ZONES,
)
from .zone import Zone


if TYPE_CHECKING:
    import logging

    from . import Broker, Gateway, Location
    from .schema import _DhwIdT, _EvoDictT, _EvoListT, _FilePathT, _SystemIdT, _ZoneIdT


# used by temperatures() and *_schedules()...
SZ_ID = "id"
SZ_NAME = "name"
SZ_TEMP = "temp"
SZ_THERMOSTAT = "thermostat"
SZ_SCHEDULE = "schedule"
SZ_SETPOINT = "setpoint"


class _ControlSystemDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def set_status_reset(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_reset() is deprecrated, use .reset_mode()"
        )

    async def set_status(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status() is deprecrated, use .set_mode()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_normal() is deprecrated, use .set_auto()"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_away() is deprecrated, use .set_away()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_custom() is deprecrated, use .set_custom()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_dayoff() is deprecrated, use .set_dayoff()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_eco() is deprecrated, use .set_eco()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "ControlSystem.set_status_heatingoff() is deprecrated, use .set_heatingoff()"
        )

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "TCS.zone_schedules_backup() is deprecated, use .backup_schedules()"
        )

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "TCS.zone_schedules_restore() is deprecated, use .restore_schedules()"
        )


class ControlSystem(_ControlSystemDeprecated):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    STATUS_SCHEMA: Final = SCH_TCS_STATUS
    TYPE: Final[str] = SZ_TEMPERATURE_CONTROL_SYSTEM

    def __init__(self, gateway: Gateway, config: _EvoDictT) -> None:
        self.gateway = gateway
        self.location: Location = gateway.location

        self._broker: Broker = gateway._broker
        self._logger: logging.Logger = gateway._logger

        self._status: _EvoDictT = {}
        self._config: Final[_EvoDictT] = {
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }

        try:
            assert self.systemId, "Invalid config dict"
        except AssertionError as exc:
            raise InvalidSchema(str(exc))
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
        return f"{self._id} ({self.TYPE})"

    @property
    def allowedSystemModes(self) -> _EvoListT:
        return self._config[SZ_ALLOWED_SYSTEM_MODES]

    @property
    def modelType(self) -> str:
        return self._config[SZ_MODEL_TYPE]

    @property
    def systemId(self) -> _SystemIdT:
        return self._config[SZ_SYSTEM_ID]

    async def _refresh_status(self) -> None:
        await self.location.refresh_status()

    def _update_status(self, tcs_status: _EvoDictT) -> None:
        self._status = tcs_status

    @property
    def activeFaults(self) -> _EvoListT | None:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def systemModeStatus(self) -> _EvoDictT | None:
        return self._status.get(SZ_SYSTEM_MODE_STATUS)

    @property  # status attr for convenience (new)
    def system_mode(self) -> str | None:
        return self.systemModeStatus[SZ_SYSTEM_MODE] if self.systemModeStatus else None

    async def _set_mode(self, mode: dict) -> None:
        """Set the TCS mode."""  # {'mode': 'Auto', 'isPermanent': True}
        _ = await self._broker.put(f"{self.TYPE}/{self._id}/mode", json=mode)

    async def reset_mode(self) -> None:
        """Set the TCS to auto mode (and DHW/all zones to FollowSchedule mode)."""
        await self.set_status(SystemMode.AUTO_WITH_RESET)

    async def set_mode(self, mode: SystemMode, /, *, until: dt | None = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        request: _EvoDictT

        if mode not in [m[SZ_SYSTEM_MODE] for m in self.allowedSystemModes]:
            raise InvalidParameter(f"Unsupported/unknown mode: {mode}")

        if until is None:
            request = {
                SZ_SYSTEM_MODE: mode,
                SZ_PERMANENT: True,
                SZ_TIME_UNTIL: None,
            }
        else:
            request = {
                SZ_SYSTEM_MODE: mode,
                SZ_PERMANENT: False,
                SZ_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_mode(request)

    async def set_auto(self) -> None:
        """Set the system into normal mode."""
        await self.set_status(SystemMode.AUTO)

    async def set_away(self, /, *, until: dt | None = None) -> None:
        """Set the system into away mode."""
        await self.set_status(SystemMode.AWAY, until=until)

    async def set_custom(self, /, *, until: dt | None = None) -> None:
        """Set the system into custom mode."""
        await self.set_status(SystemMode.CUSTOM, until=until)

    async def set_dayoff(self, /, *, until: dt | None = None) -> None:
        """Set the system into dayoff mode."""
        await self.set_status(SystemMode.DAY_OFF, until=until)

    async def set_eco(self, /, *, until: dt | None = None) -> None:
        """Set the system into eco mode."""
        await self.set_status(SystemMode.AUTO_WITH_ECO, until=until)

    async def set_heatingoff(self, /, *, until: dt | None = None) -> None:
        """Set the system into heating off mode."""
        await self.set_status(SystemMode.HEATING_OFF, until=until)

    async def temperatures(self) -> _EvoListT:
        """A convienience function to return the latest temperatures and setpoints."""

        await self.location.refresh_status()

        result = []

        if dhw := self.hotwater:
            dhw_status = {
                SZ_THERMOSTAT: "DOMESTIC_HOT_WATER",
                SZ_ID: dhw.dhwId,
                SZ_NAME: dhw.name,
                SZ_TEMP: None,
            }

            if (
                isinstance(dhw.temperatureStatus, dict)
                and dhw.temperatureStatus[SZ_IS_AVAILABLE]
            ):
                dhw_status[SZ_TEMP] = dhw.temperatureStatus[SZ_TEMPERATURE]

            result.append(dhw_status)

        for zone in self._zones:
            zone_status = {
                SZ_THERMOSTAT: "EMEA_ZONE",
                SZ_ID: zone.zoneId,
                SZ_NAME: zone.name,
                SZ_SETPOINT: None,
                SZ_TEMP: None,
            }

            if isinstance(zone.setpointStatus, dict):
                zone_status[SZ_SETPOINT] = zone.setpointStatus[
                    SZ_TARGET_HEAT_TEMPERATURE
                ]

            if (
                isinstance(zone.temperatureStatus, dict)
                and zone.temperatureStatus[SZ_IS_AVAILABLE]
            ):
                zone_status[SZ_TEMP] = zone.temperatureStatus[SZ_TEMPERATURE]

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
            schedules[zone.zoneId] = {
                SZ_NAME: zone.name,
                SZ_SCHEDULE: schedule,
            }

        if self.hotwater:
            schedule = await self.hotwater.get_schedule()
            schedules[self.hotwater.dhwId] = {
                SZ_NAME: self.hotwater.name,
                SZ_SCHEDULE: schedule,
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

            name = schedule.get(SZ_NAME)

            if self.hotwater and self.hotwater.dhwId == id:
                await self.hotwater.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

            elif zone := self.zones_by_id.get(id):
                await zone.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

            else:
                self._logger.warning(
                    f"Ignoring schedule of {id} ({name}): unknown id"
                    ", consider matching by name rather than by id"
                )
                return False

            return True

        async def restore_by_name(id: _ZoneIdT | _DhwIdT, schedule: dict) -> bool:
            """Restore schedule by name and return False if there was no match."""

            name = schedule[SZ_NAME]  # don't use .get()

            if self.hotwater and name == self.hotwater.name:
                await self.hotwater.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

            elif zone := self.zones.get(name):
                await zone.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

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
