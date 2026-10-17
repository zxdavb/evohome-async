"""evohomeasync provides an async client for the v1 Resideo TCC API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from warnings import deprecated

from _evohome.const import _ERR_NO_CONFIG
from _evohome.helpers import Case

from . import exceptions as exc
from .auth import AbstractSessionManager, Auth
from .const import SZ_LOCATION_ID, SZ_USER_ID
from .entities import Location, create_location
from .schemas import factory_location_response_list, factory_user_account_info_response

if TYPE_CHECKING:
    import aiohttp

    from _evohome.helpers import Validator

    from .entities import ControlSystem
    from .typedefs import EvoTcsInfoDictT, EvoUserAccountInfoDictT

SCH_GET_ACCOUNT_INFO: Final[Validator[EvoUserAccountInfoDictT]] = (
    factory_user_account_info_response(Case.PYTHONIC)
)
SCH_GET_ACCOUNT_LOCS: Final[Validator[list[EvoTcsInfoDictT]]] = (
    factory_location_response_list(Case.PYTHONIC)
)

_LOGGER = logging.getLogger(__name__.rpartition(".")[0])  # "evohomeasync"


class EvohomeClient:
    """Provide a client to access the Resideo TCC API."""

    _user_info: EvoUserAccountInfoDictT | None = None
    _user_locs: list[EvoTcsInfoDictT] | None = None  # all locations of the user

    def __init__(
        self,
        session_manager: AbstractSessionManager,
        /,
        *,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v1 EvohomeClient object."""

        self._logger = _LOGGER
        if debug:
            self._logger.setLevel(logging.DEBUG)
            self._logger.debug("Debug mode explicitly enabled via kwarg.")

        self._session_manager = session_manager
        self.auth = Auth(session_manager, websession or session_manager.websession)

        # self.devices: dict[_ZoneIdT, _DeviceDictT] = {}  # dhw or zone by id
        # self.named_devices: dict[_ZoneNameT, _DeviceDictT] = {}  # zone by name

        self._locations: list[Location] | None = None  # to preserve the order
        self._location_by_id: dict[str, Location] | None = None

        self._stale_config: str | None = None  # the last warning, so is logged once

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(auth='{self.auth}')"

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    async def setup(self, *, _reset_config: bool = False) -> None:
        """Retrieve the user information & the configuration of all their locations.

        This is usually called only once, before using the client. In v1, the config
        and status of a location are one GET, so this also retrieves their status.
        """

        await self.get_status(_reset_config=_reset_config)

    async def get_status(self, *, _reset_config: bool = False) -> list[EvoTcsInfoDictT]:
        """Retrieve the latest state of the user's locations.

        If required (or when `_reset_config` is true, for use by the test suite), first
        retrieves the user information.

        There is one API call for the user info, and a second for the config/status of
        all the user's locations (in v1, these are one GET).

        Logs a warning if the locations are not those of the config (the status of the
        known locations is updated).
        """

        if _reset_config:
            self._clear_config()

        self._user_locs = None  # the locations (config & status) are always re-fetched

        try:
            user_locs = await self._get_config()
        except exc.BadApiResponseError as err:  # e.g. failed validation
            if self._locations is None:  # the entities are yet to be instantiated
                raise exc.InvalidConfigError(err.message) from err
            raise exc.InvalidStatusError(err.message) from err

        assert self._location_by_id is not None  # mypy

        for loc_entry in user_locs:  # each entry is both config & status
            loc_id = str(loc_entry[SZ_LOCATION_ID])
            if loc_id not in self._location_by_id:  # added since config was fetched
                continue
            self._location_by_id[loc_id]._update_status(loc_entry)  # noqa: SLF001

        self._warn_if_stale_config(user_locs)

        return user_locs

    @deprecated(
        "EvohomeClient.update() is deprecated: use .setup(), then .get_status()"
    )
    async def update(
        self,
        /,
        *,
        dont_update_status: bool = False,
        _reset_config: bool = False,  # for use by test suite
    ) -> list[EvoTcsInfoDictT]:
        """Retrieve the latest state of the user's locations.

        Kept for compatibility: use `setup()`, and then `get_status()`.

        If `dont_update_status` is true, does nothing if the config has already been
        retrieved (otherwise, is the same as `get_status()`).
        """

        if _reset_config:
            self._clear_config()

        if dont_update_status and self._user_locs is not None:
            return self._user_locs

        return await self.get_status()

    def _clear_config(self) -> None:
        """Clear the user information & the config of their locations."""

        self._user_info = None
        self._user_locs = None

        self._locations = None
        self._location_by_id = None

    def _warn_if_stale_config(self, user_locs: list[EvoTcsInfoDictT]) -> None:
        """Log a warning (only once) if the locations are not those of the config."""

        assert self._location_by_id is not None  # mypy

        loc_ids = {str(loc_entry[SZ_LOCATION_ID]) for loc_entry in user_locs}

        problems = [
            f"no entry for location_id='{loc_id}'"
            for loc_id in sorted(self._location_by_id.keys() - loc_ids)
        ] + [
            f"location_id='{loc_id}' not known"
            for loc_id in sorted(loc_ids - self._location_by_id.keys())
        ]

        msg = (
            f"{self}: status has {', '.join(problems)}"
            ", (has the account configuration changed?)"
            if problems
            else None
        )

        if msg and msg != self._stale_config:
            self._logger.warning(msg)
        self._stale_config = msg

    async def _get_config(self) -> list[EvoTcsInfoDictT]:
        """Ensures the config of the user and their locations.

        If required, first retrieves the user information & installation configuration.
        """

        if self._user_info is None:  # will handle session_id rejection
            url = "accountInfo"

            # if valid, auth.get() sends this id (without yielding), else it fetches another
            session_id = (
                self._session_manager.session_id
                if self._session_manager.is_session_valid()
                else None
            )

            try:
                self._user_info = await self.auth.get(url, schema=SCH_GET_ACCOUNT_INFO)

            except exc.AuthenticationFailedError:  # unable to get a session_id
                raise

            except exc.ApiCallFailedError as err:  # check if 401 - bad session_id
                if err.status != HTTPStatus.UNAUTHORIZED:  # 401
                    raise

                # as the accountInfo URL is open to all authenticated users, any 401 is
                # due the (albeit valid) session_id being rejected by the server

                self._logger.warning(
                    f"The session_id has been rejected (will re-authenticate): {err}"
                )

                # another task may have since refreshed it, so don't clear the new one
                if session_id is None or self._session_manager.session_id == session_id:
                    self._session_manager.clear_session_id()
                self._user_info = await self.auth.get(url, schema=SCH_GET_ACCOUNT_INFO)

            assert self._user_info is not None  # mypy

        if self._user_locs is None:
            try:
                user_id = self._user_info[SZ_USER_ID]
            except (KeyError, TypeError) as err:
                raise exc.BadApiResponseError(
                    f"No user_id in user_info dict. Received: {self._user_info}"
                ) from err

            self._user_locs = await self.auth.get(
                f"locations?userId={user_id}&allData=True", schema=SCH_GET_ACCOUNT_LOCS
            )

            assert self._user_locs is not None  # mypy

        if self._locations is None:
            self._locations = []
            self._location_by_id = {}

            for loc_entry in self._user_locs:  # each entry is both config & status
                loc = await create_location(self, loc_entry)
                self._locations.append(loc)
                self._location_by_id[loc.id] = loc

            #
            #

        return self._user_locs

    @property
    def user_account(self) -> EvoUserAccountInfoDictT:
        """Return the information of the user account."""

        if self._user_info is None:
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Account information"))

        return self._user_info

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._locations is None:  # None: never fetched, []: fetched but empty
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Installation information"))

        return self._locations

    @property
    def location_by_id(self) -> dict[str, Location]:
        """Return the list of locations."""

        if self._location_by_id is None:  # None: never fetched, {}: fetched but empty
            raise exc.NotFetchedError(_ERR_NO_CONFIG.format("Installation information"))

        return self._location_by_id

    @property
    @deprecated("EvohomeClient.tcs is deprecated: use Location.tcs")
    def tcs(self) -> ControlSystem:
        """Return the TCS of the account's single location, or raise an exception.

        The majority of users will have only one location, with one TCS.
        """

        if len(locs := self.locations) != 1:
            raise exc.ClientStateError(
                "There is not a single location (only) for this account"
            )

        if (tcs := locs[0].tcs) is None:
            raise exc.ClientStateError("The location of this account has no TCS")

        return tcs
