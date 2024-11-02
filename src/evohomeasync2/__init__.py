#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the *updated* Evohome TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

import logging
from datetime import datetime as dt
from typing import TYPE_CHECKING

from . import exceptions as exc  # used internally
from .auth import AbstractTokenManager, Auth  # noqa: F401
from .controlsystem import ControlSystem
from .exceptions import (  # noqa: F401
    AuthenticationFailedError,
    EvohomeBaseError,
    EvohomeError,
    InvalidParameterError,
    InvalidScheduleError,
    InvalidSchemaError,
    NoSingleTcsError,
    NoSystemConfigError,
    RateLimitExceededError,
    RequestFailedError,
    SystemConfigBaseError,
)
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location
from .schema import SCH_FULL_CONFIG, SCH_USER_ACCOUNT, convert_keys_to_snake_case
from .schema.const import SZ_USER_ID
from .zone import Zone  # noqa: F401

if TYPE_CHECKING:
    import aiohttp

    from .schema import _EvoDictT, _EvoListT, _ScheduleT


__version__ = "1.2.0"

_LOGGER = logging.getLogger(__name__)


class TokenManager(AbstractTokenManager):  # used only by EvohomeClientOld
    """A wrapper to expose the new EvohomeClient without a TokenManager."""

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
    ) -> None:
        super().__init__(username, password, websession)

        self._refresh_token = refresh_token or ""
        self._access_token = access_token or ""
        self._access_token_expires = access_token_expires or dt.min

    async def load_access_token(self) -> None:
        raise NotImplementedError

    async def save_access_token(self) -> None:
        pass


class EvohomeClientNew:  # requires a Token Manager
    """Provide a client to access the Honeywell TCC API."""

    _installation_config: _EvoListT | None = None # all locations
    _user_information: _EvoDictT | None = None

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object."""

        self._logger = _LOGGER
        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode is explicitly enabled.")

        self.auth = Auth(websession or token_manager.websession, token_manager, _LOGGER)

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(token_manager='{self.auth.token_manager}')"

    async def update(
        self,
        /,
        *,
        reset_config: bool = False,
        disable_status_update: bool = False,
    ) -> _EvoListT:
        """Retrieve the latest state of the installation and it's locations.

        If required, or when `reset_config` is true, first retrieves the user
        information & installation configuration.

        If `disable_status_update` is True, does not update the status of each location
        (but will still retreive configuration data, if required).
        """

        if reset_config:
            self._user_information = None
            self._installation_config = None

        if not self._user_information:
            url = "userAccount"
            self._user_information = await self.auth.get(url, schema=SCH_USER_ACCOUNT)

        if not self._installation_config:
            url = (
                f"location/installationInfo?userId={self._user_information[SZ_USER_ID]}"
            )
            url += "&includeTemperatureControlSystems=True"

            self._installation_config = await self.auth.get(url, schema=SCH_FULL_CONFIG)

            self._locations = []
            self._location_by_id = {}

            for loc_config in self._installation_config:
                loc = Location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            if disable_status_update and (num := len(self._locations)) > 1:
                self._logger.warning(
                    f"There are {num} locations. Reduce the risk of exceeding API rate "
                    "limits by individually updating only the necessary locations."
                )

        if not disable_status_update:
            for loc in self._locations:
                await loc.update()

        return self._installation_config

    @property
    def user_information(self) -> _EvoDictT:
        """Return the information of the user account."""

        if not self._user_information:
            raise exc.NoSystemConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return convert_keys_to_snake_case(self._user_information)

    @property
    def installation_config(self) -> _EvoListT:
        """Return the installation info (config) of all the user's locations."""

        if not self._installation_config:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return convert_keys_to_snake_case(self._installation_config)

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._installation_config is None:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )
        return self._locations

    # Most users only have exactly one TCS, thus these convenience methods...
    def _get_single_tcs(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        Most users will have only one TCS.
        """

        if not (locs := self.locations) or len(locs) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single location (only) for this account"
            )

        if not (gwys := locs[0].gateways) or len(gwys) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single gateway (only) for this account/location"
            )

        if not (tcss := gwys[0].control_systems) or len(tcss) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single TCS (only) for this account/location/gateway"
            )

        return tcss[0]

    @property
    def system_id(self) -> str:
        """Return the id of the default TCS (assumes only one loc/gwy/TCS)."""
        return self._get_single_tcs().id

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


class EvohomeClientOld(EvohomeClientNew):  # needs only user credentials (no TM)
    """A wrapper to use the new EvohomeClient without passing in a TokenManager."""

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        websession: None | aiohttp.ClientSession = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object."""

        websession = websession or aiohttp.ClientSession()

        self._token_manager = TokenManager(
            username,
            password,
            websession,
            refresh_token=refresh_token,
            access_token=access_token,
            access_token_expires=access_token_expires,
        )

        super().__init__(self._token_manager, debug=debug)

    @property
    def access_token(self) -> str:  # type: ignore[override]
        """Return the access_token attr."""
        return self._token_manager.access_token

    @property
    def access_token_expires(self) -> dt:  # type: ignore[override]
        """Return the access_token_expires attr."""
        return self._token_manager.access_token_expires

    @property
    def refresh_token(self) -> str:  # type: ignore[override]
        """Return the refresh_token attr."""
        return self._token_manager.refresh_token

    @property
    def username(self) -> str:  # type: ignore[override]
        """Return the username attr."""
        return self._token_manager.username


class EvohomeClient(EvohomeClientOld):  # The default EvohomeClient (old or new)
    """A wrapper to expose the new EvohomeClient in the selected version."""
