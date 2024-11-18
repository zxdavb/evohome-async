#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPMethod
from typing import TYPE_CHECKING, NoReturn

from . import exceptions as exc
from .auth import AbstractSessionManager, Auth
from .location import Location
from .schema import (
    SCH_LOCATION_RESPONSE,
    SCH_USER_ACCOUNT_RESPONSE,
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
    SZ_USER_ID as S2_USER_ID,
    SZ_VALUE,
)

if TYPE_CHECKING:
    import aiohttp

    from .schema import (
        LocationResponseT,
        SystemMode,
        UserAccountResponseT,
        _DeviceDictT,
        _DhwIdT,
        _EvoListT,
        _LocationIdT,
        _ZoneIdT,
        _ZoneNameT,
    )


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClientNew:
    """Provide a client to access the Resideo TCC API (assumes a single TCS)."""

    _LOC_IDX: int = 0  # the index of the location in the full_data list

    _user_info: UserAccountResponseT | None = None
    _user_locs: list[LocationResponseT] | None = None  # all locations of the user

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v0 EvohomeClient object."""

        self._logger = _LOGGER
        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode is explicitly enabled.")

        self.location_id: _LocationIdT = None  # type: ignore[assignment]

        self.devices: dict[_ZoneIdT, _DeviceDictT] = {}  # dhw or zone by id
        self.named_devices: dict[_ZoneNameT, _DeviceDictT] = {}  # zone by name

        self.auth = Auth(
            session_manager,
            websession or session_manager._websession,
            logger=self._logger,
        )

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    #
    # New methods...

    async def update(
        self,
        /,
        *,
        _reset_config: bool = False,
        # _dont_update_status: bool = False,
    ) -> LocationResponseT | None:
        """Retrieve the latest state of the installation and it's locations.

        If required, or when `_reset_config` is true, first retrieves the user
        information.
        """

        if _reset_config:
            self._user_info = None
            #

        if self._user_info is None:
            url = "accountInfo"
            self._user_info = await self.auth.get(url, schema=SCH_USER_ACCOUNT_RESPONSE)

        # assert self._user_info is not None  # mypy hint

        if self._user_locs is None:
            url = f"locations?userId={self._user_info[S2_USER_ID]}&allData=True"
            #

            self.locn_data = await self.auth.get(url, schema=SCH_LOCATION_RESPONSE)

            self._locations = None
            self._location_by_id = None

        # assert self._user_locs is not None  # mypy hint

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_config in self._user_locs:
                loc = Location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

        self._locn_info = self._user_locs[self._LOC_IDX]

        self.location_id = self._locn_info[SZ_LOCATION_ID]

        self.devices = {d[SZ_DEVICE_ID]: d for d in self._locn_info[SZ_DEVICES]}
        self.named_devices = {d[SZ_NAME]: d for d in self._locn_info[SZ_DEVICES]}

        return self._user_locs

    @property
    def user_account(self) -> UserAccountResponseT:
        """Return the information of the user account."""

        if self._user_info is None:
            raise exc.NoSystemConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return self._user_info

    #
    # Location methods...

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
