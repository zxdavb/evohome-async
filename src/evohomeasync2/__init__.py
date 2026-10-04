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
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiResponseError,
    BadApiSchemaError,
    BadScheduleUploadedError,
    BadUserCredentialsError,
    ConfigError,
    EvohomeError,
    InvalidConfigError,
    InvalidDhwModeError,
    InvalidScheduleError,
    InvalidStatusError,
    InvalidSystemModeError,
    InvalidZoneModeError,
    NoSingleTcsError,
    StatusError,
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
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadApiSchemaError",
    "BadScheduleUploadedError",
    "BadUserCredentialsError",
    "ConfigError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidDhwModeError",
    "InvalidScheduleError",
    "InvalidStatusError",
    "InvalidSystemModeError",
    "InvalidZoneModeError",
    "NoSingleTcsError",
    "StatusError",
]
