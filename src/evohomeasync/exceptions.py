"""The exceptions raised by the v1 client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _evohome.exceptions import (
    ApiCallErrorReason,
    ApiCallFailedError,
    ApiCallRejectedError,
    ApiRateLimitExceededError,
    AuthenticationFailedError,
    AuthRateLimitExceededError,
    BadApiRequestError,
    BadApiResponseError,
    BadUserCredentialsError,
    ClientStateError,
    ClientStateErrorReason,
    CommTaskFailedError,
    EvohomeError,
    InvalidConfigError,
    InvalidGetConfigError,
    InvalidGetScheduleError,
    InvalidGetStatusError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidSetScheduleError,
    InvalidStatusError,
    NotFetchedError,
    RequestErrorReason,
    ResponseErrorReason,
    deprecated_getattr,
)

if TYPE_CHECKING:  # at runtime, they are served by __getattr__() (and warn)
    from _evohome.exceptions import ApiRequestFailedError

__all__ = [
    "ApiCallErrorReason",
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
    "ClientStateErrorReason",
    "CommTaskFailedError",
    "EvohomeError",
    "InvalidConfigError",  # TODO: deprecate in v4.0 (an alias of InvalidGetConfigError)
    "InvalidGetConfigError",
    "InvalidGetScheduleError",
    "InvalidGetStatusError",
    "InvalidScheduleError",  # TODO: deprecate in v4.0 (an alias of InvalidGetScheduleError)
    "InvalidScheduleRequestError",  # TODO: deprecate in v4.0 (an alias of InvalidSetScheduleError)
    "InvalidSetScheduleError",
    "InvalidStatusError",  # TODO: deprecate in v4.0 (an alias of InvalidGetStatusError)
    "NotFetchedError",
    "RequestErrorReason",
    "ResponseErrorReason",
]

# hidden from type checkers, which would otherwise accept any name in this module
if not TYPE_CHECKING:
    __getattr__ = deprecated_getattr(__name__, ("ApiRequestFailedError",))
