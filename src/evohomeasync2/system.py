"""Provides handling of TCC temperature control systems."""

# TODO: extend set_mode() for non-evohome modes (e.g. "Heat", "Off")

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .const import (
    API_STRFTIME,
    SZ_ALLOWED_SYSTEM_MODES,
    SZ_DAILY_SCHEDULES,
    SZ_DHW,
    SZ_DHW_ID,
    SZ_ID,  # remove?
    SZ_MODE,
    SZ_MODEL_TYPE,
    SZ_NAME,
    SZ_SETPOINT,  # remove?
    SZ_STATE,
    SZ_SYSTEM_ID,
    SZ_SYSTEM_MODE,
    SZ_SYSTEM_MODE_STATUS,
    SZ_TEMPERATURE,  # remove?
    SZ_THERMOSTAT,  # remove?
    SZ_ZONE_ID,
    SZ_ZONES,
)
from .hotwater import HotWater
from .schemas import SystemMode, factory_tcs_status
from .schemas.const import (
    S2_PERMANENT,
    S2_SYSTEM_MODE,
    S2_TIME_UNTIL,
    EntityType,
    TcsModelType,
)
from .zone import ActiveFaultsBase, Zone

if TYPE_CHECKING:
    from datetime import datetime as dt

    import voluptuous as vol

    from . import Gateway, Location
    from .schemas.typedefs import (
        DayOfWeekDhwT,
        DayOfWeekZoneT,
        EvoAllowedSystemModeT,
        EvoScheduleDhwT,
        EvoScheduleZoneT,
        EvoSystemModeStatusT,
        EvoTcsConfigEntryT,
        EvoTcsConfigResponseT,
        EvoTcsStatusResponseT,
    )


class ControlSystem(ActiveFaultsBase):
    """Instance of a gateway's TCS (temperatureControlSystem)."""

    SCH_STATUS: vol.Schema = factory_tcs_status(camel_to_snake)
    _TYPE = EntityType.TCS

    def __init__(self, gateway: Gateway, config: EvoTcsConfigResponseT) -> None:
        super().__init__(
            config[SZ_SYSTEM_ID],
            gateway._auth,
            gateway._logger,
        )

        self.gateway = gateway  # parent
        self.location: Location = gateway.location

        self._config: Final[EvoTcsConfigEntryT] = {  # type: ignore[assignment,misc]
            k: v for k, v in config.items() if k not in (SZ_DHW, SZ_ZONES)
        }
        self._status: EvoTcsStatusResponseT | None = None

        # children
        self.zones: list[Zone] = []
        self.zones_by_id: dict[str, Zone] = {}

        self.hotwater: HotWater | None = None

        for zon_entry in config[SZ_ZONES]:
            try:
                zone = Zone(self, zon_entry)
            except exc.InvalidSchemaError as err:
                self._logger.warning(
                    f"{self}: zone_id='{zon_entry[SZ_ZONE_ID]}' ignored: {err}"
                )
            else:
                self.zones.append(zone)
                self.zones_by_name[zone.name] = zone
                self.zones_by_id[zone.id] = zone

        if dhw_entry := config.get(SZ_DHW):
            self.hotwater = HotWater(self, dhw_entry)

    def _update_status(self, status: EvoTcsStatusResponseT) -> None:
        self._update_faults(status["active_faults"])
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
    def allowed_system_modes(self) -> tuple[EvoAllowedSystemModeT, ...]:
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

        return tuple(self._config[SZ_ALLOWED_SYSTEM_MODES])

    @property  # a convenience attr
    def mode(self) -> SystemMode | None:
        if self.system_mode_status is None:
            return None
        return self.system_mode_status[SZ_MODE]

    @property  # a convenience attr
    def modes(self) -> tuple[SystemMode, ...]:
        return tuple(d[SZ_SYSTEM_MODE] for d in self.allowed_system_modes)

    @property
    def model(self) -> TcsModelType:
        return self._config[SZ_MODEL_TYPE]

    @property
    def system_mode_status(self) -> EvoSystemModeStatusT | None:
        """
        "systemModeStatus": {
            "mode": "AutoWithEco",
            "isPermanent": true
        }
        """
        if self._status is None:
            return None
        return self._status[SZ_SYSTEM_MODE_STATUS]

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

        await self._auth.put(f"{self._TYPE}/{self.id}/mode", json=mode)

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

        await self._set_mode(request)  # type: ignore[arg-type]

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
    ) -> list[dict[str, float | str | None]]:  # TODO: remove this convenience function?
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

    async def get_schedules(self) -> list[EvoScheduleDhwT | EvoScheduleZoneT]:
        """Backup all schedules from the control system."""

        async def get_schedule(
            child: HotWater | Zone,
        ) -> list[DayOfWeekDhwT] | list[DayOfWeekZoneT]:
            try:
                return await child.get_schedule()
            except exc.InvalidScheduleError:
                self._logger.warning(
                    f"Ignoring schedule of {child.id} ({child.name}): missing/invalid"
                )
            return []

        self._logger.info(
            f"Schedules: Backing up from {self.id} ({self.location.name})"
        )

        schedules: list[EvoScheduleDhwT | EvoScheduleZoneT] = []

        for zone in self.zones:
            schedules.append(  # noqa: PERF401
                {
                    SZ_ZONE_ID: zone.id,
                    SZ_NAME: zone.name,
                    SZ_DAILY_SCHEDULES: await get_schedule(zone),  # type: ignore[typeddict-item]
                }
            )
        if self.hotwater:
            schedules.append(
                {
                    SZ_ZONE_ID: self.hotwater.id,
                    SZ_NAME: self.hotwater.name,
                    SZ_DAILY_SCHEDULES: await get_schedule(self.hotwater),  # type: ignore[typeddict-item]
                }
            )

        return schedules

    async def set_schedules(
        self,
        schedules: list[EvoScheduleDhwT | EvoScheduleZoneT],
        match_by_name: bool | None = None,
    ) -> bool:
        """Restore all schedules to the control system and return True if success.

        The default is to match a schedule to its zone/dhw by id.
        """

        async def restore_by_id(sched: EvoScheduleDhwT | EvoScheduleZoneT) -> bool:
            """Restore a schedule by id and return False if there was no match."""

            id_: str = sched.get("zone_id") or sched["dhw_id"]  # type: ignore[assignment,typeddict-item]

            if self.hotwater and self.hotwater.id == id_:
                await self.hotwater.set_schedule(json.dumps(sched["daily_schedules"]))

            elif zone := self.zones_by_id.get(id_):
                await zone.set_schedule(json.dumps(sched["daily_schedules"]))

            else:
                self._logger.warning(
                    f"Ignoring schedule of {id_} ({sched.get("name")}): unknown id"
                    ", consider matching by name rather than by id"
                )
                return False

            return True

        async def restore_by_name(sched: EvoScheduleDhwT | EvoScheduleZoneT) -> bool:
            """Restore a schedule by name and return False if there was no match."""

            name: str | None = sched.get("name")  # name is NotRequired[str]

            if name and self.hotwater and name == self.hotwater.name:
                await self.hotwater.set_schedule(json.dumps(sched["daily_schedules"]))

            elif name and (zone := self.zones_by_name.get(name)):
                await zone.set_schedule(json.dumps(sched["daily_schedules"]))

            else:
                id_: str = sched.get("zone_id") or sched["dhw_id"]  # type: ignore[assignment,typeddict-item]

                self._logger.warning(
                    f"Ignoring schedule of {id_} ({name}): unknown name"
                    ", consider matching by id rather than by name"
                )
                return False

            return True

        self._logger.info(
            f"Schedules: Restoring (matched by {'name' if match_by_name else 'id'})"
            f" to {self.id} ({self.location.name})"
        )

        fnc = restore_by_name if match_by_name else restore_by_id
        all_restored = all([await fnc(sch) for sch in schedules])

        same_count = len(schedules) == len(self.zones) + (1 if self.hotwater else 0)

        if not (success := same_count and all_restored):
            self._logger.debug("Some schedules not restored (DHW?)")

        return success