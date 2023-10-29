#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

import asyncio
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
import json
import logging
from typing import TYPE_CHECKING, Any, NoReturn

import aiohttp

from .exceptions import (
    AuthenticationFailed,
    InvalidSchema,
    RateLimitExceeded,
    RequestFailed,
)


if TYPE_CHECKING:
    from .schema import (
        _DeviceIdT,
        _EvoDictT,
        _EvoListT,
        _LocationIdT,
        _SystemModeT,
        _TaskIdT,
        _ZoneIdT,
    )


_LOGGER = logging.getLogger(__name__)


class EvohomeClientDeprecated:  # NOTE: incl. _wait_for_put_task()
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    hostname: str

    async def _wait_for_put_task(self, response: aiohttp.ClientResponse) -> None:
        """This functionality is deprecated, but remains here as documentation."""

        async def get_task_status(task_id: _TaskIdT) -> str:
            await self._populate_full_data()
            url = self.hostname + f"/WebAPI/api/commTasks?commTaskId={task_id}"

            response = await self._do_request(HTTPMethod.GET, url)
            return dict(await response.json())["state"]

        task_id: _TaskIdT

        assert response.method == HTTPMethod.PUT

        ret = await response.json()
        task_id = ret[0]["id"] if isinstance(ret, list) else ret["id"]

        # FIXME: could wait forvever?
        while await get_task_status(task_id) != "Succeeded":
            await asyncio.sleep(1)

    async def _do_request(self, *args, **kwargs) -> aiohttp.ClientResponse:
        raise NotImplementedError

    async def _populate_full_data(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def get_system_modes(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.get_modes() is deprecated, "
            "use .get_system_modes() or .get_zone_modes()"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_away() is deprecated, use .set_mode_away()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_custom() is deprecated, use .set_mode_custom()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_dayoff() is deprecated, use .set_mode_dayoff()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_eco() is deprecated, use .set_mode_eco()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_heatingoff() is deprecated, use .set_mode_heatingoff()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "EvohomeClient.set_status_normal() is deprecated, use .set_mode_auto()"
        )


class EvohomeClient(EvohomeClientDeprecated):
    """Provide a client to access the Honeywell TCC API (assumes a single TCS)."""

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        user_data: dict[str, str] | None = None,
        **kwargs,
    ) -> None:
        """Construct the v1 EvohomeClient object.

        If user_data is given then this will be used to try and reduce the number of
        calls to the authentication service which is known to be rate limited.
        """
        if kwargs.get("debug"):
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")

        self.username = username
        self.password = password

        self.user_data: dict[str, str] | None = user_data
        self.hostname: str = kwargs.get("hostname", "https://tccna.honeywell.com")

        self._session = kwargs.get("session") or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        self.full_data: _EvoDictT = None  # type: ignore[assignment]
        self.location_id: _LocationIdT = None  # type: ignore[assignment]

        self.devices: _EvoDictT = {}
        self.named_devices: _EvoDictT = {}

        self.postdata: dict[str, Any] = {}
        self.headers: dict[str, Any] = {}

    async def _do_request(
        self,
        method: HTTPMethod,
        url: str,
        /,
        *,
        data: str | None = None,
        retry: bool = True,
    ) -> aiohttp.ClientResponse:
        """Perform an HTTP request, with optional retry (usu. for authentication)."""

        if method == HTTPMethod.GET:
            func = self._session.get
        elif method == HTTPMethod.PUT:
            func = self._session.put
        elif method == HTTPMethod.POST:
            func = self._session.post

        async with func(url, data=data, headers=self.headers) as response:
            response_text = await response.text()

            # if 401/unauthorized, attempt to refresh sessionId if it has expired
            if response.status == HTTPStatus.UNAUTHORIZED and retry is True:
                if "code" in response_text:  # don't use .json() yet: may be plain text
                    response_json = await response.json()

                    if response_json[0]["code"] == "Unauthorized":
                        _LOGGER.debug("Session expired, re-authenticating...")

                        # Get a fresh (= None) sessionId (self.user_data)
                        self.user_data = None
                        await self._populate_user_info()

                        # Set headers with the new sessionId
                        session_id = self.user_data["sessionId"]  # type: ignore[index]
                        self.headers["sessionId"] = session_id
                        _LOGGER.debug(f"sessionId = {session_id}")

                        response = await self._do_request(
                            method, url, data=data, retry=False
                        )  # NOTE: this is a recursive call

            # if not 200/OK, display (useful?) error message if the vendor provided one
            if response.status != HTTPStatus.OK:
                if "code" in response_text:  # don't use .json(): may be plain text
                    _LOGGER.warning(
                        f"HTTP Status = {response.status}, Response = {response_text}",
                    )

            try:
                response.raise_for_status()
            except aiohttp.ClientResponseError as exc:
                if method == HTTPMethod.POST:
                    raise AuthenticationFailed(str(exc))
                if response.status != HTTPStatus.TOO_MANY_REQUESTS:
                    raise RateLimitExceeded(str(exc))
                raise RequestFailed(str(exc))

        return response

    async def _populate_full_data(self, force_refresh: bool = False) -> None:
        """"""

        if self.full_data is None or force_refresh:
            await self._populate_user_info()

            user_id = self.user_data["userInfo"]["userID"]  # type: ignore[index]
            session_id = self.user_data["sessionId"]  # type: ignore[index]

            url = self.hostname + f"/WebAPI/api/locations?userId={user_id}&allData=True"
            self.headers["sessionId"] = session_id

            response = await self._do_request(
                HTTPMethod.GET, url, data=json.dumps(self.postdata)
            )

            self.full_data = list(await response.json())[0]
            self.location_id = self.full_data["locationID"]

            self.devices = {}
            self.named_devices = {}

            for device in self.full_data["devices"]:
                self.devices[device["deviceID"]] = device
                self.named_devices[device["name"]] = device

    async def _populate_user_info(self) -> _EvoDictT:
        """"""

        if self.user_data is None:
            url = self.hostname + "/WebAPI/api/Session"
            self.postdata = {
                "Username": self.username,
                "Password": self.password,
                "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
            }
            self.headers = {"content-type": "application/json"}

            response = await self._do_request(
                HTTPMethod.POST, url, data=json.dumps(self.postdata), retry=False
            )
            self.user_data = await response.json()

        assert isinstance(self.user_data, dict)  # mypy
        return self.user_data

    async def temperatures(self, force_refresh: bool = False) -> _EvoListT:
        """Retrieve the current details for each zone."""

        set_point: float
        status: str

        await self._populate_full_data(force_refresh)

        result = []

        try:
            for device in self.full_data["devices"]:
                if "heatSetpoint" in device["thermostat"]["changeableValues"]:
                    set_point = float(
                        device["thermostat"]["changeableValues"]["heatSetpoint"][
                            "value"
                        ]
                    )
                    status = device["thermostat"]["changeableValues"]["heatSetpoint"][
                        "status"
                    ]

                else:
                    set_point = 0
                    status = device["thermostat"]["changeableValues"]["status"]
                result.append(
                    {
                        "thermostat": device["thermostatModelType"],
                        "id": device["deviceID"],
                        "name": device["name"],
                        "temp": float(device["thermostat"]["indoorTemperature"]),
                        "setpoint": set_point,
                        "status": status,
                        "mode": device["thermostat"]["changeableValues"]["mode"],
                    }
                )

        # harden code against unexpected schema (JSON structure)
        except (LookupError, TypeError, ValueError) as exc:
            raise InvalidSchema(str(exc))
        return result

    async def get_system_modes(self) -> NoReturn:
        """Return the set of modes the system can be assigned."""
        raise NotImplementedError

    async def _set_system_mode(
        self, status: _SystemModeT, until: None | dt = None
    ) -> None:
        """Set the system mode."""

        await self._populate_full_data()
        url = (
            self.hostname + f"/WebAPI/api/evoTouchSystems?locationId={self.location_id}"
        )

        if until is None:
            data = {"QuickAction": status, "QuickActionNextTime": None}
        else:
            data = {
                "QuickAction": status,
                "QuickActionNextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._do_request(HTTPMethod.PUT, url, data=json.dumps(data))

    async def set_mode_auto(self) -> None:
        """Set the system to normal operation."""
        await self._set_system_mode("Auto")

    async def set_mode_away(self, until: None | dt = None) -> None:
        """Set the system to the away mode."""
        await self._set_system_mode("Away", until)

    async def set_mode_custom(self, until: None | dt = None) -> None:
        """Set the system to the custom programme."""
        await self._set_system_mode("Custom", until)

    async def set_mode_dayoff(self, until: None | dt = None) -> None:
        """Set the system to the day off mode."""
        await self._set_system_mode("DayOff", until)

    async def set_mode_eco(self, until: None | dt = None) -> None:
        """Set the system to the eco mode."""
        await self._set_system_mode("AutoWithEco", until)

    async def set_mode_heatingoff(self, until: None | dt = None) -> None:
        """Set the system to the heating off mode."""
        await self._set_system_mode("HeatingOff", until)

    async def get_zone_modes(self, zone) -> list[str]:
        """Return the set of modes the zone can be assigned."""
        await self._populate_full_data()
        device = self._get_device(zone)
        return device["thermostat"]["allowedModes"]

    def _get_device(self, zone: str) -> _EvoDictT:
        """"""

        if isinstance(zone, str):
            return self.named_devices[zone]
        return self.devices[zone]  # TODO: no need for str.isnumeric() check?

    def _get_device_id(self, device_id: _DeviceIdT) -> _DeviceIdT:
        """"""

        device = self._get_device(device_id)
        return device["deviceID"]

    async def _set_heat_setpoint(self, zone, data: _EvoDictT) -> None:
        """"""

        await self._populate_full_data()
        zone_id: _ZoneIdT = self._get_device_id(zone)

        url = (
            self.hostname
            + f"/WebAPI/api/devices/{zone_id}/thermostat/changeableValues/heatSetpoint"
        )

        await self._do_request(HTTPMethod.PUT, url, data=json.dumps(data))

    async def set_temperature(self, zone, temperature, until: None | dt = None) -> None:
        """Set the temperature of the given zone."""

        if until is None:
            data = {"Value": temperature, "Status": "Hold", "NextTime": None}
        else:
            data = {
                "Value": temperature,
                "Status": "Temporary",
                "NextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_heat_setpoint(zone, data)

    async def cancel_temp_override(self, zone) -> None:
        """Remove an existing temperature override."""

        data = {"Value": None, "Status": "Scheduled", "NextTime": None}
        await self._set_heat_setpoint(zone, data)

    def _get_dhw_zone(self) -> str | None:
        for device in self.full_data["devices"]:
            if device["thermostatModelType"] == "DOMESTIC_HOT_WATER":
                return device["deviceID"]
        return None

    async def _set_dhw(
        self,
        status: str = "Scheduled",
        mode: str | None = None,
        next_time: str | None = None,
    ) -> None:
        """Set DHW to On, Off or Auto, either indefinitely, or until a set time."""

        data = {
            "Status": status,
            "Mode": mode,
            "NextTime": next_time,
            "SpecialModes": None,
            "HeatSetpoint": None,
            "CoolSetpoint": None,
        }

        await self._populate_full_data()
        dhw_id = self._get_dhw_zone()

        if dhw_id is None:
            raise InvalidSchema("No DHW zone reported from API")
        url = (
            self.hostname + f"/WebAPI/api/devices/{dhw_id}/thermostat/changeableValues"
        )

        await self._do_request(HTTPMethod.PUT, url, data=json.dumps(data))

    async def set_dhw_on(self, until: None | dt = None) -> None:
        """Set DHW to on, either indefinitely, or until a specified time.

        When On, the DHW controller will work to keep its target temperature at/above
        its target temperature.  After the specified time, it will revert to its
        scheduled behaviour.
        """

        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOn", next_time=time_until)

    async def set_dhw_off(self, until: None | dt = None) -> None:
        """Set DHW to on, either indefinitely, or until a specified time.

        When Off, the DHW controller will ignore its target temperature. After the
        specified time, it will revert to its scheduled behaviour.
        """

        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOff", next_time=time_until)

    async def set_dhw_auto(self) -> None:
        """Set DHW to On or Off, according to its schedule."""
        await self._set_dhw(status="Scheduled")
