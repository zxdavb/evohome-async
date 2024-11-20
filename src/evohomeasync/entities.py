#!/usr/bin/env python3
"""Provides handling of TCC v0 locations."""

from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPMethod
from typing import TYPE_CHECKING, Any, Final, NoReturn

from . import exceptions as exc
from .auth import Auth
from .schemas import (
    SZ_ALLOWED_MODES,
    SZ_CHANGEABLE_VALUES,
    SZ_DEVICE_ID,
    SZ_DEVICES,
    SZ_DHW_OFF,
    SZ_DHW_ON,
    SZ_DOMESTIC_HOT_WATER,
    SZ_EMEA_ZONE,
    SZ_HEAT_SETPOINT,
    SZ_HOLD,
    SZ_ID,
    SZ_INDOOR_TEMPERATURE,
    SZ_LOCATION_ID,
    SZ_MODE,
    SZ_NAME,
    SZ_NEXT_TIME,
    SZ_QUICK_ACTION,
    SZ_QUICK_ACTION_NEXT_TIME,
    SZ_SCHEDULED,
    SZ_SETPOINT,
    SZ_STATUS,
    SZ_TEMP,
    SZ_TEMPORARY,
    SZ_THERMOSTAT,
    SZ_THERMOSTAT_MODEL_TYPE,
    SZ_VALUE,
)

if TYPE_CHECKING:

    from .schemas import (
        LocationResponseT,
        SystemMode,
        _DeviceDictT,
        _DhwIdT,
        _EvoListT,
        _ZoneIdT,
        _ZoneNameT,
    )

if TYPE_CHECKING:
    import logging

    from . import _EvohomeClientNew as EvohomeClient
    from .auth import Auth

    _EvoDictT = dict[str, Any]


class EntityBase:
    # _TYPE: EntityType  # e.g. "temperatureControlSystem", "domesticHotWater"

    _config: _EvoDictT
    _status: _EvoDictT

    def __init__(self, id: str, auth: Auth, logger: logging.Logger) -> None:
        self._id: Final = id

        self._auth = auth
        self._logger = logger

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}')"

    @property
    def id(self) -> str:
        return self._id

    @property
    def config(self) -> _EvoDictT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> _EvoDictT | None:
        """Return the latest status of the entity."""
        return self._status


class Location(EntityBase):
    """Instance of an account's location."""

    def __init__(self, client: EvohomeClient, config: dict[str, Any]) -> None:
        super().__init__(
            config["location_id"],
            client.auth,
            client._logger,
        )

        self._cli = client  # proxy for parent

        self._config: Final[_EvoDictT] = config
        self._status: _EvoDictT = {}

        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}

        for dev_config in config["devices"]:
            if dev_config["gateway_id"] not in self.gateway_by_id:
                gwy = Gateway(self, dev_config)

                self.gateways.append(gwy)
                self.gateway_by_id[gwy.id] = gwy

            if dev_config["thermostat_model_type"] == "DOMESTIC_HOT_WATER":
                dhw = Hotwater(gwy, dev_config)

                self.gateway_by_id[gwy.id].hotwater = dhw

            elif dev_config["thermostat_model_type"] == "EMEA_ZONE":
                zon = Zone(gwy, dev_config)

                self.gateway_by_id[gwy.id].zones.append(zon)
                self.gateway_by_id[gwy.id].zone_by_id[zon.id] = zon  # domain_id

            else:
                self._logger.warning("Unknown device type: %s", dev_config)

    async def _get_locn_data(self, force_refresh: bool = True) -> LocationResponseT:
        """Retrieve the latest system data.

        Pull the latest JSON from the web unless force_refresh is False.
        """

        if not self.locn_data or force_refresh:
            full_data = await self.auth.get_locn_data()
            self.locn_data = full_data[self._LOC_IDX]

            self.location_id = self.locn_data[SZ_LOCATION_ID]

            self.devices = {d[SZ_DEVICE_ID]: d for d in self.locn_data[SZ_DEVICES]}
            self.named_devices = {d[SZ_NAME]: d for d in self.locn_data[SZ_DEVICES]}

        return self.locn_data

    async def get_temperatures(
        self, force_refresh: bool = True
    ) -> _EvoListT:  # a convenience function
        """Retrieve the latest details for each zone (incl. DHW)."""

        set_point: float
        status: str

        await self._get_locn_data(force_refresh=force_refresh)

        result = []

        try:
            for device in self.locn_data[SZ_DEVICES]:
                temp = float(device[SZ_THERMOSTAT][SZ_INDOOR_TEMPERATURE])
                values = device[SZ_THERMOSTAT][SZ_CHANGEABLE_VALUES]

                if SZ_HEAT_SETPOINT in values:
                    set_point = float(values[SZ_HEAT_SETPOINT][SZ_VALUE])
                    status = values[SZ_HEAT_SETPOINT][SZ_STATUS]
                else:
                    set_point = 0
                    status = values[SZ_STATUS]

                result.append(
                    {
                        SZ_THERMOSTAT: device[SZ_THERMOSTAT_MODEL_TYPE],
                        SZ_ID: device[SZ_DEVICE_ID],
                        SZ_NAME: device[SZ_NAME],
                        SZ_TEMP: None if temp == 128 else temp,
                        SZ_SETPOINT: set_point,
                        SZ_STATUS: status,
                        SZ_MODE: values[SZ_MODE],
                    }
                )

        # harden code against unexpected schema (JSON structure)
        except (LookupError, TypeError, ValueError) as err:
            raise exc.InvalidSchemaError(str(err)) from err
        return result  # type: ignore[return-value]

    async def get_system_modes(self) -> NoReturn:
        """Return the set of modes the system can be assigned."""
        raise NotImplementedError

    async def _set_system_mode(
        self, system_mode: SystemMode, until: dt | None = None
    ) -> None:
        """Set the system mode."""

        # just want id, so retrieve the config data only if we don't already have it
        await self._get_locn_data(force_refresh=False)  # get self.location_id

        data: dict[str, str] = {SZ_QUICK_ACTION: system_mode}
        if until:
            data |= {SZ_QUICK_ACTION_NEXT_TIME: until.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"evoTouchSystems?locationId={self.location_id}"
        await self.auth.request(HTTPMethod.PUT, url, data=data)

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

    #
    # Zone methods...

    async def _get_zone(self, id_or_name: _ZoneIdT | _ZoneNameT) -> _DeviceDictT:
        """Return the location's zone by its id or name (if needed, get the JSON).

        Raise an exception if the zone is not found.
        """

        device_dict: _DeviceDictT | None

        # just want id, so retrieve the config data only if we don't already have it
        await self._get_locn_data(force_refresh=False)

        if isinstance(id_or_name, int):
            device_dict = self.devices.get(id_or_name)
        else:
            device_dict = self.named_devices.get(id_or_name)

        if device_dict is None:
            raise exc.InvalidSchemaError(
                f"No zone {id_or_name} in location {self.location_id}"
            )

        if (model := device_dict[SZ_THERMOSTAT_MODEL_TYPE]) != SZ_EMEA_ZONE:
            raise exc.InvalidSchemaError(
                f"Zone {id_or_name} is not an EMEA_ZONE: {model}"
            )

        return device_dict

    #
    # DHW methods...

    async def _get_dhw(self) -> _DeviceDictT:
        """Return the locations's DHW, if there is one (if needed, get the JSON).

        Raise an exception if the DHW is not found.
        """

        # just want id, so retrieve the config data only if we don't already have it
        await self._get_locn_data(force_refresh=False)

        for device in self.locn_data[SZ_DEVICES]:
            if device[SZ_THERMOSTAT_MODEL_TYPE] == SZ_DOMESTIC_HOT_WATER:
                ret: _DeviceDictT = device
                return ret

        raise exc.InvalidSchemaError(f"No DHW in location {self.location_id}")


class Gateway(EntityBase):
    """Instance of a location's gateway."""

    def __init__(self, location: Location, config: dict[str, Any]) -> None:
        super().__init__(
            config["gateway_id"],
            location._auth,
            location._logger,
        )

        self._loc = location  # parent

        self._config: Final[_EvoDictT] = config
        self._status: _EvoDictT = {}

        self.mac_address = config["mac_id"]

        self.hotwater: Hotwater = None

        self.zones: list[Zone] = []
        self.zone_by_id: dict[str, Zone] = {}


class Zone(EntityBase):
    """Instance of a location's gateway."""

    def __init__(self, gateway: Gateway, config: dict[str, Any]) -> None:
        super().__init__(
            config["device_id"],
            gateway._auth,
            gateway._logger,
        )

        self._gwy = gateway  # parent

        self._config: Final[_EvoDictT] = config
        self._status: _EvoDictT = {}

    @property
    def name(self) -> str:
        return self._config[SZ_NAME]

    @property
    def idx(self) -> str:
        return f"{self._config["instance"]:02X}"

    async def get_zone_modes(self, zone: _ZoneNameT) -> list[str]:
        """Return the set of modes the zone can be assigned."""

        device = await self._get_zone(zone)

        ret: list[str] = device[SZ_THERMOSTAT][SZ_ALLOWED_MODES]
        return ret

    async def _set_heat_setpoint(
        self,
        zone: _ZoneIdT | _ZoneNameT,
        status: str,  # "Scheduled" | "Temporary" | "Hold
        value: float | None = None,
        next_time: dt | None = None,  # "%Y-%m-%dT%H:%M:%SZ"
    ) -> None:
        """Set zone setpoint, either indefinitely, or until a set time."""

        zone_id: _ZoneIdT = (await self._get_zone(zone))[SZ_DEVICE_ID]

        if next_time is None:
            data = {SZ_STATUS: SZ_HOLD, SZ_VALUE: value}
        else:
            data = {
                SZ_STATUS: status,
                SZ_VALUE: value,
                SZ_NEXT_TIME: next_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        url = f"devices/{zone_id}/thermostat/changeableValues/heatSetpoint"
        await self.auth.request(HTTPMethod.PUT, url, data=data)

    async def set_temperature(
        self, zone: _ZoneIdT | _ZoneNameT, temperature: float, until: dt | None = None
    ) -> None:
        """Override the setpoint of a zone, for a period of time, or indefinitely."""

        if until:
            await self._set_heat_setpoint(
                zone, SZ_TEMPORARY, value=temperature, next_time=until
            )
        else:
            await self._set_heat_setpoint(zone, SZ_HOLD, value=temperature)

    async def set_zone_auto(self, zone: _ZoneIdT | _ZoneNameT) -> None:
        """Set a zone to follow its schedule."""
        await self._set_heat_setpoint(zone, status=SZ_SCHEDULED)


class Hotwater(EntityBase):
    """Instance of a location's gateway."""

    def __init__(self, gateway: Gateway, config: dict[str, Any]) -> None:
        super().__init__(
            config["device_id"],
            gateway._auth,
            gateway._logger,
        )

        self._gwy = gateway  # parent

        self._config: Final[_EvoDictT] = config
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

        dhw_id: _DhwIdT = (await self._get_dhw())[SZ_DEVICE_ID]

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

        url = f"devices/{dhw_id}/thermostat/changeableValues"
        await self.auth.request(HTTPMethod.PUT, url, data=data)

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
