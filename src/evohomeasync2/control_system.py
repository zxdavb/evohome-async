#!/usr/bin/env python3
"""Provides handling of TCC temperature control systems."""

# TODO: add provision for cooling
# TODO: add set_mode() for non-evohome modes (e.g. "Heat", "Off")

from __future__ import annotations

import json
from datetime import datetime as dt
from typing import TYPE_CHECKING, Final

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_ID,  # remove?
    SZ_MODE,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SCHEDULE,
    SZ_SETPOINT,  # remove?
    SZ_STATE,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TEMPERATURE,  # remove?
    SZ_THERMOSTAT,  # remove?
    SZ_ZONE_ID,
    SZ_ZONES,
    SystemMode,
)
from .hotwater import HotWater
from .schema import SCH_TCS_STATUS
from .schema.const import (
    S2_PERMANENT,
    S2_SYSTEM_MODE,
    S2_TIME_UNTIL,
    EntityType,
    TcsModelType,
)
from .zone import ActiveFaultsBase, Zone

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Gateway, Location
    from .schema import _EvoDictT, _ScheduleT


class ControlSystem(ActiveFaultsBase):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_TCS_STATUS
    _TYPE: Final = EntityType.TCS  # type: ignore[misc]

    def __init__(self, gateway: Gateway, config: _EvoDictT) -> None:
        super().__init__(
            config[SZ_SYSTEM_ID],
            gateway._broker,
            gateway._logger,
        )

        self.gateway = gateway  # parent
        self.location: Location = gateway.location

        self._config: Final[_EvoDictT] = {  # type: ignore[misc]
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }
        self._status: _EvoDictT = {}

        # children
        self.zones: list[Zone] = []
        self.zones_by_id: dict[str, Zone] = {}

        self.hotwater: HotWater | None = None

        zon_config: _EvoDictT
        for zon_config in config[SZ_ZONES]:
            try:
                zone = Zone(self, zon_config)
            except exc.InvalidSchemaError as err:
                self._logger.warning(
                    f"{self}: zone_id='{zon_config[SZ_ZONE_ID]}' ignored: {err}"
                )
            else:
                self.zones.append(zone)
                self.zones_by_name[zone.name] = zone
                self.zones_by_id[zone.id] = zone

        dhw_config: _EvoDictT
        if dhw_config := config.get(SZ_DHW):  # type: ignore[assignment]
            self.hotwater = HotWater(self, dhw_config)

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

        for zon_status in self._status[SZ_ZONES]:
            if zone := self.zones_by_id.get(zon_status[SZ_ZONE_ID]):
                zone._update_status(zon_status)

            else:
                self._logger.warning(
                    f"{self}: zone_id='{zon_status[SZ_ZONE_ID]}' not known"
                    ", (has the system configuration been changed?)"
                )

        if dhw_status := self._status.get(SZ_DHW):
            if self.hotwater and self.hotwater.id == dhw_status[SZ_DHW_ID]:
                self.hotwater._update_status(dhw_status)

            else:
                self._logger.warning(
                    f"{self}: dhw_id='{dhw_status[SZ_DHW_ID]}' not known"
                    ", (has the system configuration been changed?)"
                )

    @property
    def allowed_system_modes(self) -> list[_EvoDictT]:
        """
        "allowedSystemModes": [
            {"systemMode": "HeatingOff",    "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "Auto",          "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "AutoWithReset", "canBePermanent": true, "canBeTemporary": false},
            {"systemMode": "AutoWithEco",   "canBePermanent": true, "canBeTemporary": true, "maxDuration":  "1.00:00:00", "timingResolution":   "01:00:00", "timingMode": "Duration"},
            {"systemMode": "Away",          "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"},
            {"systemMode": "DayOff",        "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"},
            {"systemMode": "Custom",        "canBePermanent": true, "canBeTemporary": true, "maxDuration": "99.00:00:00", "timingResolution": "1.00:00:00", "timingMode": "Period"}
        ]
        """

        ret: list[_EvoDictT] = self._config[SZ_ALLOWED_SYSTEM_MODES]
        return ret

    @property  # a convenience attr
    def mode(self) -> SystemMode | None:
        if self.system_mode_status is None:
            return None
        ret: SystemMode = self.system_mode_status[SZ_MODE]
        return ret

    @property  # a convenience attr
    def modes(self) -> tuple[SystemMode]:
        ret = tuple(d[SZ_SYSTEM_MODE] for d in self.allowed_system_modes)
        return ret

    @property
    def model(self) -> TcsModelType:
        ret: TcsModelType = self._config[SZ_MODEL_TYPE]
        return ret

    @property
    def system_mode_status(self) -> _EvoDictT | None:
        """
        "systemModeStatus": {
            "mode": "AutoWithEco",
            "isPermanent": true
        }
        """

        ret: _EvoDictT | None = self._status.get(SZ_SYSTEM_MODE_STATUS)
        return ret

    @property
    def zones_by_name(self) -> dict[str, Zone]:
        """Return the zones by name (names are not fixed attrs)."""
        return {zone.name: zone for zone in self.zones}

    async def _set_mode(self, mode: dict[str, str | bool]) -> None:
        """Set the TCS mode."""  # {'mode': 'Auto', 'isPermanent': True}

        if mode[S2_SYSTEM_MODE] not in self.modes:
            raise exc.InvalidParameterError(
                f"{self}: Unsupported/unknown {S2_SYSTEM_MODE}: {mode}"
            )

        await self._broker.put(f"{self._TYPE}/{self.id}/mode", json=mode)

    async def reset(self) -> None:
        """Set the TCS to auto mode (and DHW/all zones to FollowSchedule mode)."""

        if SystemMode.AUTO_WITH_RESET in self.modes:
            await self.set_mode(SystemMode.AUTO_WITH_RESET)
            return

        await self.set_mode(SystemMode.AUTO)  # may raise InvalidParameterError

        for zone in self.zones:
            await zone.reset()
        if self.hotwater:
            await self.hotwater.reset()

    async def set_mode(self, mode: SystemMode, /, *, until: dt | None = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        request: _EvoDictT

        if until is None:
            request = {
                S2_SYSTEM_MODE: mode,
                S2_PERMANENT: True,
                # S2_TIME_UNTIL: None,
            }
        else:
            request = {
                S2_SYSTEM_MODE: mode,
                S2_PERMANENT: False,
                S2_TIME_UNTIL: until.strftime(API_STRFTIME),
            }

        await self._set_mode(request)

    async def set_auto(self) -> None:
        """Set the system into normal mode."""
        await self.set_mode(SystemMode.AUTO)

    async def set_away(self, /, *, until: dt | None = None) -> None:
        """Set the system into away mode."""
        await self.set_mode(SystemMode.AWAY, until=until)

    async def set_custom(self, /, *, until: dt | None = None) -> None:
        """Set the system into custom mode."""
        await self.set_mode(SystemMode.CUSTOM, until=until)

    async def set_dayoff(self, /, *, until: dt | None = None) -> None:
        """Set the system into dayoff mode."""
        await self.set_mode(SystemMode.DAY_OFF, until=until)

    async def set_eco(self, /, *, until: dt | None = None) -> None:
        """Set the system into eco mode."""
        await self.set_mode(SystemMode.AUTO_WITH_ECO, until=until)

    async def set_heatingoff(self, /, *, until: dt | None = None) -> None:
        """Set the system into heating off mode."""
        await self.set_mode(SystemMode.HEATING_OFF, until=until)

    async def get_temperatures(
        self,
    ) -> list[dict[str, float | str | None]]:  # TODO: remove?
        """A convenience function to return the latest temperatures and setpoints."""

        await self.location.update()

        result = [
            {
                SZ_THERMOSTAT: zone.type,
                SZ_ID: zone.id,
                SZ_NAME: zone.name,
                SZ_SETPOINT: zone.target_heat_temperature,
                SZ_TEMPERATURE: zone.temperature,
            }
            for zone in self.zones
        ]

        if dhw := self.hotwater:
            dhw_status = {
                SZ_THERMOSTAT: dhw.type,
                SZ_ID: dhw.id,
                SZ_NAME: dhw.name,
                SZ_STATE: dhw.state,
                SZ_TEMPERATURE: dhw.temperature,
            }

            result.append(dhw_status)

        return result

    async def get_schedules(self) -> _ScheduleT:
        """Backup all schedules from the control system."""

        async def get_schedule(child: HotWater | Zone) -> _ScheduleT:
            try:
                return await child.get_schedule()
            except exc.InvalidScheduleError:
                self._logger.warning(
                    f"Ignoring schedule of {child.id} ({child.name}): missing/invalid"
                )
            return {}

        self._logger.info(
            f"Schedules: Backing up from {self.id} ({self.location.name})"
        )

        schedules = {}

        for zone in self.zones:
            schedules[zone.id] = {
                SZ_NAME: zone.name,
                SZ_SCHEDULE: await get_schedule(zone),
            }

        if self.hotwater:
            schedules[self.hotwater.id] = {
                SZ_NAME: self.hotwater.name,
                SZ_SCHEDULE: await get_schedule(self.hotwater),
            }

        return schedules

    async def set_schedules(
        self, schedules: _ScheduleT, match_by_name: bool = False
    ) -> bool:
        """Restore all schedules to the control system and return True if success.

        The default is to match a schedule to its zone/dhw by id.
        """

        async def restore_by_id(id: str, schedule: _ScheduleT) -> bool:
            """Restore schedule by id and return False if there was no match."""

            name = schedule.get(SZ_NAME)

            if self.hotwater and self.hotwater.id == id:
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

        async def restore_by_name(id: str, schedule: _ScheduleT) -> bool:
            """Restore schedule by name and return False if there was no match."""

            name: str = schedule[SZ_NAME]  # type: ignore[assignment]

            if self.hotwater and name == self.hotwater.name:
                await self.hotwater.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

            elif zone := self.zones_by_name.get(name):
                await zone.set_schedule(json.dumps(schedule[SZ_SCHEDULE]))

            else:
                self._logger.warning(
                    f"Ignoring schedule of {id} ({name}): unknown name"
                    ", consider matching by id rather than by name"
                )
                return False

            return True

        self._logger.info(
            f"Schedules: Restoring (matched by {'name' if match_by_name else 'id'})"
            f" to {self.id} ({self.location.name})"
        )

        with_errors = False

        for id, schedule in schedules.items():
            assert isinstance(schedule, dict)  # mypy

            if match_by_name:
                matched = await restore_by_name(id, schedule)
            else:
                matched = await restore_by_id(id, schedule)

            with_errors = with_errors and not matched

        success = not with_errors or len(schedules) == len(self.zones_by_name) + (
            1 if self.hotwater else 0
        )

        if not success:
            self._logger.warning(
                f"Schedules: Some entities not restored:"
                f" not matched by {'name' if match_by_name else 'id'}"
            )

        return success
