"""An async client for the v0 Resideo TCC API."""

from __future__ import annotations

from evohome.exceptions import (  # noqa: F401
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiResponseError,
    BadApiSchemaError,
    BadScheduleUploadedError,
    ConfigError,
    EvohomeError,
    InvalidConfigError,
    InvalidScheduleError,
    InvalidStatusError,
    NoSingleTcsError,
    StatusError,
)
