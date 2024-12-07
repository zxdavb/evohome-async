#!/usr/bin/env python3
"""Provides handling of TCC v0 locations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Final, NoReturn

from . import exceptions as exc
from .auth import Auth
from .schemas import (
    SZ_DHW_OFF,
    SZ_DHW_ON,
    SZ_HOLD,
    SZ_MODE,
    SZ_NAME,
    SZ_NEXT_TIME,
    SZ_QUICK_ACTION,
    SZ_QUICK_ACTION_NEXT_TIME,
    SZ_SCHEDULED,
    SZ_STATUS,
    SZ_TEMPORARY,
    SZ_THERMOSTAT,
    SZ_VALUE,
    SystemMode,
)

if TYPE_CHECKING:
    import logging
    from datetime import datetime as dt

    from . import _EvohomeClientNew as EvohomeClient
    from .auth import Auth
    from .schemas import EvoDevConfigDictT, EvoGwyConfigDictT, EvoLocConfigDictT

    _EvoDictT = dict[str, Any]


_TEMP_IS_NA: Final = 128


class EntityBase:
    # _TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

    _config: EvoDevConfigDictT | EvoGwyConfigDictT | EvoLocConfigDictT
    _status: _EvoDictT

    def __init__(self, entity_id: int, auth: Auth, logger: logging.Logger) -> None:
        self._id: Final = entity_id

        self._auth = auth
        self._logger = logger

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self._id}')"

    @property
    def id(self) -> str:
        return str(self._id)

    @property
    def config(self) -> EvoDevConfigDictT | EvoGwyConfigDictT | EvoLocConfigDictT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> _EvoDictT | None:
        """Return the latest status of the entity."""
        return self._status


class Location(EntityBase):
    """Instance of an account's location."""

    def __init__(self, client: EvohomeClient, config: EvoLocConfigDictT) -> None:
        super().__init__(
            config["location_id"],
            client.auth,
            client._logger,
        )

        self._evo = client  # proxy for parent

        self._config: EvoLocConfigDictT = config
        self._status: _EvoDictT = {}

        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}

        self.devices: list[Hotwater | Zone] = []

        self.devices_by_id: dict[str, Hotwater | Zone] = {}
        self.devices_by_idx: dict[str, Hotwater | Zone] = {}
        self.devices_by_name: dict[str, Hotwater | Zone] = {}

        def add_device(dev: Hotwater | Zone) -> None:
            self.devices.append(dev)

            self.devices_by_id[dev.id] = dev
            self.devices_by_name[dev.name] = dev
            self.devices_by_idx[dev.idx] = dev

        for dev_config in config["devices"]:
            if str(dev_config["gateway_id"]) not in self.gateway_by_id:
                gwy = Gateway(self, dev_config)

                self.gateways.append(gwy)
                self.gateway_by_id[gwy.id] = gwy

            if dev_config["thermostat_model_type"] == "DOMESTIC_HOT_WATER":
                dhw = Hotwater(gwy, dev_config)

                self.gateway_by_id[gwy.id].hotwater = dhw

                add_device(dhw)

            elif dev_config["thermostat_model_type"].startswith("EMEA_"):
                zon = Zone(gwy, dev_config)

                self.gateway_by_id[gwy.id].zones.append(zon)
                self.gateway_by_id[gwy.id].zone_by_id[zon.id] = zon

                add_device(zon)

            else:  # assume everything else is a zone
                self._logger.warning("Unknown device type: %s", dev_config)

                zon = Zone(gwy, dev_config)

                self.gateway_by_id[gwy.id].zones.append(zon)
                self.gateway_by_id[gwy.id].zone_by_id[zon.id] = zon

                add_device(zon)

    # TODO: needs a tidy-up
    async def get_temperatures(
        self, disable_refresh: bool | None = None
    ) -> list[dict[str, Any]]:  # a convenience function
        """Retrieve the latest details for each zone (incl. DHW)."""

        set_point: float
        status: str

        if not disable_refresh:
            await self._evo.update()

        result = []

        for dev in self.devices:
            temp = float(dev._config["thermostat"]["indoor_temperature"])
            values = dev._config["thermostat"]["changeable_values"]

            if "heat_setpoint" in values:
                set_point = float(values["heat_setpoint"]["value"])
                status = values["heat_setpoint"]["status"]
            else:
                set_point = 0
                status = values["status"]

            result.append(
                {
                    "device_id": dev.id,
                    "thermostat": dev._config["thermostat_model_type"],
                    "name": dev._config["name"],
                    "temperature": None if temp == _TEMP_IS_NA else temp,
                    "setpoint": set_point,
                    "status": status,
                    "mode": values["mode"],
                }
            )

        return result

    async def get_system_modes(self) -> NoReturn:
        """Return the set of modes the system can be assigned."""
        raise NotImplementedError

    async def _set_system_mode(
        self, system_mode: SystemMode, until: dt | None = None
    ) -> None:
        """Set the system mode."""

        # just want id, so retrieve the config data only if we don't already have it
        # await self._cli.update(force_refresh=False)  # get self.location_id

        data: dict[str, str] = {SZ_QUICK_ACTION: system_mode}
        if until:
            data |= {SZ_QUICK_ACTION_NEXT_TIME: until.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"evoTouchSystems?locationId={self.id}"
        await self._auth.put(url, json=data)

    async def set_auto(self) -> None:
        """Set the system to normal operation."""
        await self._set_system_mode(SystemMode.AUTO)

    async def set_away(self, /, *, until: dt | None = None) -> None:
        """Set the system to the away mode."""
        await self._set_system_mode(SystemMode.AWAY, until=until)

    async def set_custom(self, /, *, until: dt | None = None) -> None:
        """Set the system to the custom programme."""
        await self._set_system_mode(SystemMode.CUSTOM, until=until)

    async def set_dayoff(self, /, *, until: dt | None = None) -> None:
        """Set the system to the day off mode."""
        await self._set_system_mode(SystemMode.DAY_OFF, until=until)

    async def set_eco(self, /, *, until: dt | None = None) -> None:
        """Set the system to the eco mode."""
        await self._set_system_mode(SystemMode.AUTO_WITH_ECO, until=until)

    async def set_heatingoff(self, /, *, until: dt | None = None) -> None:
        """Set the system to the heating off mode."""
        await self._set_system_mode(SystemMode.HEATING_OFF, until=until)

    def _get_zone(self, zon_id: int | str) -> Zone:
        """Return the location's zone by its id, idx or name."""

        # just want id, so retrieve the config data only if we don't already have it
        # await self._cli.update(force_refresh=False)

        if isinstance(zon_id, int):
            zon_id = str(zon_id)

        dev = self.devices_by_id.get(zon_id)

        if dev is None:
            dev = self.devices_by_idx.get(zon_id)

        if dev is None:
            dev = self.devices_by_name.get(zon_id)

        if dev is None:
            raise exc.InvalidSchemaError(f"No zone {zon_id} in location {self.id}")

        if not isinstance(dev, Zone):
            raise exc.InvalidSchemaError(f"Zone {zon_id} is not an EMEA_ZONE")

        return dev

    def _get_dhw(self) -> Hotwater:
        """Return the locations's DHW, if there is one."""

        # just want id, so retrieve the config data only if we don't already have it
        # await self._cli.update(force_refresh=False)

        dev = self.devices_by_id.get("HW")

        if dev is None:
            raise exc.InvalidSchemaError(f"No DHW in location {self.id}")

        assert isinstance(dev, Hotwater)  # mypy

        return dev


class Gateway(EntityBase):
    """Instance of a location's gateway."""

    def __init__(self, location: Location, config: EvoGwyConfigDictT) -> None:
        super().__init__(
            config["gateway_id"],
            location._auth,
            location._logger,
        )

        self._loc = location  # parent

        self._config: EvoGwyConfigDictT = config  # is of one of its devices
        self._status: _EvoDictT = {}

        self.mac_address = config["mac_id"]

        self.hotwater: Hotwater | None = None

        self.zones: list[Zone] = []

        self.zone_by_id: dict[str, Zone] = {}
        self.zone_by_idx: dict[str, Zone] = {}
        self.zone_by_name: dict[str, Zone] = {}


class Zone(EntityBase):
    """Instance of a location's heating zone."""

    def __init__(self, gateway: Gateway, config: EvoDevConfigDictT) -> None:
        super().__init__(
            config["device_id"],
            gateway._auth,
            gateway._logger,
        )

        self._gwy = gateway  # parent

        self._config: EvoDevConfigDictT = config
        self._status: _EvoDictT = {}

    @property
    def name(self) -> str:
        return self._config[SZ_NAME]

    @property
    def idx(self) -> str:
        return f"{self._config["instance"]:02X}"

    async def get_zone_modes(self) -> list[str]:
        """Return the set of modes the zone can be assigned."""
        return self._config["thermostat"]["allowed_modes"]

    async def _set_heat_setpoint(
        self,
        status: str,  # "Scheduled" | "Temporary" | "Hold
        value: float | None = None,
        next_time: dt | None = None,  # "%Y-%m-%dT%H:%M:%SZ"
    ) -> None:
        """Set zone setpoint, either indefinitely, or until a set time."""

        if next_time is None:
            data = {SZ_STATUS: SZ_HOLD, SZ_VALUE: value}
        else:
            data = {
                SZ_STATUS: status,
                SZ_VALUE: value,
                SZ_NEXT_TIME: next_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        url = f"devices/{self.id}/thermostat/changeableValues/heatSetpoint"
        await self._auth.put(url, json=data)

    async def set_temperature(
        self, temperature: float, until: dt | None = None
    ) -> None:
        """Override the setpoint of a zone, for a period of time, or indefinitely."""

        if until:
            await self._set_heat_setpoint(
                SZ_TEMPORARY, value=temperature, next_time=until
            )
        else:
            await self._set_heat_setpoint(SZ_HOLD, value=temperature)

    async def set_zone_auto(self) -> None:
        """Set a zone to follow its schedule."""
        await self._set_heat_setpoint(status=SZ_SCHEDULED)

    @property
    def temperature(self) -> float:
        return float(self._config[SZ_THERMOSTAT]["indoor_temperature"])


class Hotwater(EntityBase):
    """Instance of a location's DHW zone."""

    def __init__(self, gateway: Gateway, config: EvoDevConfigDictT) -> None:
        super().__init__(
            config["device_id"],
            gateway._auth,
            gateway._logger,
        )

        self._gwy = gateway  # parent

        self._config: EvoDevConfigDictT = config
        self._status: _EvoDictT = {}

    @property
    def name(self) -> str:
        return "Domestic Hot Water"

    @property
    def idx(self) -> str:
        return "HW"

    async def _set_dhw(
        self,
        status: str,  # "Scheduled" | "Hold"
        mode: str | None = None,  # "DHWOn" | "DHWOff"
        next_time: dt | None = None,  # "%Y-%m-%dT%H:%M:%SZ"
    ) -> None:
        """Set DHW to Auto, or On/Off, either indefinitely, or until a set time."""

        data = {
            SZ_STATUS: status,
            SZ_MODE: mode,
            # SZ_NEXT_TIME: None,
            # SZ_SPECIAL_TIMES: None,
            # SZ_HEAT_SETPOINT: None,
            # SZ_COOL_SETPOINT: None,
        }
        if next_time:
            data |= {SZ_NEXT_TIME: next_time.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"devices/{self.id}/thermostat/changeableValues"
        await self._auth.put(url, json=data)

    async def set_dhw_on(self, until: dt | None = None) -> None:
        """Set DHW to On, either indefinitely, or until a specified time.

        When On, the DHW controller will work to keep its target temperature at/above
        its target temperature.  After the specified time, it will revert to its
        scheduled behaviour.
        """

        await self._set_dhw(status=SZ_HOLD, mode=SZ_DHW_ON, next_time=until)

    async def set_dhw_off(self, until: dt | None = None) -> None:
        """Set DHW to Off, either indefinitely, or until a specified time.

        When Off, the DHW controller will ignore its target temperature. After the
        specified time, it will revert to its scheduled behaviour.
        """

        await self._set_dhw(status=SZ_HOLD, mode=SZ_DHW_OFF, next_time=until)

    async def set_dhw_auto(self) -> None:
        """Allow DHW to switch between On and Off, according to its schedule."""
        await self._set_dhw(status=SZ_SCHEDULED)
