"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations

from _evohome.exceptions import (
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

__all__ = [
    "ApiCallFailedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",  # deprecated alias for ApiCallFailedError
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
