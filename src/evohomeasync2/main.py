"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .auth import AbstractTokenManager, Auth
from .const import SZ_USER_ID
from .location import Location
from .schemas import factory_user_account, factory_user_locations_installation_info

if TYPE_CHECKING:
    import aiohttp

    from .schemas.typedefs import EvoLocConfigResponseT, EvoUsrConfigResponseT
    from .system import ControlSystem


SCH_USER_ACCOUNT: Final = factory_user_account(camel_to_snake)
SCH_USER_LOCATIONS: Final = factory_user_locations_installation_info(camel_to_snake)


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClientNew:
    """Provide a client to access the Resideo TCC API."""

    _LOC_IDX: int = 0  # the index of the default location in _user_locs

    _user_info: EvoUsrConfigResponseT | None = None
    _user_locs: list[EvoLocConfigResponseT] | None = None  # all locations of the user

    def __init__(
        self,
        token_manager: AbstractTokenManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object."""

        self.logger = _LOGGER
        if debug:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode is explicitly enabled.")

        self.auth = Auth(
            token_manager,
            websession or token_manager.websession,
            logger=self.logger,
        )

        try:
            self._tzinfo: ZoneInfo | None = ZoneInfo("localtime")
        except ZoneInfoNotFoundError:  # e.g. on Windows
            self._tzinfo = None

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    async def update(
        self,
        /,
        *,
        _reset_config: bool = False,
        _dont_update_status: bool = False,
    ) -> list[EvoLocConfigResponseT]:
        """Retrieve the latest state of the installation and it's locations.

        If required, or when `_reset_config` is true, first retrieves the user
        information & installation configuration.

        If `_disable_status_update` is True, does not update the status of each location
        (but will still retrieve configuration data, if required).
        """

        if _reset_config:
            self._user_info = None
            self._user_locs = None

        if self._user_info is None:
            url = "userAccount"
            self._user_info = await self.auth.get(url, schema=SCH_USER_ACCOUNT)  # type: ignore[assignment]

        assert self._user_info is not None  # mypy hint

        if self._user_locs is None:
            url = f"location/installationInfo?userId={self._user_info[SZ_USER_ID]}&includeTemperatureControlSystems=True"
            self._user_locs = await self.auth.get(url, schema=SCH_USER_LOCATIONS)  # type: ignore[assignment]

            self._locations = None
            self._location_by_id = None

        assert self._user_locs is not None  # mypy hint

        if self._locations is None:  # create/refresh the configured locations
            self._locations = []
            self._location_by_id = {}

            for loc_entry in self._user_locs:
                loc = Location(self, loc_entry)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            # only warn once per config refresh (i.e. not on every status update)
            if not _dont_update_status and (num := len(self._locations)) > 1:
                self.logger.warning(
                    f"There are {num} locations. Reduce the risk of exceeding API rate "
                    "limits by individually updating only the necessary locations."
                )

        assert self._locations is not None  # mypy hint

        if not _dont_update_status:  # see warning, above
            for loc in self._locations:
                await loc.update()
        #

        return self._user_locs

    @property
    def user_account(self) -> EvoUsrConfigResponseT:
        """Return the (config) information of the user account."""

        if not self._user_info:
            raise exc.NoSystemConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return self._user_info

    @property
    def user_installation(self) -> list[EvoLocConfigResponseT]:
        """Return the (config) information of all the user's locations."""

        if not self._user_locs:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._user_locs

    @property
    def locations(self) -> list[Location]:
        """Return the list of location entities."""

        if not self._user_locs:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        assert self._locations is not None  # mypy hint
        return self._locations

    # A significant majority of users will have exactly one TCS, thus for convenience...
    def _get_single_tcs(self) -> ControlSystem:
        """If there is a single location/gateway/TCS, return it, or raise an exception.

        The majority of users will have only one TCS.
        """

        if not (locs := self.locations) or len(locs) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single location (only) for this account"
            )

        if not (gwys := locs[self._LOC_IDX].gateways) or len(gwys) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single gateway (only) for this account/location"
            )

        if not (tcss := gwys[0].systems) or len(tcss) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single TCS (only) for this account/location/gateway"
            )

        return tcss[0]

    @property
    def tcs(self) -> ControlSystem:
        return self._get_single_tcs()

    @property
    def tzinfo(self) -> ZoneInfo | None:
        """Return a tzinfo-compliant object for this running instance of evohome."""
        return self._tzinfo
