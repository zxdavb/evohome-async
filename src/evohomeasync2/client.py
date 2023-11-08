#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the *updated* Evohome API."""
from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING, NoReturn

import aiohttp

from .broker import Broker
from .controlsystem import ControlSystem
from .exceptions import AuthenticationFailed, DeprecationError, NoSingleTcsError
from .location import Location
from .schema import SCH_FULL_CONFIG, SCH_USER_ACCOUNT

if TYPE_CHECKING:
    from .schema import (
        _EvoDictT,
        _EvoListT,
        _EvoSchemaT,
        _FilePathT,
        _LocationIdT,
        _SystemIdT,
    )


_LOGGER = logging.getLogger(__name__)


class EvohomeClientDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def full_installation(
        self, location_id: None | _LocationIdT = None
    ) -> NoReturn:
        # if location_id is None:
        #     location_id = self.installation_info[0]["locationInfo"]["locationId"]
        # url = f"location/{location_id}/installationInfo?"  # Specific location

        raise DeprecationError(
            "EvohomeClient.full_installation() is deprecated, use .installation()"
        )

    async def gateway(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError("EvohomeClient.gateway() is deprecated")

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

    async def set_status_reset(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.set_status_reset() is deprecated, use .reset_mode()"
        )

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.zone_schedules_backup() is deprecated, use .backup_schedules()"
        )

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:
        raise DeprecationError(
            "EvohomeClient.zone_schedules_restore() is deprecated, use .restore_schedules()"
        )


class EvohomeClient(EvohomeClientDeprecated):
    """Provide a client to access the Honeywell TCC API."""

    _full_config: _EvoListT = None  # type: ignore[assignment]  # installation_info (all locations of user)
    _user_account: _EvoDictT = None  # type: ignore[assignment]  # account_info

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        debug: bool = False,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        session: None | aiohttp.ClientSession = None,
    ) -> None:
        """Construct the v2 EvohomeClient object.

        If tokens are given then this will be used to try and reduce the number of
        calls to the authentication service which is known to be rate limited.
        """

        self._logger = _LOGGER

        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode is explicitly enabled.")

        self._broker = Broker(
            username,
            password,
            refresh_token=refresh_token,
            access_token=access_token,
            access_token_expires=access_token_expires,
            session=session,
            logger=self._logger,
        )

        self.locations: list[Location] = []

    @property
    def username(self) -> str:  # TODO: deprecate? or use config JSON?
        return self._broker._credentials["Username"]

    @property
    def password(self) -> str:  # TODO: deprecate
        return self._broker._credentials["Password"]

    @property
    def refresh_token(self) -> str | None:  # TODO: deprecate
        return self._broker.refresh_token

    @property
    def access_token(self) -> str | None:  # TODO: deprecate
        return self._broker.access_token

    @property
    def access_token_expires(self) -> dt | None:  # TODO: deprecate
        return self._broker.access_token_expires

    async def login(self) -> None:
        """Retrieve the user account and installation details.

        Will authenticate as required.
        """

        try:  # the cached access_token may be valid, but is not authorized
            await self.user_account()

        except AuthenticationFailed as exc:
            if exc.status != HTTPStatus.UNAUTHORIZED or not self.access_token:
                raise

            self._logger.warning(
                "Unauthorized access_token (will try re-authenticating)."
            )
            self._broker.access_token = None  # FIXME: this is a hack
            await self.user_account(force_update=True)

        await self.installation()

    @property  # user_account
    def account_info(self) -> _EvoSchemaT:  # from original evohomeclient namespace
        """Return the information of the user account."""
        return self._user_account

    async def user_account(self, force_update: bool = False) -> _EvoDictT:
        """Return the user account information.

        If required/forced, retrieve that data from the vendor's API.
        """

        # There is usually no need to refresh this data (it is config, not state)
        if self._user_account and not force_update:
            return self._user_account

        self._user_account = await self._broker.get(
            "userAccount", schema=SCH_USER_ACCOUNT
        )  # type: ignore[assignment]

        return self._user_account

    @property  # full_config (all locations of user)
    def installation_info(self) -> _EvoListT:  # from original evohomeclient namespace
        """Return the installation info (config) of all the user's locations."""
        return self._full_config

    async def installation(self, force_update: bool = False) -> _EvoListT:
        """Return the configuration of the user's locations their status.

        If required/forced, retrieve that data from the vendor's API.
        Note that the force_update flag will create new location entities (it includes
        `self.locations = []`).
        """

        # There is usually no need to refresh this data (it is config, not state)
        if self._full_config and not force_update:
            return self._full_config

        return await self._installation()  # aka self.installation_info

    async def _installation(self, refresh_status: bool = True) -> _EvoListT:
        """Return the configuration of the user's locations their status.

        The refresh_status flag is used for dev/test to disable retreiving the initial
        status of each location (and its child entities).
        """

        assert isinstance(self.account_info, dict)  # mypy

        # FIXME: shouldn't really be starting again with new objects?
        self.locations = []  # for now, need to clear this before GET

        url = f"location/installationInfo?userId={self.account_info['userId']}"
        url += "&includeTemperatureControlSystems=True"

        self._full_config = await self._broker.get(url, schema=SCH_FULL_CONFIG)  # type: ignore[assignment]

        # populate each freshly instantiated location with its initial status
        loc_config: _EvoDictT

        for loc_config in self._full_config:
            loc = Location(self, loc_config)
            self.locations.append(loc)
            if refresh_status:
                await loc.refresh_status()

        return self._full_config

    def _get_single_tcs(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        Most users will have only one TCS.
        """

        if not self.locations or len(self.locations) != 1:
            raise NoSingleTcsError(
                "There is not a single location (only) for this account"
            )

        if len(self.locations[0]._gateways) != 1:  # type: ignore[index]
            raise NoSingleTcsError(
                "There is not a single gateway (only) for this account/location"
            )

        if len(self.locations[0]._gateways[0]._control_systems) != 1:  # type: ignore[index]
            raise NoSingleTcsError(
                "There is not a single TCS (only) for this account/location/gateway"
            )

        return self.locations[0]._gateways[0]._control_systems[0]  # type: ignore[index]

    @property
    def system_id(self) -> _SystemIdT:  # an evohome-client anachronism, deprecate?
        """Return the ID of the 'default' TCS (assumes only one loc/gwy/TCS)."""
        return self._get_single_tcs().systemId

    async def reset_mode(self) -> None:
        """Reset the mode of the default TCS and its zones."""
        await self._get_single_tcs().reset_mode()

    async def set_mode_auto(self) -> None:
        """Set the default TCS into auto mode."""
        await self._get_single_tcs().set_auto()

    async def set_mode_away(self, /, *, until: dt | None = None) -> None:
        """Set the default TCS into away mode."""
        await self._get_single_tcs().set_away(until=until)

    async def set_mode_custom(self, /, *, until: dt | None = None) -> None:
        """Set the default TCS into custom mode."""
        await self._get_single_tcs().set_custom(until=until)

    async def set_mode_dayoff(self, /, *, until: dt | None = None) -> None:
        """Set the default TCS into day off mode."""
        await self._get_single_tcs().set_dayoff(until=until)

    async def set_mode_eco(self, /, *, until: dt | None = None) -> None:
        """Set the default TCS into eco mode."""
        await self._get_single_tcs().set_eco(until=until)

    async def set_mode_heatingoff(self, /, *, until: dt | None = None) -> None:
        """Set the default TCS into heating off mode."""
        await self._get_single_tcs().set_heatingoff(until=until)

    async def temperatures(self) -> _EvoListT:
        """Return the current temperatures and setpoints of the default TCS."""
        return await self._get_single_tcs().temperatures()

    async def backup_schedules(self, filename: _FilePathT) -> None:
        """Backup all schedules from the default control system to the file."""
        await self._get_single_tcs().backup_schedules(filename)

    async def restore_schedules(
        self, filename: _FilePathT, match_by_name: bool = False
    ) -> None:
        """Restore all schedules from the file to the control system.

        There is the option to match schedules to their zone/dhw by name rather than id.
        """

        await self._get_single_tcs().restore_schedules(
            filename, match_by_name=match_by_name
        )
