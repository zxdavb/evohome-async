"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .auth import AbstractSessionManager, Auth
from .entities import Location
from .schemas import factory_location_response_list, factory_user_account_info_response

if TYPE_CHECKING:
    import aiohttp

    from .schemas import EvoLocConfigDictT, EvoUserAccountDictT

SCH_GET_ACCOUNT_INFO: Final = factory_user_account_info_response(camel_to_snake)
SCH_GET_ACCOUNT_LOCS: Final = factory_location_response_list(camel_to_snake)

_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClient:
    """Provide a client to access the Resideo TCC API (assumes one TCS/Location)."""

    _user_info: EvoUserAccountDictT | None = None
    _user_locs: list[EvoLocConfigDictT] | None = None  # all locations of the user

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v0 EvohomeClient object."""

        self.logger = _LOGGER
        if debug:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode is explicitly enabled.")

        self._session_manager = session_manager

        self.auth = Auth(
            session_manager.get_session_id,
            websession or session_manager.websession,
            logger=self.logger,
        )

        # self.devices: dict[_ZoneIdT, _DeviceDictT] = {}  # dhw or zone by id
        # self.named_devices: dict[_ZoneNameT, _DeviceDictT] = {}  # zone by name

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    async def update(
        self,
        /,
        *,
        _reset_config: bool = False,
    ) -> list[EvoLocConfigDictT] | None:
        """Retrieve the latest state of the user's locations.

        If required, or when `_reset_config` is true, first retrieves the user
        information.
        """

        if _reset_config:
            self._user_info = None
            self._user_locs = None

        await self._get_config()

        return self._user_locs

    async def _get_config(self) -> list[EvoLocConfigDictT]:
        """Ensures the config of the user and their locations.

        If required, first retrieves the user information & installation configuration.
        """

        if self._user_info is None:  # will handle a bad session_id
            url = "accountInfo"
            try:
                self._user_info = await self.auth.get(url, schema=SCH_GET_ACCOUNT_INFO)  # type: ignore[assignment]

            except exc.ApiRequestFailedError as err:  # check if 401 - bad session_id
                if err.status != HTTPStatus.UNAUTHORIZED:  # 401
                    raise

                # in this case, the 401 must be due to a bad session_id as the
                # URL is well-known (and there is no no usr_id, loc_id, etc.)
                # that is, the accountInfo URL is open to all authenticated users

                self.logger.warning(
                    f"The session_id appears invalid (will re-authenticate): {err}"
                )

                self._session_manager._clear_session_id()
                self._user_info = await self.auth.get(url, schema=SCH_GET_ACCOUNT_INFO)  # type: ignore[assignment]

        assert self._user_info is not None  # mypy (internal hint)

        if self._user_locs is None:
            url = f"locations?userId={self._user_info["user_id"]}&allData=True"
            self._user_locs = await self.auth.get(url, schema=SCH_GET_ACCOUNT_LOCS)  # type: ignore[assignment]

            self._locations = None
            self._location_by_id = None

        assert self._user_locs is not None  # mypy (internal hint)

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_config in self._user_locs:
                loc = Location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

        return self._user_locs

    @property
    def user_account(self) -> EvoUserAccountDictT:
        """Return the information of the user account."""

        if self._user_info is None:
            raise exc.InvalidConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return self._user_info

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._user_locs is None:
            raise exc.InvalidConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._locations  # type: ignore[return-value]

    @property
    def location_by_id(self) -> dict[str, Location]:
        """Return the list of locations."""

        if self._user_locs is None:
            raise exc.InvalidConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._location_by_id  # type: ignore[return-value]

    # A significant majority of users will have exactly one TCS, thus for convenience...
    @property
    def tcs(self) -> Location:
        """If there is a single location/TCS, return it, or raise an exception.

        The majority of users will have only one location/TCS.
        """

        if not (locs := self.locations) or len(locs) != 1:
            raise exc.NoSingleTcsError(
                f"{self}: There is not a single location (only) for this account"
            )

        return locs[0]
