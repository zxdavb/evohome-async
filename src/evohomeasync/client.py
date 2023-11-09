#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime as dt
from http import HTTPMethod
from typing import TYPE_CHECKING, NoReturn

import aiohttp

from .broker import Broker, _FullDataT, _SessionIdT, _UserDataT, _UserInfoT
from .exceptions import DeprecationError, InvalidSchema

if TYPE_CHECKING:
    from .schema import (
        _EvoDictT,
        _EvoListT,
        _LocationIdT,
        _SystemModeT,
        _TaskIdT,
        _ZoneNameT,
    )


_LOGGER = logging.getLogger(__name__)


class EvohomeClientDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def user_data(self) -> _UserDataT | None:
        raise DeprecationError(
            "EvohomeClient.user_data is deprecated, use .user_info"
            " (session_id is now .broker.session_id)"
        )

    @property
    def headers(self) -> str:
        raise DeprecationError("EvohomeClient.headers is deprecated")

    @property
    def hostname(self) -> str:
        raise DeprecationError(
            "EvohomeClient.hostanme is deprecated, use .broker.hostname"
        )

    @property
    def postdata(self) -> str:
        raise DeprecationError("EvohomeClient.postdata is deprecated")

    async def _wait_for_put_task(self, response: aiohttp.ClientResponse) -> None:
        """This functionality is deprecated, but remains here as documentation."""

        async def get_task_status(task_id: _TaskIdT) -> str:
            await self._populate_full_data()

            url = f"/commTasks?commTaskId={task_id}"
            response = await self._do_request(HTTPMethod.GET, url)

            return dict(await response.json())["state"]

        task_id: _TaskIdT

        assert response.method == HTTPMethod.PUT

        ret = await response.json()
        task_id = ret[0]["id"] if isinstance(ret, list) else ret["id"]

        # FIXME: could wait forvever?
        while await get_task_status(task_id) != "Succeeded":
            await asyncio.sleep(1)

    # Not deprecated, just a placeholder for self._wait_for_put_task()
    async def _do_request(self, *args, **kwargs) -> aiohttp.ClientResponse:
        raise NotImplementedError

    # Not deprecated, just a placeholder for self._wait_for_put_task()
    async def _populate_full_data(self, force_refresh: bool = True) -> _FullDataT:
        raise NotImplementedError

    async def get_system_modes(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.get_modes() is deprecated, "
            "use .get_system_modes() or .get_zone_modes()"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_away() is deprecated, use .set_mode_away()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_custom() is deprecated, use .set_mode_custom()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_dayoff() is deprecated, use .set_mode_dayoff()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_eco() is deprecated, use .set_mode_eco()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_heatingoff() is deprecated, use .set_mode_heatingoff()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_normal() is deprecated, use .set_mode_auto()"
        )


class EvohomeClient(EvohomeClientDeprecated):
    """Provide a client to access the Honeywell TCC API (assumes a single TCS)."""

    user_info: _UserInfoT  # user_idata["UserInfo"] *without* session_id
    full_data: _FullDataT  # of a single location (config and status)

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        session_id: _SessionIdT | None = None,
        session: aiohttp.ClientSession | None = None,
        hostname: str | None = None,  # is a URL
        debug: bool = False,
    ) -> None:
        """Construct the v1 EvohomeClient object.

        If a session_id is provided it will be used to avoid calling the
        authentication service, which is known to be rate limited.
        """
        if debug:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")

        self.user_info = {}
        self.full_data = {}
        self.location_id: _LocationIdT = None  # type: ignore[assignment]

        self.devices: _FullDataT = {}  # dhw or zone by id
        self.named_devices: _FullDataT = {}  # zone by name

        self.broker = Broker(
            username,
            password,
            _LOGGER,
            session_id=session_id,
            hostname=hostname,
            session=session,
        )

    @property
    def user_data(self) -> _UserDataT | None:  # TODO: deprecate?
        """Return the user data used for HTTP authentication."""

        if not self.broker.session_id:
            return None
        return {
            "sessionId": self.broker.session_id,
            "userInfo": self.user_info,
        }

    # User methods...

    async def _populate_user_data(
        self, force_refresh: bool = False
    ) -> dict[str, bool | int | str]:
        """Retrieve the cached user data (excl. the session ID).

        Pull the latest JSON from the web only if force_refresh is True.
        """

        if not self.user_info or force_refresh:
            user_data = await self.broker.populate_user_data()
            self.user_info = user_data["userInfo"]  # type: ignore[assignment]

        return self.user_info  # excludes session ID

    async def _get_user(self) -> _UserInfoT:
        """Return the user (if needed, get the JSON)."""

        # only retrieve the config data if we don't already have it
        if not self.user_info:
            await self._populate_user_data(force_refresh=False)
        return self.user_info

    # Location methods...

    async def _populate_full_data(self, force_refresh: bool = True) -> _FullDataT:
        """Retrieve the latest system data.

        Pull the latest JSON from the web unless force_refresh is False.
        """

        if not self.full_data or force_refresh:
            full_data = await self.broker.populate_full_data()
            self.full_data = full_data[0]

            self.devices = {d["deviceID"]: d for d in self.full_data["devices"]}
            self.named_devices = {d["name"]: d for d in self.full_data["devices"]}

        return self.full_data

    async def temperatures(self) -> _EvoListT:  # DEPRECATED
        return await self.get_temperatures()

    async def get_temperatures(self) -> _EvoListT:  # a convenience function
        """Retrieve the latest details for each zone (incl. DHW)."""

        set_point: float
        status: str

        await self._populate_full_data(force_refresh=True)

        result = []

        try:
            for device in self.full_data["devices"]:
                temp = float(device["thermostat"]["indoorTemperature"])
                values = device["thermostat"]["changeableValues"]

                if "heatSetpoint" in values:
                    set_point = float(values["heatSetpoint"]["value"])
                    status = values["heatSetpoint"]["status"]
                else:
                    set_point = 0
                    status = values["status"]

                result.append(
                    {
                        "thermostat": device["thermostatModelType"],
                        "id": device["deviceID"],
                        "name": device["name"],
                        "temp": None if temp == 128 else temp,
                        "setpoint": set_point,
                        "status": status,
                        "mode": values["mode"],
                    }
                )

        # harden code against unexpected schema (JSON structure)
        except (LookupError, TypeError, ValueError) as exc:
            raise InvalidSchema(str(exc)) from exc
        return result

    async def _get_location(self) -> _FullDataT:
        """Return the frst location (if needed, get the JSON)."""

        # just want id, so retrieve the config data only if we don't already have it
        await self._populate_full_data(force_refresh=False)

        return self.full_data

    async def get_system_modes(self) -> NoReturn:
        """Return the set of modes the system can be assigned."""
        raise NotImplementedError

    async def _set_system_mode(
        self, status: _SystemModeT, until: dt | None = None
    ) -> None:
        """Set the system mode."""

        location_id = (await self._get_location())["locationID"]

        data = {"QuickAction": status}
        if until:
            data |= {"QuickActionNextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"/evoTouchSystems?locationId={location_id}"
        await self.broker._request(HTTPMethod.PUT, url, data=data)

    async def set_mode_auto(self) -> None:
        """Set the system to normal operation."""
        await self._set_system_mode("Auto")

    async def set_mode_away(self, until: dt | None = None) -> None:
        """Set the system to the away mode."""
        await self._set_system_mode("Away", until)

    async def set_mode_custom(self, until: dt | None = None) -> None:
        """Set the system to the custom programme."""
        await self._set_system_mode("Custom", until)

    async def set_mode_dayoff(self, until: dt | None = None) -> None:
        """Set the system to the day off mode."""
        await self._set_system_mode("DayOff", until)

    async def set_mode_eco(self, until: dt | None = None) -> None:
        """Set the system to the eco mode."""
        await self._set_system_mode("AutoWithEco", until)

    async def set_mode_heatingoff(self, until: dt | None = None) -> None:
        """Set the system to the heating off mode."""
        await self._set_system_mode("HeatingOff", until)

    # Zone methods...

    async def _get_zone(self, id_or_name: str) -> _EvoDictT:
        """Return the location's zone by its id or name (if needed, get the JSON).

        Raise an exception if the zone is not found.
        """

        # just want id, so retrieve the config data only if we don't already have it
        await self._populate_full_data(force_refresh=False)

        device = self.devices.get(id_or_name)
        if not device:
            device = self.named_devices.get(id_or_name)

        if device is None:
            raise InvalidSchema(f"No zone {id_or_name} in location {self.location_id}")

        if (model := device["thermostatModelType"]) != "EMEA_ZONE":
            raise InvalidSchema(f"Zone {id_or_name} is not an EMEA_ZONE: {model}")

        return device

    async def get_zone_modes(self, zone: _ZoneNameT) -> list[str]:
        """Return the set of modes the zone can be assigned."""

        device: _EvoDictT = await self._get_zone(zone)
        return device["thermostat"]["allowedModes"]

    async def _set_heat_setpoint(
        self,
        zone_id: _ZoneNameT,
        status: str,  # "Scheduled" | "Temporary" | "Hold
        value: float | None = None,
        next_time: dt | None = None,  # "%Y-%m-%dT%H:%M:%SZ"
    ) -> None:
        """Set zone setpoint, either indefinitely, or until a set time."""

        zone: _EvoDictT = await self._get_zone(zone_id)

        if next_time is None:
            data = {"Status": "Hold", "Value": value}
        else:
            data = {
                "Status": status,
                "Value": value,
                "NextTime": next_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        url = f"/devices/{zone['deviceID']}/thermostat/changeableValues/heatSetpoint"
        await self.broker._request(HTTPMethod.PUT, url, data=data)

    async def set_temperature(
        self, zone: _ZoneNameT, temperature, until: dt | None = None
    ) -> None:
        """Override the setpoint of a zone, for a period of time, or indefinitely."""

        if until:
            await self._set_heat_setpoint(
                zone, "Temporary", value=temperature, next_time=until
            )
        else:
            await self._set_heat_setpoint(zone, "Hold", value=temperature)

    async def cancel_temp_override(self, zone: _ZoneNameT) -> None:  # DEPRECATED
        return await self.set_zone_auto(zone)

    async def set_zone_auto(self, zone: _ZoneNameT) -> None:
        """Set a zone to follow its schedule."""
        await self._set_heat_setpoint(zone, status="Scheduled")

    # DHW methods...

    async def _get_dhw(self) -> _FullDataT:
        """Return the locations's DHW, if there is one (if needed, get the JSON).

        Raise an exception if the DHW is not found.
        """

        # just want id, so retrieve the config data only if we don't already have it
        await self._populate_full_data(force_refresh=False)

        for device in self.full_data["devices"]:
            if device["thermostatModelType"] == "DOMESTIC_HOT_WATER":
                return device

        raise InvalidSchema(f"No DHW in location {self.location_id}")

    async def _set_dhw(
        self,
        status: str,  # "Scheduled" | "Hold"
        mode: str | None = None,  # "DHWOn" | "DHWOff
        next_time: dt | None = None,  # "%Y-%m-%dT%H:%M:%SZ"
    ) -> None:
        """Set DHW to Auto, or On/Off, either indefinitely, or until a set time."""

        dhw: _EvoDictT = await self._get_dhw()
        dhw_id = dhw["deviceID"]

        data = {
            "Status": status,
            "Mode": mode,  # "NextTime": None,
            # "SpecialModes": None, "HeatSetpoint": None, "CoolSetpoint": None,
        }
        if next_time:
            data |= {"NextTime": next_time.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"/devices/{dhw_id}/thermostat/changeableValues"
        await self.broker._request(HTTPMethod.PUT, url, data=data)

    async def set_dhw_on(self, until: dt | None = None) -> None:
        """Set DHW to On, either indefinitely, or until a specified time.

        When On, the DHW controller will work to keep its target temperature at/above
        its target temperature.  After the specified time, it will revert to its
        scheduled behaviour.
        """

        await self._set_dhw(status="Hold", mode="DHWOn", next_time=until)

    async def set_dhw_off(self, until: dt | None = None) -> None:
        """Set DHW to Off, either indefinitely, or until a specified time.

        When Off, the DHW controller will ignore its target temperature. After the
        specified time, it will revert to its scheduled behaviour.
        """

        await self._set_dhw(status="Hold", mode="DHWOff", next_time=until)

    async def set_dhw_auto(self) -> None:
        """Allow DHW to switch between On and Off, according to its schedule."""
        await self._set_dhw(status="Scheduled")
