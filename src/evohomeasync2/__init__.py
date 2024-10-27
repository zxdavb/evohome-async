#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the *updated* Evohome API.

It is (largely) a faithful port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

import logging
from datetime import datetime as dt

import aiohttp

from .base import EvohomeClient
from .controlsystem import ControlSystem  # noqa: F401
from .exceptions import (  # noqa: F401
    AuthenticationFailed,
    DeprecationError,
    EvohomeError,
    InvalidParameter,
    InvalidSchedule,
    InvalidSchema,
    NoSingleTcsError,
    RateLimitExceeded,
    RequestFailed,
)
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location  # noqa: F401
from .session import AbstractTokenManager, Auth  # noqa: F401
from .zone import Zone  # noqa: F401

__version__ = "1.2.0"

_LOOGER = logging.getLogger(__name__)


class _TokenManager(AbstractTokenManager):
    """A token manager that uses a cache file to store the tokens."""

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

        self.refresh_token = refresh_token or ""
        self.access_token = access_token or ""
        self.access_token_expires = access_token_expires or dt.min

    async def restore_access_token(self) -> None:
        raise NotImplementedError

    async def save_access_token(self) -> None:
        pass


class EvohomeClientOld(EvohomeClient):
    """A wrapper to expose the new EvohomeClient in the old style."""

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        session: None | aiohttp.ClientSession = None,
        debug: bool = False,
    ) -> None:
        """Construct the v2 EvohomeClient object."""

        websession = session or aiohttp.ClientSession()

        self._token_manager = _TokenManager(
            username,
            password,
            websession,
            refresh_token=refresh_token,
            access_token=access_token,
            access_token_expires=access_token_expires,
        )

        super().__init__(self._token_manager, websession, debug=debug)

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
