"""The client for the TCC v2 API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiozoneinfo import async_get_time_zone

from _evohome.const import _ERR_NO_CONFIG
from _evohome.helpers import Case

from . import exceptions as exc
from .auth import AbstractTokenManager, Auth
from .const import SZ_USER_ID
from .location import Location, create_location
from .schemas.account import factory_usr_account
from .schemas.config import factory_usr_locations

if TYPE_CHECKING:
    import aiohttp

    from _evohome.helpers import Validator

    from .typedefs import EvoLocConfigResponseT, EvoUsrAccountResponseT


SCH_USR_ACCOUNT: Final[Validator[EvoUsrAccountResponseT]] = factory_usr_account(
    Case.PYTHONIC
)
SCH_USR_LOCATIONS: Final[Validator[list[EvoLocConfigResponseT]]] = (
    factory_usr_locations(Case.PYTHONIC)
)

_LOGGER = logging.getLogger(__name__.rpartition(".")[0])  # "evohomeasync2"


class EvohomeClient:
    """Provide a client to access the Resideo TCC API."""

    _user_info: EvoUsrAccountResponseT | None = None
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

        self._logger = _LOGGER
        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode explicitly enabled via kwarg.")

        self._token_manager = token_manager
        self.auth = Auth(token_manager, websession or token_manager.websession)

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

        self._tzinfo: ZoneInfo | None = None
        self._tzinfo_initialized: bool = False

    def __str__(self) -> str:
        """Return a string representation of this object."""
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def tzinfo(self) -> ZoneInfo | None:
        """Return a tzinfo-compliant object for the client's local time."""

        if not self._tzinfo_initialized:
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Timezone information"))

        return self._tzinfo

    async def setup(self, *, _reset_config: bool = False) -> None:
        """Retrieve the user information & the configuration of all their locations.

        This is usually called only once, before using the client. It does not
        retrieve the status of any location: use `Location.get_status()` for that.

        There is one API call for the user info, and a second for the config of all the
        user's locations. If they have already been retrieved, there are none (unless
        `_reset_config` is true, for use by the test suite).
        """

        if _reset_config:
            self._user_info = None
            self._user_locs = None

            self._locations = None
            self._location_by_id = None

        if self._user_locs is None:
            try:
                await self._get_config()
            except exc.BadApiResponseError as err:  # e.g. failed validation
                raise exc.InvalidConfigError(err.message) from err

    async def _async_init_tzinfo(self) -> None:
        """Initialize timezone info without blocking the event loop."""

        # NOTE: below is an attempt to determine the local TZ of the host running this
        # client, and is not necessarily the TZ of each location known to this client;
        # locations each have their own TZ

        try:
            self._tzinfo = await async_get_time_zone("localtime")
        except ZoneInfoNotFoundError:  # e.g. on Windows
            self._tzinfo = None
        finally:
            self._tzinfo_initialized = True

    async def _get_user_account(self) -> EvoUsrAccountResponseT:
        """Get the user's account, re-authenticating if the access_token is rejected."""

        url = "userAccount"

        # if valid, auth.get() sends this token (without yielding), else it fetches another
        access_token = (
            self._token_manager.access_token
            if self._token_manager.is_token_valid()
            else None
        )

        try:
            return await self.auth.get(url, schema=SCH_USR_ACCOUNT)

        except exc.AuthenticationFailedError:  # unable to get an access_token
            raise

        except exc.ApiCallFailedError as err:  # check if 401 - bad access_token
            if err.status != HTTPStatus.UNAUTHORIZED:  # 401
                raise

            # as the userAccount URL is open to all authenticated users, any 401 is
            # due the (albeit valid) access_token being rejected by the server

            self._logger.warning(
                f"The access_token has been rejected (will re-authenticate): {err}"
            )

            # another task may have since refreshed it, so don't clear the new one
            if access_token is None or self._token_manager.access_token == access_token:
                self._token_manager.clear_access_token()
            return await self.auth.get(url, schema=SCH_USR_ACCOUNT)

    async def _get_config(self) -> list[EvoLocConfigResponseT]:
        """Ensures the config of the user and their locations.

        If required, first retrieves the user information & installation configuration.
        """

        if not self._tzinfo_initialized:
            await self._async_init_tzinfo()

        if self._user_info is None:  # will handle access_token rejection
            self._user_info = await self._get_user_account()

        if self._user_locs is None:
            try:
                user_id = self._user_info[SZ_USER_ID]
            except (KeyError, TypeError) as err:
                raise exc.BadApiResponseError(
                    f"No user_id in user_info dict. Received: {self._user_info}"
                ) from err

            self._user_locs = await self.auth.get(
                f"location/installationInfo?userId={user_id}&includeTemperatureControlSystems=True",
                schema=SCH_USR_LOCATIONS,
            )

            assert self._user_locs is not None  # mypy

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_config in self._user_locs:
                loc = await create_location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

        return self._user_locs

    @property
    def user_account(self) -> EvoUsrAccountResponseT:
        """Return the (config) information of the user account."""

        if self._user_info is None:  # None: never fetched, []: fetched but empty
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Account information"))

        return self._user_info

    @property
    def locations(self) -> list[Location]:
        """Return the list of location entities (may be empty)."""

        if self._locations is None:  # None: never fetched, []: fetched but empty
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Installation information"))

        return self._locations

    @property
    def location_by_id(self) -> dict[str, Location]:
        """Return the location entities by id (may be empty)."""

        if self._location_by_id is None:  # None: never fetched, []: fetched but empty
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Installation information"))

        return self._location_by_id
