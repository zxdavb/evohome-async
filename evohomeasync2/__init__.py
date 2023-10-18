#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
from __future__ import annotations

from json.decoder import JSONDecodeError
import logging
from datetime import datetime as dt
from datetime import timedelta as td
from typing import TYPE_CHECKING, NoReturn

import aiohttp

# from .tests.mock import aiohttp

from .exceptions import AuthenticationError, InvalidResponse, SingleTcsError
from .exceptions import volErrorInvalid as _volErrorInvalid
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
from .schema import SCH_FULL_CONFIG, SCH_OAUTH_TOKEN, SCH_USER_ACCOUNT
from .zone import ZoneBase, Zone  # noqa: F401

try:  # voluptuous is an optional module...
    from voluptuous.error import Invalid as SchemaInvalid  # type: ignore[import-untyped]
except ModuleNotFoundError:  # No module named 'voluptuous'
    SchemaInvalid = _volErrorInvalid


if TYPE_CHECKING:
    from .typing import _FilePathT, _LocationIdT, _SystemIdT


HTTP_UNAUTHORIZED = 401

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)


class EvohomeClient:
    """Provide access to the v2 Evohome API."""

    _full_config: dict = None  # type: ignore[assignment]  # installation_info (all locations of user)
    _user_account: dict = None  # type: ignore[assignment]  # account_info

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

        self._credentials = {"Username": username, "Password": password}

        self.refresh_token = refresh_token
        self.access_token = access_token
        self.access_token_expires = access_token_expires

        self._session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        self.locations: list[Location] = []

    async def login(self) -> None:
        """Retreive the user account and installation details.

        Will authenticate as required.
        """

        try:  # the cached access_token may be valid, but is not authorized
            await self.user_account()
        except aiohttp.ClientResponseError as exc:
            if exc.status != HTTP_UNAUTHORIZED or not self.access_token:
                raise AuthenticationError(str(exc))

            _LOGGER.warning("Unauthorized access_token (will try re-authenticating).")
            self.access_token = None
            await self.user_account(force_update=True)

        await self.installation()

    async def _client(
        self, method, url, data=None, json=None, headers=None
    ) -> None | dict | str:
        """Wrapper for aiohttp.ClientSession()."""

        if headers is None:
            headers = await self._headers()

        if method == "GET":
            _session_method = self._session.get
            kwargs = {"headers": headers}

        elif method == "POST":
            _session_method = self._session.post
            kwargs = {"data": data, "headers": headers}

        elif method == "PUT":
            _session_method = self._session.put
            # headers["Content-Type"] = "application/json"
            kwargs = {"data": data, "json": json, "headers": headers}

        async with _session_method(url, **kwargs) as response:
            response.raise_for_status()

            try:
                result = await response.json()
            except JSONDecodeError:
                pass
            else:
                _LOGGER.info(f"{method} {url} (JSON) = {result}")
                return result

            try:
                result = await response.text()
            except UnicodeError:
                pass
            else:
                _LOGGER.info(f"{method} {url} (TEXT) = {result}")
                return result

            return None

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
            "Content-Type": "application/json",
        }

    async def _basic_login(self) -> None:
        """Obtain a new access token from the vendor (as it is invalid, or expired).

        First, try using the refresh token, if one is available, otherwise authenticate
        using the user credentials.
        """

        # assert (
        #     not self.access_token
        #     or not self.access_token_expires
        #     or dt.now() > self.access_token_expires - td(seconds=30)
        # )

        _LOGGER.debug("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = self.access_token_expires = None

        if self.refresh_token:
            _LOGGER.debug("Authenticating with the refresh_token...")
            credentials = {"refresh_token": self.refresh_token}

            try:
                await self._obtain_access_token(CREDS_REFRESH_TOKEN | credentials)
            except AuthenticationError:
                _LOGGER.warning("Invalid refresh_token (will try user credentials).")
                self.refresh_token = None

        if not self.refresh_token:
            _LOGGER.debug("Authenticating with the user credentials...")
            await self._obtain_access_token(CREDS_USER_PASSWORD | self._credentials)

        _LOGGER.debug(f"refresh_token = {self.refresh_token}")
        _LOGGER.debug(f"access_token = {self.access_token}")
        _LOGGER.debug(f"access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, credentials: dict) -> None:
        """Obtain an access token using either the refresh token or user credentials."""

        try:
            response = await self._client(
                "POST", AUTH_URL, data=AUTH_PAYLOAD | credentials, headers=AUTH_HEADER
            )  # 429, 503
            SCH_OAUTH_TOKEN(response)  # can't use this, due to obsfucatied values

        except aiohttp.ClientResponseError as exc:
            # These have been seen / have been common:
            #  - 400 Bad Request: unknown username/password?
            #  - 429 Too Many Requests: exceeded authentication/api rate limits
            #  - 503 Service Unavailable

            # can't use response.text() as may raise another error
            raise AuthenticationError(f"Unable to obtain an Access Token: {exc}")

        try:  # the access token _should_ be valid...
            self.access_token = response["access_token"]  # type: ignore[index]
            self.access_token_expires = dt.now() + td(seconds=response["expires_in"])  # type: ignore[index, arg-type]
            self.refresh_token = response["refresh_token"]  # type: ignore[index]

        except SchemaInvalid as exc:  # TODO: only if voluptuous is installed
            raise AuthenticationError(f"Unable to obtain an Access Token, hint: {exc}")

        except KeyError:
            raise AuthenticationError(
                f"Unable to obtain an Access Token, hint: {response}"
            )

        except TypeError:  # response was str or None, not dict
            raise AuthenticationError(
                f"Unable to obtain an Access Token, hint: {response}"
            )

    @property  # user_account
    def account_info(self) -> dict:  # from the original evohomeclient namespace
        """Return the information of the user account."""
        return self._user_account

    async def user_account(self, force_update: bool = False) -> dict:
        """Return the user account information.

        If required/forced, retreive that data from the vendor's API.
        """

        # There is usually no need to refresh this data
        if self._user_account and not force_update:
            return self._user_account

        try:
            response = await self._client("GET", f"{URL_BASE}/userAccount")

        except aiohttp.ClientResponseError as exc:
            # These have been seen / have been common:
            # - 401 Unauthorized

            raise InvalidResponse(f"Unable to obtain Account details: {exc}")

        self._user_account: dict = SCH_USER_ACCOUNT(response)

        return self._user_account

    @property  # full_config (all locations of user)
    def installation_info(self) -> dict:  # from the original evohomeclient namespace
        """Return the installation info (config) of all the user's locations."""
        return self._full_config

    async def installation(self, force_update: bool = False) -> dict:
        """Return the configuration of the user's locations their status.

        If required/forced, retreive that data from the vendor's API.
        """

        # There is usually no need to refresh this data
        if self._full_config and not force_update:
            return self._full_config
        return await self._installation()  # aka self.installation_info

    async def _installation(self, refresh_status: bool = True) -> dict:
        """Return the configuration of the user's locations their status.

        The refresh_status flag is used for dev/test.
        """

        assert isinstance(self.account_info, dict)  # mypy

        # FIXME: shouldn't really be starting again with new objects?
        self.locations = []  # for now, need to clear this before GET

        url = f"location/installationInfo?userId={self.account_info['userId']}&"
        url += "includeTemperatureControlSystems=True"

        try:
            response = await self._client("GET", f"{URL_BASE}/{url}")
        except aiohttp.ClientResponseError as exc:
            raise InvalidResponse(f"Unable to obtain Installation details: {exc}")

        self._full_config: dict = SCH_FULL_CONFIG(response)

        # populate each freshly instantiated location with its initial status
        for loc_data in self._full_config:
            loc = Location(self, loc_data)
            self.locations.append(loc)
            if refresh_status:
                await loc.refresh_status()

        return self._full_config

    async def full_installation(
        self, location_id: None | _LocationIdT = None
    ) -> NoReturn:
        # if location_id is None:
        #     location_id = self.installation_info[0]["locationInfo"]["locationId"]
        # url = f"location/{location_id}/installationInfo?"  # Specific location

        raise NotImplementedError(
            "EvohomeClient.full_installation() is deprecated, use .installation()"
        )

    async def gateway(self, *args, **kwargs) -> NoReturn:  # deprecated
        raise NotImplementedError("EvohomeClient.gateway() is deprecated")

    @property
    def system_id(self) -> _SystemIdT:  # an evohome-client anachronism, deprecate?
        """Return the ID of the 'default' TCS (assumes only one loc/gwy/TCS)."""
        return self._get_single_heating_system().systemId

    def _get_single_heating_system(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        Most systems will have only one TCS.
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

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:  # deprecated
        raise NotImplementedError(
            "ZoneBase.zone_schedules_backup() is deprecated, use .backup_schedules()"
        )

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the default control system to the file."""
        await self._get_single_heating_system().backup_schedules(filename)

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:  # deprecated
        raise NotImplementedError(
            "ZoneBase.zone_schedules_restore() is deprecated, use .restore_schedules()"
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
