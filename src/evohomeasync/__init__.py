"""evohomeasync provides an async client for the v0 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from typing import Self

import aiohttp

from .auth import AbstractSessionManager
from .entities import ControlSystem, Gateway, HotWater, Location, Zone
from .exceptions import (
    ApiCallFailedError,
    ApiCallRejectedError,
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadApiRequestError,
    BadApiResponseError,
    BadScheduleUploadedError,
    BadUserCredentialsError,
    ClientStateError,
    EvohomeError,
    InvalidConfigError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidStatusError,
    NoSingleTcsError,
    NotFetchedError,
)
from .main import EvohomeClient
from .schemas import (  # noqa: F401
    S1_ALLOWED_MODES as SZ_ALLOWED_MODES,
    S1_CHANGEABLE_VALUES as SZ_CHANGEABLE_VALUES,
    S1_DEVICE_ID as SZ_DEVICE_ID,
    S1_DEVICES as SZ_DEVICES,
    S1_HEAT_SETPOINT as SZ_HEAT_SETPOINT,
    S1_INDOOR_TEMPERATURE as SZ_INDOOR_TEMPERATURE,
    S1_LOCATION_ID as SZ_LOCATION_ID,
    S1_MODE as SZ_MODE,
    S1_NAME as SZ_NAME,
    S1_NEXT_TIME as SZ_NEXT_TIME,
    S1_QUICK_ACTION as SZ_QUICK_ACTION,
    S1_QUICK_ACTION_NEXT_TIME as SZ_QUICK_ACTION_NEXT_TIME,
    S1_STATUS as SZ_STATUS,
    S1_THERMOSTAT as SZ_THERMOSTAT,
    S1_THERMOSTAT_MODEL_TYPE as SZ_THERMOSTAT_MODEL_TYPE,
    S1_USER_INFO as SZ_USER_INFO,
    S1_VALUE as SZ_VALUE,
    TccCommTaskState,
    TccDhwMode,
    TccEquipmentOutputStatus,
    TccLocationType,
    TccSensorStatus,
    TccSetpointStatus,
    TccSystemMode,
    TccThermostatMode,
    TccThermostatModelType,
)


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


class EvohomeClientOld(EvohomeClient):
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

        self._owns_session = websession is None
        websession = websession or aiohttp.ClientSession()

        self._session_manager = _SessionManager(
            username,
            password,
            websession,
            session_id=session_id,
        )
        super().__init__(self._session_manager, debug=debug)

    async def close(self) -> None:
        """Close the owned aiohttp.ClientSession, if any."""
        if self._owns_session:
            await self._session_manager.websession.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


__all__ = [  # noqa: RUF022
    "EvohomeClient",
    "AbstractSessionManager",
    #
    "Location",
    "Gateway",
    "ControlSystem",
    "Zone",
    "HotWater",
    #
    "TccCommTaskState",
    "TccDhwMode",
    "TccEquipmentOutputStatus",
    "TccLocationType",
    "TccSensorStatus",
    "TccSetpointStatus",
    "TccSystemMode",
    "TccThermostatMode",
    "TccThermostatModelType",
    #
    "ApiCallFailedError",
    "ApiCallRejectedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",
    "AuthenticationFailedError",
    "AuthRateLimitExceededError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadScheduleUploadedError",
    "BadUserCredentialsError",
    "ClientStateError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidScheduleError",
    "InvalidScheduleRequestError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "NotFetchedError",
]
