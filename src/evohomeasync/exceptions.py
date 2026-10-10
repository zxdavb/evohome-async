"""An async client for the v0 Resideo TCC API."""

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
    EvohomeError,
    InvalidConfigError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidStatusError,
    NoSingleTcsError,
    NotFetchedError,
    deprecated_getattr,
)

if TYPE_CHECKING:  # at runtime, they are served by __getattr__() (and warn)
    from _evohome.exceptions import ApiRequestFailedError

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
    "EvohomeError",
    "InvalidConfigError",
    "InvalidScheduleError",
    "InvalidScheduleRequestError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "NotFetchedError",
]

# hidden from type checkers, which would otherwise accept any name in this module
if not TYPE_CHECKING:
    __getattr__ = deprecated_getattr(__name__, ("ApiRequestFailedError",))
