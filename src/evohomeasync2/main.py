#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import logging
from datetime import datetime as dt
from typing import TYPE_CHECKING

from . import exceptions as exc
from .auth import AbstractTokenManager, Auth
from .control_system import ControlSystem
from .location import Location
from .schema import SCH_FULL_CONFIG, SCH_USER_ACCOUNT, convert_keys_to_snake_case
from .schema.const import S2_USER_ID

if TYPE_CHECKING:
    import aiohttp

    from .schema import _EvoDictT, _EvoListT, _ScheduleT


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClientNew:  # requires a Token Manager
    """Provide a client to access the Resideo TCC API."""

    #

    _install_config: _EvoListT | None = None  # all locations
    _user_info: _EvoDictT | None = None

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

        # self._token_manager = token_manager

        #
        #
        #

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

        self.auth = Auth(
            token_manager,
            websession or token_manager._websession,
            logger=self._logger,
        )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    async def update(
        self,
        /,
        *,
        reset_config: bool = False,
        dont_update_status: bool = False,
    ) -> None:
        """Retrieve the latest state of the installation and it's locations.

        If required, or when `reset_config` is true, first retrieves the user
        information & installation configuration.

        If `disable_status_update` is True, does not update the status of each location
        (but will still retrieve configuration data, if required).
        """

        if reset_config:
            self._user_info = None
            self._install_config = None

        if self._user_info is None:
            url = "userAccount"
            self._user_info = await self.auth.get(url, schema=SCH_USER_ACCOUNT)  # type: ignore[assignment]

        assert self._user_info is not None  # mypy hint

        if self._install_config is None:
            url = f"location/installationInfo?userId={self._user_info[S2_USER_ID]}"
            url += "&includeTemperatureControlSystems=True"

            self._install_config = await self.auth.get(url, schema=SCH_FULL_CONFIG)  # type: ignore[assignment]

            self._locations = None
            self._location_by_id = None

        assert self._install_config is not None  # mypy hint

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_config in self._install_config:
                loc = Location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            if dont_update_status and (num := len(self._locations)) > 1:
                self._logger.warning(
                    f"There are {num} locations. Reduce the risk of exceeding API rate "
                    "limits by individually updating only the necessary locations."
                )

        assert self._locations is not None  # mypy hint

        if not dont_update_status:
            for loc in self._locations:
                await loc.update()

    @property
    def user_information(self) -> _EvoDictT:
        """Return the information of the user account."""

        if not self._user_info:
            raise exc.NoSystemConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return convert_keys_to_snake_case(self._user_info)

    @property
    def installation_config(self) -> _EvoListT:
        """Return the installation info (config) of all the user's locations."""

        if not self._install_config:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return convert_keys_to_snake_case(self._install_config)

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._install_config is None:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        assert self._locations  # mypy hint

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

    async def temperatures(self) -> list[dict[str, int | str | None]]:  # TODO: remove?
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
