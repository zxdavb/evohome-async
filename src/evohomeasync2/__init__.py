"""evohomeasync provides an async client for the v2 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from .auth import AbstractTokenManager
from .const import (
    DayOfWeek,
    DhwState,
    FanMode,
    FaultType,
    LocationType,
    SystemMode,
    TcsModelType,
    TimingMode,
    ZoneMode,
    ZoneModelType,
    ZoneType,
)
from .control_system import ControlSystem
from .exceptions import (
    ApiCallFailedError,
    ApiCallRejectedError,
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadApiRequestError,
    BadApiResponseError,
    BadUserCredentialsError,
    ClientStateError,
    EvohomeError,
    GhostZoneError,
    InvalidConfigError,
    InvalidModeRequestError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidStatusError,
    InvalidSystemModeError,
    NoSingleTcsError,
    NotFetchedError,
)
from .gateway import Gateway
from .hotwater import HotWater
from .location import Location
from .main import EvohomeClient
from .zone import Zone

__all__ = [  # noqa: RUF022
    "EvohomeClient",
    "AbstractTokenManager",
    #
    "Location",
    "Gateway",
    "ControlSystem",
    "Zone",
    "HotWater",
    #
    "DayOfWeek",
    "DhwState",
    "FanMode",
    "FaultType",
    "LocationType",
    "SystemMode",
    "TcsModelType",
    "TimingMode",
    "ZoneMode",
    "ZoneModelType",
    "ZoneType",
    #
    "ApiCallFailedError",
    "ApiCallRejectedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",
    "AuthenticationFailedError",
    "AuthRateLimitExceededError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadUserCredentialsError",
    "ClientStateError",
    "EvohomeError",
    "GhostZoneError",
    "InvalidConfigError",
    "InvalidModeRequestError",
    "InvalidScheduleError",
    "InvalidScheduleRequestError",
    "InvalidStatusError",
    "InvalidSystemModeError",  # deprecated alias for InvalidModeRequestError
    "NoSingleTcsError",
    "NotFetchedError",
]
