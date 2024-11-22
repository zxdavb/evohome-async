#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from . import exceptions as exc
from .auth import AbstractSessionManager, Auth
from .entities import Location
from .schemas import factory_location_response_list, factory_user_account_info_response

if TYPE_CHECKING:
    import aiohttp

    from .schemas import EvoLocationDictT, EvoUserAccountDictT, _LocationIdT

SCH_GET_ACCOUNT_INFO: Final = factory_user_account_info_response(camel_to_snake)
SCH_GET_ACCOUNT_LOCS: Final = factory_location_response_list(camel_to_snake)

_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


class EvohomeClientNew:
    """Provide a client to access the Resideo TCC API (assumes a single TCS)."""

    _LOC_IDX: int = 0  # the index of the default location in _user_locs

    _user_info: EvoUserAccountDictT | None = None
    _user_locs: list[EvoLocationDictT] | None = None  # all locations of the user

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v0 EvohomeClient object."""

        self._logger = _LOGGER
        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode is explicitly enabled.")

        self.auth = Auth(
            session_manager,
            websession or session_manager._websession,
            logger=self._logger,
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
        # _dont_update_status: bool = False,
    ) -> list[EvoLocationDictT] | None:
        """Retrieve the latest state of the installation and it's locations.

        If required, or when `_reset_config` is true, first retrieves the user
        information.
        """

        if _reset_config:
            self._user_info = None
            self._user_locs = None

        if self._user_info is None:
            url = "accountInfo"
            self._user_info = await self.auth.get(url, schema=SCH_GET_ACCOUNT_INFO)  # type: ignore[assignment]

        assert self._user_info is not None  # mypy hint

        if self._user_locs is None:
            url = f"locations?userId={self._user_info["user_id"]}"
            url += "&allData=True"

            self._user_locs = await self.auth.get(url, schema=SCH_GET_ACCOUNT_LOCS)  # type: ignore[assignment]

            self._locations = None
            self._location_by_id = None

        assert self._user_locs is not None  # mypy hint

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_config in self._user_locs:
                loc = Location(self, loc_config)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            #
            #

        assert self._locations is not None  # mypy hint

        self._locn_info = self._user_locs[self._LOC_IDX]

        return self._user_locs

    @property
    def user_account(self) -> EvoUserAccountDictT:
        """Return the information of the user account."""

        if self._user_info is None:
            raise exc.NoSystemConfigError(
                f"{self}: The account information is not (yet) available"
            )

        return self._user_info

    @property
    def location_id(self) -> _LocationIdT:
        """Return the list of locations."""

        if self._user_locs is None:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        return self._user_locs[self._LOC_IDX]["location_id"]

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._user_locs is None:
            raise exc.NoSystemConfigError(
                f"{self}: The installation information is not (yet) available"
            )

        assert self._locations  # mypy hint
        return self._locations
