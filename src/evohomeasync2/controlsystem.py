#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC temperature control systems."""

# TODO: add provision for cooling
# TODO: add set_mode() for non-evohome modes (e.g. "Heat", "Off")

from __future__ import annotations

import json
from datetime import datetime as dt
from typing import TYPE_CHECKING, Final, NoReturn

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ID,
    SZ_NAME,
    SZ_SCHEDULE,
    SZ_SETPOINT,
    SZ_TEMP,
    SZ_THERMOSTAT,
    SystemMode,
)
from .hotwater import HotWater
from .schema import SCH_TCS_STATUS
from .schema.const import (
    SZ_ACTIVE_FAULTS,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_IS_AVAILABLE,
    SZ_MODE,
    SZ_MODEL_TYPE,
    SZ_PERMANENT,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TARGET_HEAT_TEMPERATURE,
    SZ_TEMPERATURE,
    SZ_TEMPERATURE_CONTROL_SYSTEM,
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONES,
)
from .zone import ActiveFaultsBase, Zone

if TYPE_CHECKING:
    import voluptuous as vol  # type: ignore[import-untyped]

    from . import Gateway, Location
    from .schema import (
        _DhwIdT,
        _EvoDictT,
        _EvoListT,
        _FilePathT,
        _ScheduleT,
        _SystemIdT,
        _ZoneIdT,
    )


class _ControlSystemDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def set_status_reset(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_reset() is deprecrated, use .reset_mode()"
        )

    async def set_status(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status() is deprecrated, use .set_mode()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_normal() is deprecrated, use .set_auto()"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_away() is deprecrated, use .set_away()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_custom() is deprecrated, use .set_custom()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_dayoff() is deprecrated, use .set_dayoff()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_eco() is deprecrated, use .set_eco()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_heatingoff() is deprecrated, use .set_heatingoff()"
        )

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .zone_schedules_backup() is deprecated, use .backup_schedules()"
        )

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .zone_schedules_restore() is deprecated, use .restore_schedules()"
        )


class ControlSystem(ActiveFaultsBase, _ControlSystemDeprecated):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_TCS_STATUS  # type: ignore[no-any-unimported]
    TYPE: Final = SZ_TEMPERATURE_CONTROL_SYSTEM  # type: ignore[misc]

    def __init__(self, gateway: Gateway, config: _EvoDictT) -> None:
        super().__init__(config[SZ_SYSTEM_ID], gateway._broker, gateway._logger)

        self.gateway = gateway
        self.location: Location = gateway.location

        self._config: Final[_EvoDictT] = {
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }
        self._status: _EvoDictT = {}

        self._zones: list[Zone] = []
        self.zones: dict[str, Zone] = {}  # zone by name! what to do if name changed?
        self.zones_by_id: dict[str, Zone] = {}
        self.hotwater: None | HotWater = None

        zon_config: _EvoDictT
        for zon_config in config[SZ_ZONES]:
            try:
                zone = Zone(self, zon_config)
            except exc.InvalidSchema as err:
                self._logger.warning(
                    f"{self}: zone_id='{zon_config[SZ_ZONE_ID]}' ignored: {err}"
                )
            else:
                self._zones.append(zone)
                self.zones[zone.name] = zone
                self.zones_by_id[zone.zoneId] = zone

        dhw_config: _EvoDictT
        if dhw_config := config.get(SZ_DHW):  # type: ignore[assignment]
            self.hotwater = HotWater(self, dhw_config)

    @property
    def systemId(self) -> _SystemIdT:
        return self._id

    @property
    def allowedSystemModes(self) -> _EvoListT:
        ret: _EvoListT = self._config[SZ_ALLOWED_SYSTEM_MODES]
        return ret

    @property
    def modelType(self) -> str:
        ret: str = self._config[SZ_MODEL_TYPE]
        return ret

    async def _refresh_status(self) -> None:
        await self.location.refresh_status()

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

        if dhw_status := self._status.get(SZ_DHW):
            if self.hotwater and self.hotwater._id == dhw_status[SZ_DHW_ID]:
                self.hotwater._update_status(dhw_status)

            else:
                self._logger.warning(
                    f"{self}: dhw_id='{dhw_status[SZ_DHW_ID]}' not known"
                    ", (has the system configuration been changed?)"
                )

        for zon_status in self._status[SZ_ZONES]:
            if zone := self.zones_by_id.get(zon_status[SZ_ZONE_ID]):
                zone._update_status(zon_status)

            else:
                self._logger.warning(
                    f"{self}: zone_id='{zon_status[SZ_ZONE_ID]}' not known"
                    ", (has the system configuration been changed?)"
                )

    @property
    def activeFaults(self) -> _EvoListT | None:
        return self._status.get(SZ_ACTIVE_FAULTS)

    @property
    def systemModeStatus(self) -> _EvoDictT | None:
        return self._status.get(SZ_SYSTEM_MODE_STATUS)

    @property  # status attr for convenience (new)
    def system_mode(self) -> str | None:
        if self.systemModeStatus is None:
            return None
        ret: str = self.systemModeStatus[SZ_MODE]
        return ret

    async def _set_mode(self, mode: dict[str, str | bool]) -> None:
        """Set the TCS mode."""  # {'mode': 'Auto', 'isPermanent': True}
        _ = await self._broker.put(f"{self.TYPE}/{self._id}/mode", json=mode)

    async def reset_mode(self) -> None:
        """Set the TCS to auto mode (and DHW/all zones to FollowSchedule mode)."""
        await self.set_status(SystemMode.AUTO_WITH_RESET)

    async def set_mode(self, mode: SystemMode, /, *, until: dt | None = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        request: _EvoDictT

        if mode not in [m[SZ_SYSTEM_MODE] for m in self.allowedSystemModes]:
            raise exc.InvalidParameter(f"{self}: Unsupported/unknown mode: {mode}")

        if until is None:
            request = {
                SZ_SYSTEM_MODE: mode,
                SZ_PERMANENT: True,
                # SZ_TIME_UNTIL: None,
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

    async def _get_schedules(self) -> _ScheduleT:
        """Get the schedule for every DHW/zone of this TCS."""

        async def get_schedule(child: HotWater | Zone) -> _ScheduleT:
            try:
                return await child.get_schedule()
            except exc.InvalidSchedule:
                self._logger.warning(
                    f"Ignoring schedule of {child._id} ({child.name}): missing/invalid"
                )
            return {}

        schedules = {}

        for zone in self._zones:
            schedules[zone.zoneId] = {
                SZ_NAME: zone.name,
                SZ_SCHEDULE: await get_schedule(zone),
            }

        if self.hotwater:
            schedules[self.hotwater.dhwId] = {
                SZ_NAME: self.hotwater.name,
                SZ_SCHEDULE: await get_schedule(self.hotwater),
            }

        return schedules

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the control system to the file."""

        self._logger.info(
            f"Schedules: Backing up"
            f" from {self.systemId} ({self.location.name}), to {filename}"
        )

        schedules = await self._get_schedules()

        with open(filename, "w") as file_output:
            file_output.write(json.dumps(schedules, indent=4))

        self._logger.info("Schedules: Backup completed")

    async def _set_schedules(
        self, schedules: _ScheduleT, match_by_name: bool = False
    ) -> bool:
        """Set the schedule for every DHW/zone of this TCS (return True if success)."""

        async def restore_by_id(id: _ZoneIdT | _DhwIdT, schedule: _ScheduleT) -> bool:
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

        async def restore_by_name(id: _ZoneIdT | _DhwIdT, schedule: _ScheduleT) -> bool:
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

        with_errors = False

        for id, schedule in schedules.items():
            assert isinstance(schedule, dict)  # mypy

            if match_by_name:
                matched = await restore_by_name(id, schedule)
            else:
                matched = await restore_by_id(id, schedule)

            with_errors = with_errors and not matched

        success = not with_errors or len(schedules) == len(self.zones) + (
            1 if self.hotwater else 0
        )

        if not success:
            self._logger.warning(
                f"Schedules: Some entities not restored:"
                f" not matched by {'name' if match_by_name else 'id'}"
            )

        return success

    async def restore_schedules(
        self, filename: _FilePathT, match_by_name: bool = False
    ) -> None:
        """Restore all schedules from the file to the TCS.

        The default is to match a schedule to its zone/dhw by id.
        """

        self._logger.info(
            f"Schedules: Restoring (matched by {'name' if match_by_name else 'id'})"
            f" to {self.systemId} ({self.location.name}), from {filename}"
        )

        with open(filename) as file_input:
            schedule_db = file_input.read()
            schedules: _ScheduleT = json.loads(schedule_db)

        await self._set_schedules(schedules)

        self._logger.info("Schedules: Restore completed")
