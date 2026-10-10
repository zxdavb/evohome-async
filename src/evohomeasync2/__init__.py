"""evohomeasync provides an async client for the v2 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from _evohome.exceptions import deprecated_getattr

from .auth import AbstractTokenManager
from .comm_task import CommTask
from .const import (
    CommTaskState,
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
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadApiRequestError,
    BadApiResponseError,
    BadUserCredentialsError,
    ClientStateError,
    CommTaskFailedError,
    EvohomeError,
    GhostZoneError,
    InvalidConfigError,
    InvalidModeRequestError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidStatusError,
    NoSingleTcsError,
    NotFetchedError,
    StaleConfigError,
)
from .gateway import Gateway
from .hotwater import HotWater
from .location import Location
from .main import EvohomeClient
from .zone import Zone

if TYPE_CHECKING:  # at runtime, they are served by __getattr__() (and warn)
    from .exceptions import ApiRequestFailedError, InvalidSystemModeError

__all__ = [  # noqa: RUF022
    "EvohomeClient",
    "AbstractTokenManager",
    #
    "Location",
    "Gateway",
    "ControlSystem",
    "Zone",
    "HotWater",
    "CommTask",
    #
    "CommTaskState",
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
    "CommTaskFailedError",
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
    "StaleConfigError",
]

# hidden from type checkers, which would otherwise accept any name in this module
if not TYPE_CHECKING:
    __getattr__ = deprecated_getattr(
        __name__,
        (
            "ApiRequestFailedError",
            "InvalidSystemModeError",
        ),
    )
