"""The client for the TCC v1 API."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Final
from warnings import deprecated

from _evohome.const import _ERR_NO_CONFIG
from _evohome.helpers import Case

from . import exceptions as exc
from .auth import AbstractSessionManager, Auth
from .const import SZ_LOCATION_ID, SZ_USER_ID, URL_ACCOUNT_INFO, URL_LOCATIONS
from .entities import Location, create_location
from .exceptions import ClientStateErrorReason, ResponseErrorReason
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
    _user_locs: list[EvoTcsInfoDictT] | None = None  # latest config/status of all locs

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

    async def setup(self) -> None:
        """Retrieve the user information & the configuration of all their locations.

        This is usually called only once, before using the client. In v1, the config
        and status of a location are one GET, so this also retrieves their status. If
        they have already been retrieved, there are no API calls.
        """

        if self._locations is None:
            await self.get_status()

    async def get_status(self) -> list[EvoTcsInfoDictT]:
        """Retrieve the latest state of the user's locations.

        If required, first retrieves the user information and the config of their
        locations.

        There is one API call for the user info (only if required), and a second for
        the config/status of all the user's locations (in v1, these are one GET).

        Logs a warning if the locations are not those of the config (the status of the
        known locations is updated).
        """

        if self._locations is None:  # this GET is (also) of the config
            user_locs = await self._get_config()

        else:
            try:
                user_locs = await self._get_user_locs()
            except exc.BadApiResponseError as err:  # e.g. failed validation
                raise exc.InvalidGetStatusError(
                    err.message, reason=ResponseErrorReason.STATUS_INVALID
                ) from err

            self._user_locs = user_locs

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
    ) -> list[EvoTcsInfoDictT]:
        """Retrieve the latest state of the user's locations.

        Kept for compatibility: use `setup()`, and then `get_status()`.

        If `dont_update_status` is true, does nothing if the config has already been
        retrieved (otherwise, is the same as `get_status()`).
        """

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

    async def _get_account_info(self) -> EvoUserAccountInfoDictT:
        """Get the user's account info, re-authenticating if the session_id is rejected."""

        # if valid, auth.get() sends this id (without yielding), else it fetches another
        session_id = (
            self._session_manager.session_id
            if self._session_manager.is_session_valid()
            else None
        )

        try:
            return await self.auth.get(
                URL_ACCOUNT_INFO,
                schema=SCH_GET_ACCOUNT_INFO,
            )

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

            return await self.auth.get(
                URL_ACCOUNT_INFO,
                schema=SCH_GET_ACCOUNT_INFO,
            )

    async def _get_config(self) -> list[EvoTcsInfoDictT]:
        """Retrieve the user information (if required) & the config of their locations.

        In v1, the config and status of the locations are one GET, so this also
        retrieves their status. A response that is not as expected is an
        InvalidGetConfigError.

        The state is set only once all is retrieved, so a failure leaves none.
        """

        if self._user_info is None:  # will handle session_id rejection
            try:
                self._user_info = await self._get_account_info()
            except exc.BadApiResponseError as err:  # e.g. failed validation
                raise exc.InvalidGetConfigError(
                    err.message, reason=ResponseErrorReason.ACCOUNT_INVALID
                ) from err

        try:
            user_locs = await self._get_user_locs()
        except exc.BadApiResponseError as err:  # e.g. failed validation
            raise exc.InvalidGetConfigError(
                err.message, reason=ResponseErrorReason.CONFIG_INVALID
            ) from err

        locations = [await create_location(self, entry) for entry in user_locs]

        self._user_locs = user_locs
        self._locations = locations
        self._location_by_id = {loc.id: loc for loc in locations}

        return user_locs

    async def _get_user_locs(self) -> list[EvoTcsInfoDictT]:
        """GET the config/status of all the user's locations (in v1, they are one)."""

        return await self.auth.get(
            URL_LOCATIONS.format(user_id=self.user_id),
            schema=SCH_GET_ACCOUNT_LOCS,
        )

    @property
    def user_account(self) -> EvoUserAccountInfoDictT:
        """Return the information of the user account."""

        if self._user_info is None:
            raise exc.NotFetchedError(
                _ERR_NO_CONFIG.format("Account information"),
                reason=ClientStateErrorReason.CONFIG_NOT_FETCHED,
            )

        return self._user_info

    @property
    def user_id(self) -> str:
        """Return the id of the user account (the same id via either API)."""
        return str(self.user_account[SZ_USER_ID])

    @property
    def locations(self) -> list[Location]:
        """Return the list of locations."""

        if self._locations is None:  # None: never fetched, []: fetched but empty
            raise exc.NotFetchedError(
                _ERR_NO_CONFIG.format("Installation information"),
                reason=ClientStateErrorReason.CONFIG_NOT_FETCHED,
            )

        return self._locations

    @property
    def location_by_id(self) -> dict[str, Location]:
        """Return the list of locations."""

        if self._location_by_id is None:  # None: never fetched, {}: fetched but empty
            raise exc.NotFetchedError(
                _ERR_NO_CONFIG.format("Installation information"),
                reason=ClientStateErrorReason.CONFIG_NOT_FETCHED,
            )

        return self._location_by_id

    @property
    @deprecated("EvohomeClient.tcs is deprecated: use Location.tcs")
    def tcs(self) -> ControlSystem:
        """Return the TCS of the account's single location, or raise an exception.

        The majority of users will have only one location, with one TCS.
        """

        if len(locs := self.locations) != 1:
            raise exc.ClientStateError(
                "There is not a single location (only) for this account",
                reason=ClientStateErrorReason.LOCATION_NOT_SINGLE,
            )

        if (tcs := locs[0].tcs) is None:
            raise exc.ClientStateError(
                "The location of this account has no TCS",
                reason=ClientStateErrorReason.LOCATION_NO_TCS,
            )

        return tcs
