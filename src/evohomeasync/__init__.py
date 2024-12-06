#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td

import aiohttp

from .auth import AbstractSessionManager
from .exceptions import (  # noqa: F401
    AuthenticationFailedError,
    EvohomeError,
    InvalidSchemaError,
    RateLimitExceededError,
    RequestFailedError,
)
from .main import EvohomeClientNew as _EvohomeClientNew
from .schemas import (  # noqa: F401
    SZ_ALLOWED_MODES,
    SZ_CHANGEABLE_VALUES,
    SZ_DEVICE_ID,
    SZ_DEVICES,
    SZ_DHW_OFF,
    SZ_DHW_ON,
    SZ_DOMESTIC_HOT_WATER,
    SZ_EMEA_ZONE,
    SZ_HEAT_SETPOINT,
    SZ_HOLD,
    SZ_ID,
    SZ_INDOOR_TEMPERATURE,
    SZ_LOCATION_ID,
    SZ_MODE,
    SZ_NAME,
    SZ_NEXT_TIME,
    SZ_QUICK_ACTION,
    SZ_QUICK_ACTION_NEXT_TIME,
    SZ_SCHEDULED,
    SZ_SETPOINT,
    SZ_STATUS,
    SZ_TEMP,
    SZ_TEMPORARY,
    SZ_THERMOSTAT,
    SZ_THERMOSTAT_MODEL_TYPE,
    SZ_USER_INFO,
    SZ_VALUE,
)

__version__ = "1.2.0"


class _SessionManager(AbstractSessionManager):  # used only by EvohomeClientOld
    """A TokenManager wrapper to help expose the refactored EvohomeClient."""

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        session_id: str | None = None,
    ) -> None:
        super().__init__(username, password, websession)

        # to maintain compatibility, allow these to be passed in here
        if session_id:
            self._session_id = session_id
            self._session_id_expires = dt.now(tz=UTC) + td(minutes=15)  # best scenario

    async def load_session_id(self) -> None:
        raise NotImplementedError

    async def save_session_id(self) -> None:
        pass


class EvohomeClientOld(_EvohomeClientNew):
    """A wrapper to use EvohomeClient without passing in a SessionManager.

    Also permits a session_id to be passed in.
    """

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        session_id: str | None = None,
        websession: aiohttp.ClientSession | None = None,
        debug: bool = False,
    ) -> None:
        """Construct the v0 EvohomeClient object."""
        websession = websession or aiohttp.ClientSession()

        self._session_manager = _SessionManager(
            username,
            password,
            websession,
            session_id=session_id,
        )
        super().__init__(self._session_manager, debug=debug)


class EvohomeClient(_EvohomeClientNew):
    """An async client for v0 of the Resideo TCC API."""
