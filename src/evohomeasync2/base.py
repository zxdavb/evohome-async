#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the *updated* Evohome API."""

from __future__ import annotations

import logging
from datetime import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, NoReturn

import aiohttp

from . import exceptions as exc
from .broker import Broker
from .controlsystem import ControlSystem
from .location import Location
from .schema import SCH_FULL_CONFIG, SCH_USER_ACCOUNT

if TYPE_CHECKING:
    from .schema import _EvoDictT, _EvoListT, _LocationIdT, _ScheduleT, _SystemIdT


_LOGGER: Final = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClientDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def full_installation(
        self, location_id: None | _LocationIdT = None
    ) -> NoReturn:
        # if location_id is None:
        #     location_id = self.installation_info[0]["locationInfo"]["locationId"]
        # url = f"location/{location_id}/installationInfo?"  # Specific location

        raise exc.DeprecationError(
            f"{self}: .full_installation() is deprecated, use .installation()"
        )

    async def gateway(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .gateway() is deprecated, use .locations[x].gateways[y]"
        )

    async def set_status_away(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_away() is deprecated, use .set_mode_away()"
        )

    async def set_status_custom(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_custom() is deprecated, use .set_mode_custom()"
        )

    async def set_status_dayoff(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_dayoff() is deprecated, use .set_mode_dayoff()"
        )

    async def set_status_eco(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_eco() is deprecated, use .set_mode_eco()"
        )

    async def set_status_heatingoff(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_heatingoff() is deprecated, use .set_mode_heatingoff()"
        )

    async def set_status_normal(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_normal() is deprecated, use .set_mode_auto()"
        )

    async def set_status_reset(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .set_status_reset() is deprecated, use .reset_mode()"
        )

    async def zone_schedules_backup(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .zone_schedules_backup() is deprecated, use .get_schedules()"
        )

    async def zone_schedules_restore(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .zone_schedules_restore() is deprecated, use .set_schedules()"
        )

    async def backup_schedules(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .backup_schedules() is deprecated, use .get_schedules()"
        )

    async def restore_schedules(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .restore_schedules() is deprecated, use .set_schedules()"
        )


class EvohomeClient(EvohomeClientDeprecated):
    """Provide a client to access the Honeywell TCC API."""

    _full_config: _EvoListT | None = None  # installation_info (all locations of user)
    _user_account: _EvoDictT | None = None  # account_info

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        session: None | aiohttp.ClientSession = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object.

        Usage:
          evo = EvohomeClient(...
          evo.login()                 # invokes: evo.user_account(), evo.installation()
          print(evo.system_id)        # assumes only one TCS

        If access/refresh tokens are provided they will be used to avoid calling the
        authentication service, which is known to be rate limited.
        """

        if debug:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")

        self._logger = _LOGGER
        self._username = username  # for __str__

        self.broker = Broker(
            username,
            password,
            _LOGGER,
            refresh_token=refresh_token,
            access_token=access_token,
            access_token_expires=access_token_expires,
            session=session,
        )

        self.locations: list[Location] = []

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(username='{self._username}')"

    @property
    def username(self) -> str:  # TODO: deprecate? or use config JSON?
        return self.broker._credentials["Username"]

    @property
    def password(self) -> str:  # TODO: deprecate
        return self.broker._credentials["Password"]

    @property
    def refresh_token(self) -> str | None:  # TODO: deprecate
        return self.broker.refresh_token

    @property
    def access_token(self) -> str | None:  # TODO: deprecate
        return self.broker.access_token

    @property
    def access_token_expires(self) -> dt | None:  # TODO: deprecate
        return self.broker.access_token_expires

    async def login(self) -> None:
        """Retrieve the user account and installation details.

        Will authenticate as required.
        """

        try:  # the cached access_token may be valid, but is not authorized
            await self.user_account()

        except exc.AuthenticationFailed as err:
            if err.status != HTTPStatus.UNAUTHORIZED or not self.access_token:
                raise

            _LOGGER.warning("Unauthorized access_token (will try re-authenticating).")
            self.broker.access_token = None  # FIXME: this is a hack
            await self.user_account(force_update=True)

        await self.installation()

    @property  # user_account
    def account_info(self) -> _EvoDictT | None:  # from original evohomeclient namespace
        """Return the information of the user account."""
        return self._user_account

    async def user_account(self, force_update: bool = False) -> _EvoDictT:
        """Return the user account information.

        If required/forced, retrieve that data from the vendor's API.
        """

        # There is usually no need to refresh this data (it is config, not state)
        if self._user_account and not force_update:
            return self._user_account

        self._user_account: _EvoDictT = await self.broker.get(
            "userAccount", schema=SCH_USER_ACCOUNT
        )  # type: ignore[assignment]

        assert self._user_account  # mypy
        return self._user_account

    @property  # full_config (all locations of user)
    def installation_info(self) -> _EvoListT | None:  # from original evohomeclient
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
        """Return the configuration of the user's locations with their status.

        The refresh_status flag is used for dev/test to disable retreiving the initial
        status of each location (and its child entities, e.g. TCS, zones, etc.).
        """

        assert isinstance(self.account_info, dict)  # mypy

        # FIXME: shouldn't really be starting again with new objects?
        self.locations = []  # for now, need to clear this before GET

        url = f"location/installationInfo?userId={self.account_info['userId']}"
        url += "&includeTemperatureControlSystems=True"

        self._full_config = await self.broker.get(url, schema=SCH_FULL_CONFIG)  # type: ignore[assignment]

        # populate each freshly instantiated location with its initial status
        loc_config: _EvoDictT

        for loc_config in self._full_config:  # type: ignore[union-attr]
            loc = Location(self, loc_config)
            self.locations.append(loc)
            if refresh_status:
                await loc.refresh_status()

        return self._full_config  # type: ignore[return-value]

    def _get_single_tcs(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        Most users will have only one TCS.
        """

        if not self.locations or len(self.locations) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single location (only) for this account"
            )

        if len(self.locations[0]._gateways) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single gateway (only) for this account/location"
            )

        if len(self.locations[0]._gateways[0]._control_systems) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single TCS (only) for this account/location/gateway"
            )

        return self.locations[0]._gateways[0]._control_systems[0]

    @property
    def system_id(self) -> _SystemIdT:  # an evohome-client anachronism, deprecate?
        """Return the ID of the default TCS (assumes only one loc/gwy/TCS)."""
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

    async def get_schedules(self) -> _ScheduleT:
        """Backup all schedules from the default TCS."""
        return await self._get_single_tcs().get_schedules()

    async def set_schedules(
        self, schedules: _ScheduleT, match_by_name: bool = False
    ) -> bool:
        """Restore all schedules to the default TCS and return True if success.

        There is the option to match a schedule to its zone/dhw by name, rather than id.
        """

        return await self._get_single_tcs().set_schedules(
            schedules, match_by_name=match_by_name
        )
