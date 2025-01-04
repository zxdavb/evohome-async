"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .auth import AbstractTokenManager, Auth
from .const import SZ_USER_ID
from .location import Location, create_location
from .schemas import factory_user_account, factory_user_locations_installation_info

if TYPE_CHECKING:
    import aiohttp

    from .control_system import ControlSystem
    from .schemas.typedefs import EvoLocConfigResponseT, EvoUsrConfigResponseT


SCH_USER_ACCOUNT: Final = factory_user_account(camel_to_snake)
SCH_USER_LOCATIONS: Final = factory_user_locations_installation_info(camel_to_snake)


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClient:
    """Provide a client to access the Resideo TCC API."""

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

        self._token_manager = token_manager

        self.auth = Auth(
            token_manager.get_access_token,
            websession or token_manager.websession,
            logger=self.logger,
        )

        # NOTE: below is an attempt to determine the local TZ of the host running this
        # client, and is not necessarily the TZ of each location known to this client;
        # locations each have their own TZ

        try:
            self._tzinfo: ZoneInfo | None = ZoneInfo("localtime")
        except ZoneInfoNotFoundError:  # e.g. on Windows
            self._tzinfo = None

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    async def update(
        self,
        /,
        *,
        _reset_config: bool = False,  # used by test suite
        _dont_update_status: bool = False,  # used by test suite
    ) -> list[EvoLocConfigResponseT]:
        """Retrieve the latest state of the user's' locations.

        If required, or when `_reset_config` is true, first retrieves the user
        information & installation configuration.

        If `_disable_status_update` is True, does not update the status of each
        location (but will still retrieve configuration data, if required).
        """

        if _reset_config:
            self._user_info = None
            self._user_locs = None  # and thus self._locations, etc.

            self._locations = None
            self._location_by_id = None

        if self._user_locs is None:
            await self._get_config(_dont_update_status=_dont_update_status)

        if not _dont_update_status:  # see warning, above
            for loc in self.locations:
                await loc.update()

        assert self._user_locs is not None  # mypy (internal hint)
        return self._user_locs

    async def _get_config(
        self, /, *, _dont_update_status: bool = False
    ) -> list[EvoLocConfigResponseT]:
        """Ensures the config of the user and their locations.

        If required, first retrieves the user information & installation configuration.
        """

        if self._user_info is None:  # will handle a bad access_token
            url = "userAccount"
            try:
                self._user_info = await self.auth.get(url, schema=SCH_USER_ACCOUNT)  # type: ignore[assignment]

            except exc.ApiRequestFailedError as err:  # check if 401 - bad access_token
                if err.status != HTTPStatus.UNAUTHORIZED:  # 401
                    raise

                # as the userAccount URL is open to all authenticated users, any 401 is
                # due the (albeit valid) access_token being rejected by the server (why?)

                self.logger.warning(
                    f"The access_token has been rejected (will re-authenticate): {err}"
                )

                self._token_manager._clear_access_token()
                self._user_info = await self.auth.get(url, schema=SCH_USER_ACCOUNT)  # type: ignore[assignment]

        assert self._user_info is not None  # mypy (internal hint)

        if self._user_locs is None:
            url = f"location/installationInfo?userId={self._user_info[SZ_USER_ID]}&includeTemperatureControlSystems=True"
            self._user_locs = await self.auth.get(url, schema=SCH_USER_LOCATIONS)  # type: ignore[assignment]

        assert self._user_locs is not None  # mypy (internal hint)

        if self._locations is None:  # create/refresh the configured locations
            self._locations = []
            self._location_by_id = {}

            for loc_entry in self._user_locs:
                loc = await create_location(self, loc_entry)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            # only warn once per config refresh (i.e. not on every status update)
            if not _dont_update_status and (num := len(self._locations)) > 1:
                self.logger.warning(
                    f"There are {num} locations. Reduce the risk of exceeding API rate "
                    "limits by individually updating only necessary locations."
                )

        return self._user_locs

    @property
    def user_account(self) -> EvoUsrConfigResponseT:
        """Return the (config) information of the user account."""

        if not self._user_info:
            raise exc.InvalidConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return self._user_info

    @property
    def locations(self) -> list[Location]:
        """Return the list of location entities."""

        if not self._user_locs:
            raise exc.InvalidConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._locations  # type: ignore[return-value]

    @property
    def location_by_id(self) -> dict[str, Location]:
        """Return the list of location entities."""

        if not self._user_locs:
            raise exc.InvalidConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._location_by_id  # type: ignore[return-value]

    # A significant majority of users will have exactly one TCS, thus for convenience...
    @property
    def tcs(self) -> ControlSystem:
        """If there is a single TCS, return it, or raise an exception.

        The majority of users will have only one TCS.
        """

        if not (locs := self.locations) or len(locs) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single location (only) for this account"
            )

        if not (gwys := locs[0].gateways) or len(gwys) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single gateway (only) for this account/location"
            )

        if not (tcss := gwys[0].systems) or len(tcss) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single TCS (only) for this account/location/gateway"
            )

        return tcss[0]
