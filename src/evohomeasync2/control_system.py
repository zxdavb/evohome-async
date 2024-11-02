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
    SZ_ID,
    SZ_NAME,
    SZ_SCHEDULE,
    SZ_SETPOINT,
    SZ_TEMP,
    SZ_THERMOSTAT,
    SystemMode,
)
from .hotwater import HotWater
from .schema import SCH_TCS_STATUS, convert_keys_to_snake_case
from .schema.const import (
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
    SZ_TIME_UNTIL,
    SZ_ZONE_ID,
    SZ_ZONES,
    EntityType,
)
from .zone import ActiveFaultsBase, Zone

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Gateway, Location
    from .schema import _EvoDictT, _EvoListT, _ScheduleT


class ControlSystem(ActiveFaultsBase):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_TCS_STATUS
    TYPE: Final = EntityType.TCS  # type: ignore[misc]

    def __init__(self, gateway: Gateway, config: _EvoDictT) -> None:
        super().__init__(
            config[SZ_SYSTEM_ID],
            gateway._broker,
            gateway._logger,
        )

        self.gateway = gateway  # parent
        self.location: Location = gateway.location

        self._config: Final[_EvoDictT] = {
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }
        self._status: _EvoDictT = {}

        # children
        self.zones: list[Zone] = []
        self.zones_by_id: dict[str, Zone] = {}

        self.hotwater: None | HotWater = None

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

    @property
    def allowed_system_modes(self) -> _EvoListT:
        ret: _EvoListT = self._config[SZ_ALLOWED_SYSTEM_MODES]
        return convert_keys_to_snake_case(ret)

    @property
    def model_type(self) -> str:
        ret: str = self._config[SZ_MODEL_TYPE]
        return ret

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
    def system_mode_status(self) -> _EvoDictT | None:
        return self._status.get(SZ_SYSTEM_MODE_STATUS)

    @property  # status attr for convenience (new)
    def system_mode(self) -> str | None:
        if (status := self._status.get(SZ_SYSTEM_MODE_STATUS)) is None:
            return None
        ret: str = status[SZ_MODE]
        return ret

    @property
    def zones_by_name(self) -> dict[str, Zone]:
        """Return the zones by name (names are not fixed attrs)."""
        return {zone.name: zone for zone in self.zones}

    async def _set_mode(self, mode: dict[str, str | bool]) -> None:
        """Set the TCS mode."""  # {'mode': 'Auto', 'isPermanent': True}
        _ = await self._broker.put(f"{self.TYPE}/{self.id}/mode", json=mode)

    async def reset_mode(self) -> None:
        """Set the TCS to auto mode (and DHW/all zones to FollowSchedule mode)."""
        await self.set_mode(SystemMode.AUTO_WITH_RESET)

    async def set_mode(self, mode: SystemMode, /, *, until: dt | None = None) -> None:
        """Set the system to a mode, either indefinitely, or for a set time."""

        request: _EvoDictT

        if mode not in [
            m[SZ_SYSTEM_MODE] for m in self._config[SZ_ALLOWED_SYSTEM_MODES]
        ]:
            raise exc.InvalidParameterError(f"{self}: Unsupported/unknown mode: {mode}")

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

    async def temperatures(self) -> _EvoListT:
        """A convenience function to return the latest temperatures and setpoints."""

        await self.location.update()

        result = []

        if dhw := self.hotwater:
            dhw_status = {
                SZ_THERMOSTAT: "DOMESTIC_HOT_WATER",
                SZ_ID: dhw.id,
                SZ_NAME: dhw.name,
                SZ_TEMP: None,
            }

            if (
                isinstance(dhw.temperature_status, dict)
                and dhw.temperature_status[SZ_IS_AVAILABLE]
            ):
                dhw_status[SZ_TEMP] = dhw.temperature_status[SZ_TEMPERATURE]

            result.append(dhw_status)

        for zone in self.zones:
            zone_status = {
                SZ_THERMOSTAT: "EMEA_ZONE",
                SZ_ID: zone.id,
                SZ_NAME: zone.name,
                SZ_SETPOINT: None,
                SZ_TEMP: None,
            }

            if isinstance(zone.setpoint_status, dict):
                zone_status[SZ_SETPOINT] = zone.setpoint_status[
                    SZ_TARGET_HEAT_TEMPERATURE
                ]

            if (
                isinstance(zone.temperature_status, dict)
                and zone.temperature_status[SZ_IS_AVAILABLE]
            ):
                zone_status[SZ_TEMP] = zone.temperature_status[SZ_TEMPERATURE]

            result.append(zone_status)

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
