"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _evohome.exceptions import (
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
    deprecated_getattr,
)

if TYPE_CHECKING:  # at runtime, they are served by __getattr__() (and warn)
    from _evohome.exceptions import ApiRequestFailedError, InvalidSystemModeError

__all__ = [
    "ApiCallFailedError",
    "ApiCallRejectedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",  # deprecated alias for ApiCallFailedError
    "AuthRateLimitExceededError",
    "AuthenticationFailedError",
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
