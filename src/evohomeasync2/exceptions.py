"""The exceptions raised by the v2 client."""

from __future__ import annotations

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
    NotFetchedError,
    StaleConfigError,
)

__all__ = [
    "ApiCallFailedError",
    "ApiCallRejectedError",
    "ApiRateLimitExceededError",
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
    "NotFetchedError",
    "StaleConfigError",
]
