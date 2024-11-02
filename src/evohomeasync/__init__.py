#!/usr/bin/env python3
"""evohomeasync provides an async client for the *original* Evohome TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPMethod
from typing import TYPE_CHECKING, NoReturn

from . import exceptions as exc
from .auth import Auth
from .exceptions import (  # noqa: F401
    AuthenticationFailedError,
    EvohomeError,
    InvalidSchemaError,
    RateLimitExceededError,
    RequestFailedError,
)
from .schema import (
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
    SZ_SESSION_ID,
    SZ_SETPOINT,
    SZ_STATUS,
    SZ_TEMP,
    SZ_TEMPORARY,
    SZ_THERMOSTAT,
    SZ_THERMOSTAT_MODEL_TYPE,
    SZ_USER_INFO,
    SZ_VALUE,
)

if TYPE_CHECKING:
    import aiohttp

    from .auth import _LocnDataT, _SessionIdT, _UserDataT, _UserInfoT
    from .schema import (
        SystemMode,
        _DeviceDictT,
        _DhwIdT,
        _EvoListT,
        _LocationIdT,
        _ZoneIdT,
        _ZoneNameT,
    )


__version__ = "1.2.0"

_LOGGER = logging.getLogger(__name__)


# any API request invokes self._populate_user_data()             (for authentication)
# - every API GET invokes self._populate_locn_data(refresh=True) (for up-to-date state)
# - every API PUT invokes self._populate_locn_data()             (for config)


class EvohomeClient:
    """Provide a client to access the Honeywell TCC API (assumes a single TCS)."""

    _LOC_IDX: int = 0  # the index of the location in the full_data list

    user_info: _UserInfoT  # user_data[SZ_USER_INFO] only (i.e. *without* "sessionID")
    location_data: _LocnDataT  # of the first location (config and status) in list

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        session_id: _SessionIdT | None = None,
        websession: aiohttp.ClientSession | None = None,
        hostname: str | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v1 EvohomeClient object.

        If a session_id is provided it will be used to avoid calling the
        authentication service, which is known to be rate limited.
        """

        if debug:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")

        self.user_info = {}  # type: ignore[assignment]
        self.location_data = {}  # type: ignore[assignment]
        self.location_id: _LocationIdT = None  # type: ignore[assignment]

        self.devices: dict[_ZoneIdT, _DeviceDictT] = {}  # dhw or zone by id
        self.named_devices: dict[_ZoneNameT, _DeviceDictT] = {}  # zone by name

        self.auth = Auth(
            username,
            password,
            _LOGGER,
            session_id=session_id,
            hostname=hostname,
            session=websession,
        )

    @property
    def user_data(self) -> _UserDataT | None:  # TODO: deprecate?
        """Return the user data used for HTTP authentication."""

        if not self.auth.session_id:
            return None
        return {  # type: ignore[return-value]
            SZ_SESSION_ID: self.auth.session_id,
            SZ_USER_INFO: self.user_info,
        }

    # User methods...

    async def update(
        self,
        /,
        *,
        reset_config: bool = False,
    ) -> None:
        """Update the user and location data."""
        await self._populate_user_data(force_refresh=reset_config)
        await self._populate_locn_data(force_refresh=reset_config)

    async def _populate_user_data(
        self, force_refresh: bool = False
    ) -> dict[str, bool | int | str]:
        """Retrieve the cached user data (excl. the session id).

        Pull the latest JSON from the web only if force_refresh is True.
        """

        if not self.user_info or force_refresh:
            user_data = await self.auth.populate_user_data()
            self.user_info = user_data[SZ_USER_INFO]  # type: ignore[assignment]

        return self.user_info  # excludes session id

    async def _get_user(self) -> _UserInfoT:
        """Return the user (if needed, get the JSON)."""

        # only retrieve the config data if we don't already have it
        if not self.user_info:
            await self._populate_user_data(force_refresh=False)
        return self.user_info

    # Location methods...

    async def _populate_locn_data(self, force_refresh: bool = True) -> _LocnDataT:
        """Retrieve the latest system data.

        Pull the latest JSON from the web unless force_refresh is False.
        """

        if not self.location_data or force_refresh:
            full_data = await self.auth.populate_full_data()
            self.location_data = full_data[self._LOC_IDX]

            self.location_id = self.location_data[SZ_LOCATION_ID]

            self.devices = {d[SZ_DEVICE_ID]: d for d in self.location_data[SZ_DEVICES]}
            self.named_devices = {d[SZ_NAME]: d for d in self.location_data[SZ_DEVICES]}

        return self.location_data

    async def get_temperatures(
        self, force_refresh: bool = True
    ) -> _EvoListT:  # a convenience function
        """Retrieve the latest details for each zone (incl. DHW)."""

        set_point: float
        status: str

        await self._populate_locn_data(force_refresh=force_refresh)

        result = []

        try:
            for device in self.location_data[SZ_DEVICES]:
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
        await self._populate_locn_data(force_refresh=False)  # get self.location_id

        data: dict[str, str] = {SZ_QUICK_ACTION: system_mode}
        if until:
            data |= {SZ_QUICK_ACTION_NEXT_TIME: until.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"evoTouchSystems?locationId={self.location_id}"
        await self.auth.make_request(HTTPMethod.PUT, url, data=data)

    async def set_mode_auto(self) -> None:
        """Set the system to normal operation."""
        await self._set_system_mode(SystemMode.AUTO)

    async def set_mode_away(self, until: dt | None = None) -> None:
        """Set the system to the away mode."""
        await self._set_system_mode(SystemMode.AWAY, until)

    async def set_mode_custom(self, until: dt | None = None) -> None:
        """Set the system to the custom programme."""
        await self._set_system_mode(SystemMode.CUSTOM, until)

    async def set_mode_dayoff(self, until: dt | None = None) -> None:
        """Set the system to the day off mode."""
        await self._set_system_mode(SystemMode.DAY_OFF, until)

    async def set_mode_eco(self, until: dt | None = None) -> None:
        """Set the system to the eco mode."""
        await self._set_system_mode(SystemMode.AUTO_WITH_ECO, until)

    async def set_mode_heatingoff(self, until: dt | None = None) -> None:
        """Set the system to the heating off mode."""
        await self._set_system_mode(SystemMode.HEATING_OFF, until)

    # Zone methods...

    async def _get_zone(self, id_or_name: _ZoneIdT | _ZoneNameT) -> _DeviceDictT:
        """Return the location's zone by its id or name (if needed, get the JSON).

        Raise an exception if the zone is not found.
        """

        device_dict: _DeviceDictT | None

        # just want id, so retrieve the config data only if we don't already have it
        await self._populate_locn_data(force_refresh=False)

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
        await self.auth.make_request(HTTPMethod.PUT, url, data=data)

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

    # DHW methods...

    async def _get_dhw(self) -> _DeviceDictT:
        """Return the locations's DHW, if there is one (if needed, get the JSON).

        Raise an exception if the DHW is not found.
        """

        # just want id, so retrieve the config data only if we don't already have it
        await self._populate_locn_data(force_refresh=False)

        for device in self.location_data[SZ_DEVICES]:
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
        await self.auth.make_request(HTTPMethod.PUT, url, data=data)

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
