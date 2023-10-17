#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
from __future__ import annotations

import logging
from datetime import datetime as dt
from datetime import timedelta as td
from typing import TYPE_CHECKING, NoReturn

import aiohttp

# from .tests.mock import aiohttp

from .exceptions import AuthenticationError, SingleTcsError
from .exceptions import InvalidSchedule  # noqa: F401
from .const import (
    AUTH_HEADER_ACCEPT,
    AUTH_HEADER,
    AUTH_URL,
    URL_BASE,
    AUTH_PAYLOAD,
    CREDS_REFRESH_TOKEN,
    CREDS_USER_PASSWORD,
)
from .controlsystem import ControlSystem
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location
from .zone import ZoneBase, Zone  # noqa: F401

if TYPE_CHECKING:
    from .typing import _FilePathT, _LocationIdT, _SystemIdT


HTTP_UNAUTHORIZED = 401

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)


class EvohomeClient:
    """Provide access to the v2 Evohome API."""

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        debug: bool = False,
        refresh_token: None | str = None,
        access_token: None | str = None,
        access_token_expires: None | dt = None,
        session: None | aiohttp.ClientSession = None,
    ) -> None:
        """Construct the EvohomeClient object."""

        if debug:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")
        else:
            _LOGGER.debug(
                "Debug mode is not explicitly enabled (but may be enabled elsewhere)."
            )

        self.username = username
        self.password = password

        self.refresh_token = refresh_token
        self.access_token = access_token
        self.access_token_expires = access_token_expires

        self._session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        # self._session = aiohttp.ClientSession(
        #     timeout=aiohttp.ClientTimeout(total=30),
        #     mocked_server=aiohttp.MockedServer(None, None)
        # )

        self.account_info: dict = None  # type: ignore[assignment]
        self.locations: list[Location] = []
        self.installation_info: dict = None  # type: ignore[assignment]

    async def login(self) -> None:
        """Authenticate with the server."""

        try:  # the cached access_token may be valid, but is not authorized
            await self.user_account()
        except aiohttp.ClientResponseError as exc:
            if exc.status != HTTP_UNAUTHORIZED or not self.access_token:
                raise AuthenticationError(str(exc))

            _LOGGER.warning("Unauthorized access_token (will try re-authenticating).")
            self.access_token = None
            await self.user_account()

        await self.installation()

    async def _headers(self) -> dict:
        """Ensure the Authorization Header has a valid Access Token."""

        if not self.access_token or not self.access_token_expires:
            await self._basic_login()

        elif dt.now() > self.access_token_expires - td(seconds=30):
            await self._basic_login()

        assert isinstance(self.access_token, str)  # mypy

        return {
            "Accept": AUTH_HEADER_ACCEPT,
            "Authorization": "bearer " + self.access_token,
        }

    async def _basic_login(self) -> None:
        """Obtain a new access token from the vendor.

        First, try using the refresh_token, if one is available, otherwise
        authenticate using the user credentials.
        """

        _LOGGER.debug("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = self.access_token_expires = None

        if self.refresh_token:
            _LOGGER.debug("Authenticating with the refresh_token...")
            credentials = CREDS_REFRESH_TOKEN | {
                "refresh_token": self.refresh_token,
            }

            try:
                await self._obtain_access_token(credentials)
            except AuthenticationError:
                _LOGGER.warning("Invalid refresh_token (will try user credentials).")
                self.refresh_token = None

        if not self.refresh_token:
            _LOGGER.debug("Authenticating with the user credentials...")
            credentials = CREDS_USER_PASSWORD | {
                "Username": self.username,
                "Password": self.password,
            }

            await self._obtain_access_token(credentials)

        _LOGGER.debug(f"refresh_token = {self.refresh_token}")
        _LOGGER.debug(f"access_token = {self.access_token}")
        _LOGGER.debug(f"access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, credentials: dict) -> None:
        async with self._session.post(
            AUTH_URL, data=AUTH_PAYLOAD | credentials, headers=AUTH_HEADER
        ) as response:
            try:
                response_text = await response.text()  # before raise_for_status()
                response.raise_for_status()

            except aiohttp.ClientResponseError:
                msg = "Unable to obtain an Access Token"
                if response_text:  # if there is a message, then raise with it
                    msg += ", hint: " + response_text

                raise AuthenticationError(msg)

            try:  # the access token _should_ be valid...
                # this may cause a ValueError
                response_json = await response.json()

                # TODO: remove
                _LOGGER.error(f"POST {AUTH_URL} = {await response.json()}")

                # these may cause a KeyError
                self.access_token = response_json["access_token"]
                self.access_token_expires = dt.now() + td(
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

    async def user_account(self) -> dict:
        """Return the user account information."""

        self.account_info = None  # type: ignore[assignment]

        async with self._session.get(
            f"{URL_BASE}/userAccount",
            headers=await self._headers(),
        ) as response:
            response.raise_for_status()
            self.account_info = await response.json()

        assert isinstance(self.account_info, dict)  # mypy
        return self.account_info

    async def installation(self) -> dict:  # installation_info
        """Return the details of the installation and update the status."""

        assert isinstance(self.account_info, dict)  # mypy

        # FIXME: shouldn't really be starting again with new objects?
        self.locations = []  # for now, need to clear this before GET

        url = (
            f"location/installationInfo?userId={self.account_info['userId']}"
            "&includeTemperatureControlSystems=True"
        )

        async with self._session.get(
            f"{URL_BASE}/{url}", headers=await self._headers()
        ) as response:
            response.raise_for_status()
            self.installation_info = await response.json()

        for loc_data in self.installation_info:
            loc = Location(self, loc_data)
            await loc.status()
            self.locations.append(loc)

        return self.installation_info

    async def full_installation(self, location_id: None | _LocationIdT = None) -> dict:
        """Return the full details of the specified Location."""

        if location_id is None:
            location_id = self.installation_info[0]["locationInfo"]["locationId"]

        url = f"location/{location_id}/installationInfo?includeTemperatureControlSystems=True"

        async with self._session.get(
            f"{URL_BASE}/{url}", headers=await self._headers()
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def gateway(self) -> dict:  # TODO: check me
        """Update the gateway status and return the details."""

        async with self._session.get(
            f"{URL_BASE}/gateway", headers=await self._headers()
        ) as response:
            response.raise_for_status()
            return await response.json()

    def _get_single_heating_system(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        This provides a shortcut for most systems.
        """

        if not self.locations or len(self.locations) != 1:
            raise SingleTcsError(
                "There is not a single location (only) for this account"
            )

        if len(self.locations[0]._gateways) != 1:  # type: ignore[index]
            raise SingleTcsError(
                "There is not a single gateway (only) for this account/location"
            )

        if len(self.locations[0]._gateways[0]._control_systems) != 1:  # type: ignore[index]
            raise SingleTcsError(
                "There is not a single TCS (only) for this account/location/gateway"
            )

        return self.locations[0]._gateways[0]._control_systems[0]  # type: ignore[index]

    @property
    def system_id(self) -> _SystemIdT:  # an evohome-client anachronism, deprecate?
        """Return the ID of the 'default' TCS (assumes only one loc/gwy/TCS)."""
        return self._get_single_heating_system().systemId

    async def set_status_reset(self) -> None:
        """Reset the mode of the default TCS and its zones."""
        await self._get_single_heating_system().set_status_reset()

    async def set_status_normal(self) -> None:
        """Set the default TCS into auto mode."""
        await self._get_single_heating_system().set_status_normal()

    async def set_status_custom(self, /, *, until: None | dt = None) -> None:
        """Set the default TCS into custom mode."""
        await self._get_single_heating_system().set_status_custom(until=until)

    async def set_status_eco(self, /, *, until: None | dt = None) -> None:
        """Set the default TCS into eco mode."""
        await self._get_single_heating_system().set_status_eco(until=until)

    async def set_status_away(self, /, *, until: None | dt = None) -> None:
        """Set the default TCS into away mode."""
        await self._get_single_heating_system().set_status_away(until=until)

    async def set_status_dayoff(self, /, *, until: None | dt = None) -> None:
        """Set the default TCS into day off mode."""
        await self._get_single_heating_system().set_status_dayoff(until=until)

    async def set_status_heatingoff(self, /, *, until: None | dt = None) -> None:
        """Set the default TCS into heating off mode."""
        await self._get_single_heating_system().set_status_heatingoff(until=until)

    async def temperatures(self) -> list[dict]:
        """Return the current temperatures and setpoints of the default TCS."""
        return await self._get_single_heating_system().temperatures()

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "zone_schedules_backup() is deprecated, use backup_schedules()"
        )

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the default control system to the file."""
        await self._get_single_heating_system().backup_schedules(filename)

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "zone_schedules_restore() is deprecated, use restore_schedules()"
        )

    async def restore_schedules(
        self, filename: _FilePathT, match_by_name: bool = False
    ) -> None:
        """Restore all schedules from the file to the control system.

        There is the option to match schedules to their zone/dhw by name rather than id.
        """

        await self._get_single_heating_system().restore_schedules(
            filename, match_by_name=match_by_name
        )
