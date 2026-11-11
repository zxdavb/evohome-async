"""The exceptions raised by the v2 client."""

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
    InvalidGetConfigError,
    InvalidGetScheduleError,
    InvalidGetStatusError,
    InvalidModeRequestError,
    InvalidScheduleError,
    InvalidScheduleRequestError,
    InvalidSetModeError,
    InvalidSetScheduleError,
    InvalidStatusError,
    NotFetchedError,
    RequestErrorReason,
    ResponseErrorReason,
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
    "InvalidConfigError",  # TODO: deprecate in v4.0 (an alias of InvalidGetConfigError)
    "InvalidGetConfigError",
    "InvalidGetScheduleError",
    "InvalidGetStatusError",
    "InvalidModeRequestError",  # TODO: deprecate in v4.0 (an alias of InvalidSetModeError)
    "InvalidScheduleError",  # TODO: deprecate in v4.0 (an alias of InvalidGetScheduleError)
    "InvalidScheduleRequestError",  # TODO: deprecate in v4.0 (an alias of InvalidSetScheduleError)
    "InvalidSetModeError",
    "InvalidSetScheduleError",
    "InvalidStatusError",  # TODO: deprecate in v4.0 (an alias of InvalidGetStatusError)
    "InvalidSystemModeError",  # deprecated alias for InvalidSetModeError
    "NotFetchedError",
    "RequestErrorReason",
    "ResponseErrorReason",
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
