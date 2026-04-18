"""An async client for the v0 Resideo TCC API."""

from __future__ import annotations

from _evohome.exceptions import (
    ApiCallFailedError,
    ApiRateLimitExceededError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiResponseError,
    BadApiSchemaError,
    BadScheduleUploadedError,
    BadUserCredentialsError,
    ConfigError,
    EvohomeError,
    InvalidConfigError,
    InvalidScheduleError,
    InvalidStatusError,
    NoSingleTcsError,
    StatusError,
)

__all__ = [
    "ApiCallFailedError",
    "ApiRateLimitExceededError",
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadApiSchemaError",
    "BadScheduleUploadedError",
    "BadUserCredentialsError",
    "ConfigError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidScheduleError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "StatusError",
]
