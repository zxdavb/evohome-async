#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the oiginal Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
import json
import logging
import time

import aiohttp

HTTP_UNAUTHORIZED = 401
HTTP_OK = 200

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)


class EvohomeClient(object):
    """Provide a client to access the Honeywell Evohome system."""

    def __init__(self, username, password, user_data=None, **kwargs):
        """Take the username and password for the service.

        If user_data is given then this will be used to try and reduce the number of
        calls to the authentication service which is known to be rate limited.
        """
        if kwargs.get("debug") is True:  # if debug is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")
        else:
            _LOGGER.debug(
                "Debug mode is not explicitly enabled (but may be enabled elsewhere)."
            )

        self.username = username
        self.password = password

        self.user_data = user_data
        self.hostname = kwargs.get("hostname", "https://tccna.honeywell.com")

        self._session = kwargs.get("session") or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        self.full_data = None
        self.gateway_data = None

        self.location_id = ""
        self.devices = {}
        self.named_devices = {}
        self.postdata = {}
        self.headers = {}

    async def _populate_full_data(self, force_refresh=False):
        if self.full_data is None or force_refresh:
            await self._populate_user_info()

            user_id = self.user_data["userInfo"]["userID"]
            session_id = self.user_data["sessionId"]

            url = (
                self.hostname + "/WebAPI/api/locations?userId=%s&allData=True" % user_id
            )
            self.headers["sessionId"] = session_id

            response = await self._do_request("get", url, json.dumps(self.postdata))

            self.full_data = list(await response.json())[0]

            self.location_id = self.full_data["locationID"]

            self.devices = {}
            self.named_devices = {}

            for device in self.full_data["devices"]:
                self.devices[device["deviceID"]] = device
                self.named_devices[device["name"]] = device

    async def _populate_user_info(self):
        if self.user_data is None:
            url = self.hostname + "/WebAPI/api/Session"
            self.postdata = {
                "Username": self.username,
                "Password": self.password,
                "ApplicationId": "91db1612-73fd-4500-91b2-e63b069b185c",
            }
            self.headers = {"content-type": "application/json"}

            response = await self._do_request(
                "post", url, data=json.dumps(self.postdata), retry=False
            )

            self.user_data = await response.json()

        return self.user_data

    async def temperatures(self, force_refresh=False):
        """Retrieve the current details for each zone."""
        await self._populate_full_data(force_refresh)

        result = []
        for device in self.full_data["devices"]:
            set_point = 0
            status = ""
            if "heatSetpoint" in device["thermostat"]["changeableValues"]:
                set_point = float(
                    device["thermostat"]["changeableValues"]["heatSetpoint"]["value"]
                )
                status = device["thermostat"]["changeableValues"]["heatSetpoint"][
                    "status"
                ]

            else:
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

        return result

    async def get_modes(self, zone):
        """Return the set of modes the device can be assigned."""
        await self._populate_full_data()
        device = self._get_device(zone)
        return device["thermostat"]["allowedModes"]

    def _get_device(self, zone):
        if isinstance(zone, str):
            return self.named_devices[zone]
        return self.devices[zone]

    async def _get_task_status(self, task_id):
        await self._populate_full_data()
        url = self.hostname + "/WebAPI/api/commTasks?commTaskId=%s" % task_id

        response = await self._do_request("get", url)

        return dict(await response.json())["state"]

    async def _get_task_id(self, response):
        ret = await response.json()
        return ret[0]["id"] if isinstance(ret, list) else ret["id"]

    async def _do_request(self, method, url, data=None, retry=True):
        if method == "get":
            func = self._session.get
        elif method == "put":
            func = self._session.put
        elif method == "post":
            func = self._session.post

        async with func(url, data=data, headers=self.headers) as response:
            response_text = await response.text()

            # catch 401/unauthorized since we may retry
            if response.status == HTTP_UNAUTHORIZED and retry is True:
                # Attempt to refresh sessionId if it has expired
                if "code" in response_text:  # don't use response.json() here!
                    response_json = await response.json()
                    if response_json[0]["code"] == "Unauthorized":
                        _LOGGER.debug("Session expired, re-authenticating...")
                        # Get a new sessionId
                        self.user_data = None
                        await self._populate_user_info()
                        # Set headers with new sessionId
                        session_id = self.user_data["sessionId"]
                        self.headers["sessionId"] = session_id
                        _LOGGER.debug("sessionId = %s", session_id)

                        response = await self._do_request(
                            method, url, data=data, retry=False
                        )

            # display error message if the vendor provided one
            if response.status != HTTP_OK:
                if "code" in response_text:  # don't use response.json()!
                    _LOGGER.error(
                        "HTTP Status = %s, Response = %s",
                        response.status,
                        response_text,
                    )

            response.raise_for_status()

        return response

    async def _set_status(self, status, until=None):
        await self._populate_full_data()
        url = (
            self.hostname
            + "/WebAPI/api/evoTouchSystems?locationId=%s" % self.location_id
        )

        if until is None:
            data = {"QuickAction": status, "QuickActionNextTime": None}
        else:
            data = {
                "QuickAction": status,
                "QuickActionNextTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        response = await self._do_request("put", url, json.dumps(data))

        task_id = await self._get_task_id(response)

        while await self._get_task_status(task_id) != "Succeeded":
            time.sleep(1)

    async def set_status_normal(self):
        """Set the system to normal operation."""
        await self._set_status("Auto")

    async def set_status_custom(self, until=None):
        """Set the system to the custom programme."""
        await self._set_status("Custom", until)

    async def set_status_eco(self, until=None):
        """Set the system to the eco mode."""
        await self._set_status("AutoWithEco", until)

    async def set_status_away(self, until=None):
        """Set the system to the away mode."""
        await self._set_status("Away", until)

    async def set_status_dayoff(self, until=None):
        """Set the system to the day off mode."""
        await self._set_status("DayOff", until)

    async def set_status_heatingoff(self, until=None):
        """Set the system to the heating off mode."""
        await self._set_status("HeatingOff", until)

    def _get_device_id(self, zone):
        device = self._get_device(zone)
        return device["deviceID"]

    async def _set_heat_setpoint(self, zone, data):
        await self._populate_full_data()

        device_id = self._get_device_id(zone)

        url = (
            self.hostname
            + "/WebAPI/api/devices/%s/thermostat/changeableValues/heatSetpoint"
            % device_id
        )

        response = await self._do_request("put", url, json.dumps(data))

        task_id = await self._get_task_id(response)

        while await self._get_task_status(task_id) != "Succeeded":
            time.sleep(1)

    async def set_temperature(self, zone, temperature, until=None):
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

    async def cancel_temp_override(self, zone):
        """Remove an existing temperature override."""
        data = {"Value": None, "Status": "Scheduled", "NextTime": None}
        await self._set_heat_setpoint(zone, data)

    def _get_dhw_zone(self):
        for device in self.full_data["devices"]:
            if device["thermostatModelType"] == "DOMESTIC_HOT_WATER":
                return device["deviceID"]

    async def _set_dhw(self, status="Scheduled", mode=None, next_time=None):
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
        dhw_zone = self._get_dhw_zone()
        if dhw_zone is None:
            raise Exception("No DHW zone reported from API")
        url = (
            self.hostname
            + "/WebAPI/api/devices/%s/thermostat/changeableValues" % dhw_zone
        )

        response = await self._do_request("put", url, json.dumps(data))

        task_id = await self._get_task_id(response)

        while await self._get_task_status(task_id) != "Succeeded":
            time.sleep(1)

    async def set_dhw_on(self, until=None):
        """Set DHW to on, either indefinitely, or until a specified time.

        When On, the DHW controller will work to keep its target temperature at/above
        its target temperature.  After the specified time, it will revert to its
        scheduled behaviour.
        """
        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOn", next_time=time_until)

    async def set_dhw_off(self, until=None):
        """Set DHW to on, either indefinitely, or until a specified time.

        When Off, the DHW controller will ignore its target temperature. After the
        specified time, it will revert to its scheduled behaviour.
        """
        time_until = None if until is None else until.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._set_dhw(status="Hold", mode="DHWOff", next_time=time_until)

    async def set_dhw_auto(self):
        """Set DHW to On or Off, according to its schedule."""
        await self._set_dhw(status="Scheduled")
