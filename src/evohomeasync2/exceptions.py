"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations

from _evohome.exceptions import (
    ApiCallFailedError,
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
    GhostZoneError,
    InvalidConfigError,
    InvalidDhwModeError,
    InvalidScheduleError,
    InvalidScheduleUploadedError,
    InvalidStatusError,
    InvalidSystemModeError,
    InvalidZoneModeError,
    NoSingleTcsError,
    NotFetchedError,
    StaleConfigError,
)

__all__ = [
    "ApiCallFailedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",  # deprecated alias for ApiCallFailedError
    "AuthRateLimitExceededError",
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadScheduleUploadedError",  # deprecated alias for InvalidScheduleUploadedError
    "BadUserCredentialsError",
    "ClientStateError",
    "EvohomeError",
    "GhostZoneError",
    "InvalidConfigError",
    "InvalidDhwModeError",
    "InvalidScheduleError",
    "InvalidScheduleUploadedError",
    "InvalidStatusError",
    "InvalidSystemModeError",
    "InvalidZoneModeError",
    "NoSingleTcsError",
    "NotFetchedError",
    "StaleConfigError",
]
