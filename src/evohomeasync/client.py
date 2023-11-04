#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API."""
from __future__ import annotations

import asyncio
from datetime import datetime as dt
from http import HTTPMethod, HTTPStatus
import logging
from typing import TYPE_CHECKING, Any, Callable, NoReturn

import aiohttp

from .exceptions import (
    AuthenticationFailed,
    DeprecationError,
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

    # Note deprecated, just a placeholder for self.get_task_status()
    async def _do_request(self, *args, **kwargs) -> aiohttp.ClientResponse:
        raise DeprecationError

    # Note deprecated, just a placeholder for self.get_task_status()
    async def _populate_full_data(self, *args, **kwargs) -> None:
        raise DeprecationError

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
        data: dict | None = None,
        retry: bool = True,
    ) -> aiohttp.ClientResponse:
        """Perform an HTTP request, with optional retry (usu. for authentication)."""

        url = self.hostname + "/WebAPI/api" + url

        if method == HTTPMethod.GET:
            func = self._session.get
        elif method == HTTPMethod.PUT:
            func = self._session.put
        elif method == HTTPMethod.POST:
            func = self._session.post

        try:
            response = await self._do_request_base(func, url, data=data, retry=retry)

        except aiohttp.ClientError as exc:
            if method == HTTPMethod.POST:  # using response will cause UnboundLocalError
                raise AuthenticationFailed(str(exc))
            raise RequestFailed(str(exc))

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as exc:
            if response.method == HTTPMethod.POST:  # POST only used when authenticating
                raise AuthenticationFailed(str(exc), status=exc.status)
            if response.status != HTTPStatus.TOO_MANY_REQUESTS:
                raise RateLimitExceeded(str(exc), status=exc.status)
            raise RequestFailed(str(exc), status=exc.status)

        except aiohttp.ClientError as exc:
            if response.method == HTTPMethod.POST:  # POST only used when authenticating
                raise AuthenticationFailed(str(exc))
            raise RequestFailed(str(exc))

        return response

    async def _do_request_base(
        self,
        func: Callable,
        url: str,
        /,
        *,
        data: dict | None = None,
        retry: bool = True,
    ) -> aiohttp.ClientResponse:
        """Perform an HTTP request, with optional retry (usu. for authentication)."""

        response: aiohttp.ClientResponse

        async with func(url, json=data, headers=self.headers) as response:  # NB: json=
            response_text = await response.text()  # why cant I move this below the if?

            # if 401/unauthorized, may need to refresh sessionId
            if response.status != HTTPStatus.UNAUTHORIZED or not retry:
                return response

            # TODO: use response.content_type to determine whether to use .json()
            if "code" not in response_text:  # don't use .json() yet: may be plain text
                return response

            response_json = await response.json()
            if response_json[0]["code"] != "Unauthorized":
                return response

            _LOGGER.debug("Session expired/invalid, re-authenticating...")
            self.user_data = None  # Get a fresh (= None) sessionId
            await self._populate_user_data()

            session_id = self.user_data["sessionId"]  # type: ignore[index]
            self.headers["sessionId"] = session_id
            _LOGGER.debug(f"... Success: sessionId = {session_id}")

            # NOTE: this is a recursive call, used only after re-authenticating
            response = await self._do_request_base(func, url, data=data, retry=False)

        return response

    async def _populate_user_data(self) -> _EvoDictT:
        """Retrieve all the user data from the web."""

        if self.user_data is None:
            self.postdata = {
                "Username": self.username,
                "Password": self.password,
                "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
            }
            self.headers = {"content-type": "application/json"}

            url = "/Session"
            response = await self._do_request(
                HTTPMethod.POST, url, data=self.postdata, retry=False
            )

            self.user_data = await response.json()

        assert isinstance(self.user_data, dict)  # mypy
        return self.user_data

    async def _populate_full_data(self, force_refresh: bool = False) -> None:
        """Retrieve all the system data from the web."""

        if self.full_data is None or force_refresh:
            await self._populate_user_data()

            self.headers["sessionId"] = self.user_data["sessionId"]  # type: ignore[index]
            user_id = self.user_data["userInfo"]["userID"]  # type: ignore[index]

            url = f"/locations?userId={user_id}&allData=True"
            response = await self._do_request(HTTPMethod.GET, url, data=self.postdata)

            self.full_data = list(await response.json())[0]
            self.location_id = self.full_data["locationID"]

            self.devices = {}
            self.named_devices = {}

            for device in self.full_data["devices"]:
                self.devices[device["deviceID"]] = device
                self.named_devices[device["name"]] = device

    async def temperatures(self, force_refresh: bool = False) -> _EvoListT:
        """Retrieve the current details for each zone (incl. DHW)."""

        set_point: float
        status: str

        await self._populate_full_data(force_refresh=force_refresh)

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
            raise InvalidSchema(str(exc))
        return result

    async def get_system_modes(self) -> NoReturn:
        """Return the set of modes the system can be assigned."""
        raise NotImplementedError

    async def _set_system_mode(
        self, status: _SystemModeT, until: dt | None = None
    ) -> None:
        """Set the system mode."""

        await self._populate_full_data()

        data: dict[str, str | None] = {"QuickAction": status}
        if until is None:
            data |= {"QuickActionNextTime": None}
        else:
            data |= {"QuickActionNextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ")}

        url = f"/evoTouchSystems?locationId={self.location_id}"
        await self._do_request(HTTPMethod.PUT, url, data=data)

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

        url = f"/devices/{zone_id}/thermostat/changeableValues/heatSetpoint"
        await self._do_request(HTTPMethod.PUT, url, data=data)

    async def set_temperature(self, zone, temperature, until: dt | None = None) -> None:
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

        await self._populate_full_data()

        dhw_id = self._get_dhw_zone()
        if dhw_id is None:
            raise InvalidSchema("No DHW zone reported from API")

        data = {
            "Status": status,
            "Mode": mode,
            "NextTime": next_time,
            "SpecialModes": None,
            "HeatSetpoint": None,
            "CoolSetpoint": None,
        }

        url = f"/devices/{dhw_id}/thermostat/changeableValues"
        await self._do_request(HTTPMethod.PUT, url, data=data)

    async def set_dhw_on(self, until: dt | None = None) -> None:
        """Set DHW to on, either indefinitely, or until a specified time.

        When On, the DHW controller will work to keep its target temperature at/above
        its target temperature.  After the specified time, it will revert to its
        scheduled behaviour.
        """

        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOn", next_time=time_until)

    async def set_dhw_off(self, until: dt | None = None) -> None:
        """Set DHW to on, either indefinitely, or until a specified time.

        When Off, the DHW controller will ignore its target temperature. After the
        specified time, it will revert to its scheduled behaviour.
        """

        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOff", next_time=time_until)

    async def set_dhw_auto(self) -> None:
        """Set DHW to On or Off, according to its schedule."""
        await self._set_dhw(status="Scheduled")
