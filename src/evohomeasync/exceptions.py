"""An async client for the v0 Resideo TCC API."""

from __future__ import annotations

from evohome.exceptions import (
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
    InvalidScheduleError,
    InvalidStatusError,
    NoSingleTcsError,
    StatusError,
)

__all__ = [
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
    "InvalidScheduleError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "StatusError",
]
