#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
import logging
from datetime import datetime, timedelta

import aiohttp

from .location import Location

HTTP_UNAUTHORIZED = 401

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)

HEADER_ACCEPT = (
    "application/json, application/xml, text/json, text/x-json, "
    "text/javascript, text/xml"
)
HEADER_AUTHORIZATION_BASIC = (
    "Basic "
    "NGEyMzEwODktZDJiNi00MWJkLWE1ZWItMTZhMGE0MjJiOTk5OjFhMTVjZGI4LTQyZGUtNDA3Y"
    "i1hZGQwLTA1OWY5MmM1MzBjYg=="
)
HEADER_BASIC_AUTH = {
    "Accept": HEADER_ACCEPT,
    "Authorization": HEADER_AUTHORIZATION_BASIC,
}


class AuthenticationError(Exception):
    """Exception raised when unable to get an access_token."""

    def __init__(self, message):
        """Construct the AuthenticationError object."""
        self.message = message
        super(AuthenticationError, self).__init__(message)


class EvohomeClient(object):
    """Provide access to the v2 Evohome API."""

    def __init__(self, username, password, **kwargs):
        """Construct the EvohomeClient object."""
        if kwargs.get("debug") is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")
        else:
            _LOGGER.debug(
                "Debug mode is not explicitly enabled (but may be enabled elsewhere)."
            )

        self.username = username
        self.password = password

        self.refresh_token = kwargs.get("refresh_token")
        self.access_token = kwargs.get("access_token")
        self.access_token_expires = kwargs.get("access_token_expires")

        self._session = kwargs.get("session") or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        self.account_info = None
        self.locations = None
        self.installation_info = None
        self.system_id = None

    async def login(self):
        """Authenticate with the server."""
        try:  # the cached access_token may be valid, but is not authorized
            await self.user_account()
        except aiohttp.ClientResponseError as err:
            if err.status != HTTP_UNAUTHORIZED or not self.access_token:
                raise

            _LOGGER.warning("Unauthorized access_token (will try re-authenticating).")
            self.access_token = None
            await self.user_account()

        await self.installation()

    async def _headers(self):
        """Ensure the Authorization Header has a valid Access Token."""
        if not self.access_token or not self.access_token_expires:
            await self._basic_login()

        elif datetime.now() > self.access_token_expires - timedelta(seconds=30):
            await self._basic_login()

        return {"Accept": HEADER_ACCEPT, "Authorization": "bearer " + self.access_token}

    async def _basic_login(self):
        """Obtain a new access token from the vendor.

        First, try using the refresh_token, if one is available, otherwise
        authenticate using the user credentials.
        """
        _LOGGER.debug("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = self.access_token_expires = None

        if self.refresh_token:
            _LOGGER.debug("Authenticating with the refresh_token...")
            credentials = {
                "grant_type": "refresh_token",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
                "refresh_token": self.refresh_token,
            }

            try:
                await self._obtain_access_token(credentials)
            except AuthenticationError:
                _LOGGER.warning("Invalid refresh_token (will try user credentials).")
                self.refresh_token = None

        if not self.refresh_token:
            _LOGGER.debug("Authenticating with the user credentials...")
            credentials = {
                "grant_type": "password",
                "scope": "EMEA-V1-Basic EMEA-V1-Anonymous "
                "EMEA-V1-Get-Current-User-Account",
                "Username": self.username,
                "Password": self.password,
            }

            await self._obtain_access_token(credentials)

        _LOGGER.debug("refresh_token = %s", self.refresh_token)
        _LOGGER.debug("access_token = %s", self.access_token)
        _LOGGER.debug(
            "access_token_expires = %s",
            self.access_token_expires.strftime("%Y-%m-%d %H:%M:%S"),
        )

    async def _obtain_access_token(self, credentials):
        url = "https://tccna.honeywell.com/Auth/OAuth/Token"
        payload = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Host": "rs.alarmnet.com/",
            "Cache-Control": "no-store no-cache",
            "Pragma": "no-cache",
            "Connection": "Keep-Alive",
        }
        payload.update(credentials)  # merge the credentials into the payload

        async with self._session.post(
            url,
            data=payload,
            headers=HEADER_BASIC_AUTH,
        ) as response:
            try:
                response_text = await response.text()
                response.raise_for_status()

            except aiohttp.ClientResponseError:
                msg = "Unable to obtain an Access Token"
                if response_text:  # if there is a message, then raise with it
                    msg = msg + ", hint: " + response_text

                raise AuthenticationError(msg)

            try:  # the access token _should_ be valid...
                # this may cause a ValueError
                response_json = await response.json()

                # these may cause a KeyError
                self.access_token = response_json["access_token"]
                self.access_token_expires = datetime.now() + timedelta(
                    seconds=response_json["expires_in"]
                )
                self.refresh_token = response_json["refresh_token"]

            except KeyError:
                raise AuthenticationError(
                    "Unable to obtain an Access Token, hint: " + response_json
                )

            except ValueError:
                raise AuthenticationError(
                    "Unable to obtain an Access Token, hint: " + response_text
                )

    def _get_location(self, location):
        if location is None:
            return self.installation_info[0]["locationInfo"]["locationId"]
        return location

    def _get_single_heating_system(self):
        # This allows a shortcut for some systems
        if len(self.locations) != 1:
            raise Exception("More (or less) than one location available")

        if len(self.locations[0]._gateways) != 1:
            raise Exception("More (or less) than one gateway available")

        if len(self.locations[0]._gateways[0]._control_systems) != 1:
            raise Exception("More (or less) than one control system available")

        return self.locations[0]._gateways[0]._control_systems[0]

    async def user_account(self):
        """Return the user account information."""
        self.account_info = None

        url = "https://tccna.honeywell.com/WebAPI/emea/api/v1/userAccount"

        async with self._session.get(url, headers=await self._headers()) as response:
            response.raise_for_status()

            self.account_info = await response.json()
            return self.account_info

    async def installation(self):
        """Return the details of the installation."""
        self.locations = []

        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1/location"
            "/installationInfo?userId=%s&includeTemperatureControlSystems=True"
            % self.account_info["userId"]
        )

        async with self._session.get(url, headers=await self._headers()) as response:
            response.raise_for_status()

            self.installation_info = await response.json()

        self.system_id = self.installation_info[0]["gateways"][0][
            "temperatureControlSystems"
        ][0]["systemId"]

        for loc_data in self.installation_info:
            location = Location(self, loc_data)
            await location.status()
            self.locations.append(location)

        return self.installation_info

    async def full_installation(self, location=None):
        """Return the full details of the installation."""
        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1/location"
            "/%s/installationInfo?includeTemperatureControlSystems=True"
            % self._get_location(location)
        )

        async with self._session.get(url, headers=await self._headers()) as response:
            response.raise_for_status()

            return await response.json()

    async def gateway(self):
        """Return the details of the gateway."""
        url = "https://tccna.honeywell.com/WebAPI/emea/api/v1/gateway"

        async with self._session.get(url, headers=await self._headers()) as response:
            response.raise_for_status()

            return await response.json()

    async def set_status_normal(self):
        """Set the system into normal heating mode."""
        return await self._get_single_heating_system().set_status_normal()

    async def set_status_reset(self):
        """Reset the system mode."""
        return await self._get_single_heating_system().set_status_reset()

    async def set_status_custom(self, until=None):
        """Set the system into custom heating mode."""
        return await self._get_single_heating_system().set_status_custom(until)

    async def set_status_eco(self, until=None):
        """Set the system into eco heating mode."""
        return await self._get_single_heating_system().set_status_eco(until)

    async def set_status_away(self, until=None):
        """Set the system into away heating mode."""
        return await self._get_single_heating_system().set_status_away(until)

    async def set_status_dayoff(self, until=None):
        """Set the system into day off heating mode."""
        return await self._get_single_heating_system().set_status_dayoff(until)

    async def set_status_heatingoff(self, until=None):
        """Set the system into heating off heating mode."""
        return await self._get_single_heating_system().set_status_heatingoff(until)

    async def temperatures(self):
        """Return the current zone temperatures and set points."""
        return await self._get_single_heating_system().temperatures()

    def zone_schedules_backup(self, filename):
        """Back up the current system configuration to the given file."""
        return self._get_single_heating_system().zone_schedules_backup(filename)

    def zone_schedules_restore(self, filename):
        """Restore the current system configuration from the given file."""
        return self._get_single_heating_system().zone_schedules_restore(filename)
