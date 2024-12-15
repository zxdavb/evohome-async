"""evohomeasync provides an async client for the v2 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from datetime import UTC, datetime as dt

import aiohttp

from .auth import AbstractTokenManager
from .control_system import ControlSystem  # noqa: F401
from .exceptions import (  # noqa: F401
    ApiRequestFailedError,
    AuthenticationFailedError,
    EvohomeError,
    InvalidParameterError,
    InvalidScheduleError,
    InvalidSchemaError,
    NoSingleTcsError,
    NoSystemConfigError,
    RateLimitExceededError,
    SystemConfigError,
)
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location  # noqa: F401
from .main import EvohomeClientNew as _EvohomeClientNew
from .zone import Zone  # noqa: F401

__version__ = "1.2.0"


class _TokenManager(AbstractTokenManager):  # used only by EvohomeClientOld
    """A TokenManager wrapper to help expose the refactored EvohomeClient."""

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        access_token: str | None = None,
        access_token_expires: dt | None = None,  # should be aware
        refresh_token: str | None = None,
    ) -> None:
        super().__init__(username, password, websession)

        # to maintain compatibility, allow these to be passed in here
        if access_token_expires is not None and not access_token_expires.tzinfo:
            access_token_expires = access_token_expires.replace(tzinfo=UTC)

        self._access_token_expires = access_token_expires or dt.min.replace(tzinfo=UTC)
        self._access_token = access_token or ""
        self._refresh_token = refresh_token or ""

    async def load_access_token(self) -> None:
        raise NotImplementedError

    async def save_access_token(self) -> None:
        pass


class EvohomeClientOld(_EvohomeClientNew):
    """A wrapper to use EvohomeClient without passing in a TokenManager.

    Also allows auth tokens to be passed in.
    """

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object."""
        websession = websession or aiohttp.ClientSession()

        self._token_manager = _TokenManager(
            username,
            password,
            websession,
            refresh_token=refresh_token,
            access_token=access_token,
            access_token_expires=access_token_expires,
        )
        super().__init__(self._token_manager, debug=debug)

    @property
    def access_token(self) -> str:
        """Return the access_token attr."""
        return self._token_manager.access_token

    @property
    def access_token_expires(self) -> dt:
        """Return the access_token_expires attr."""
        return self._token_manager.access_token_expires

    @property
    def refresh_token(self) -> str:
        """Return the refresh_token attr."""
        return self._token_manager.refresh_token

    @property
    def username(self) -> str:
        """Return the username attr."""
        return self._token_manager.client_id


class EvohomeClient(_EvohomeClientNew):
    """An async client for v2 of the Resideo TCC API."""
