"""An async client for the v0 Resideo TCC API."""

from __future__ import annotations

from _evohome.exceptions import (
    ApiCallFailedError,
    ApiCallRejectedError,
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
    InvalidConfigError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidStatusError,
    NoSingleTcsError,
    NotFetchedError,
)

__all__ = [
    "ApiCallFailedError",
    "ApiCallRejectedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",  # deprecated alias for ApiCallFailedError
    "AuthRateLimitExceededError",
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadScheduleUploadedError",  # deprecated alias for InvalidScheduleRequestError
    "BadUserCredentialsError",
    "ClientStateError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidScheduleError",
    "InvalidScheduleRequestError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "NotFetchedError",
]
