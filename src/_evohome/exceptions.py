"""The exceptions raised by the v1 and v2 clients.

They are grouped by what the caller can do about them:

  EvohomeError
  │
  ├── ApiCallFailedError                  # no usable reply: fix issue/try again later
  │   ├── ApiRateLimitExceededError       # here, try again later
  │   │   ├── AuthRateLimitExceededError  # - is also an AuthenticationFailedError
  │   ├── AuthenticationFailedError
  │   │   └── BadUserCredentialsError     # correct credentials before trying again
  │   ├── ApiCallRejectedError
  │   └── CommTaskFailedError             # a PUT was accepted, but its task failed
  │
  ├── BadApiRequestError                  # the arguments are unusable (no API call)
  │   ├── InvalidSetModeError
  │   └── InvalidSetScheduleError
  │
  ├── BadApiResponseError                 # the reply is not as expected: report it
  │   ├── InvalidGetConfigError
  │   │   └── GhostZoneError              # a corrupt zone (delete it?)
  │   ├── InvalidGetStatusError
  │   └── InvalidGetScheduleError
  │
  └── ClientStateError                    # the client lacks the data: fetch it first
      ├── NotFetchedError                 # - config, status or schedule data absent
      └── StaleConfigError
"""

from __future__ import annotations

import warnings
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Collection


class _EvohomeBaseError(Exception):
    """The base class for all exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvohomeError(_EvohomeBaseError):
    """The base class for all exceptions."""


# 1. Call failures: there was no usable reply (e.g. no connection, rate limit exceeded,
#    authentication failed); other than for bad credentials, try again later


class ApiCallFailedError(EvohomeError):  # a base exception
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by any aiohttp.ClientError, for example: ConnectionError.  If the
    cause was a ClientResponseError, then the `status` attr will have an integer value.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status  # useful, available if via aiohttp.ClientResponseError


class ApiRateLimitExceededError(ApiCallFailedError):
    """The API request failed because the vendor's API rate limit was exceeded.

    If the vendor said how long to wait before trying again, then the `retry_after`
    attr will have that period, in seconds.
    """

    def __init__(
        self,
        message: str,
        status: int | None = HTTPStatus.TOO_MANY_REQUESTS,  # 429
        *,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status)
        self.retry_after = retry_after


class AuthenticationFailedError(ApiCallFailedError):
    """Unable to authenticate the user credentials (unable to obtain an access token).

    The cause could be any ApiCallFailedError, including ApiRateLimitExceededError.
    """


class AuthRateLimitExceededError(ApiRateLimitExceededError, AuthenticationFailedError):
    """Unable to authenticate because the vendor's API rate limit was exceeded.

    The limit is on how often the user is authenticated, and not on how often their
    locations are polled.
    """


class BadUserCredentialsError(AuthenticationFailedError):
    """Unable to authenticate the user credentials (unknown client_id or wrong secret).

    Reauthenticating will not help as the user credentials are proven to be invalid.
    """


class ApiCallRejectedError(ApiCallFailedError):
    """The vendor rejected the request (a 4xx, other than a 401 or a 429).

    For example, a PUT with a 400 (e.g. SystemModeChangeTimeUntilNotSet), or a GET with
    a 404. The request was sent, but the vendor refused it (so a PUT will not have
    changed anything), and trying again will not help. Unlike a BadApiRequestError,
    the arguments passed this library's checks.
    """


class CommTaskFailedError(ApiCallFailedError):
    """The comm task of a PUT failed (its state is "Failed").

    The PUT was accepted by the vendor, but the change did not reach the system (e.g.
    the gateway is offline).
    """


# 2. Response failures: there was a reply, but it is not as expected; trying again will
#    not help, as either the vendor's JSON or this library's schemas must change. Can be:
#    a) failing schema validation (immediately after a HTTP GET), or (later on)
#    b) internally inconsistent (e.g. a zone without a model type)


class ResponseErrorReason(StrEnum):
    """Why a response was not as expected (see BadApiResponseError).

    The values are public API, so that callers can map each one to their own (e.g.
    translated) message: renaming or removing a member is a breaking change, but
    adding one is not. They are named param_problem (e.g. config_invalid).
    """

    RESPONSE_INVALID = "response_invalid"  # it failed validation (after a GET)
    ACCOUNT_INVALID = "account_invalid"  # e.g. the user account has no user_id
    CONFIG_INVALID = "config_invalid"  # the config failed validation
    MODEL_TYPE_UNKNOWN = "model_type_unknown"  # a zone has no model type (a ghost?)
    ZONE_TYPE_UNKNOWN = "zone_type_unknown"  # a zone has no zone type (a ghost?)
    STATUS_INVALID = "status_invalid"  # the status failed validation
    SCHEDULE_INVALID = "schedule_invalid"  # the schedule failed validation
    SCHEDULE_MISSING = "schedule_missing"  # there is no schedule (e.g. it is empty)
    SWITCHPOINTS_MISSING = "switchpoints_missing"  # e.g. a day without switchpoints
    COMM_TASK_INVALID = "comm_task_invalid"  # a PUT's response is not a comm task
    COMM_TASK_MISMATCHED = "comm_task_mismatched"  # a GET returned another comm task
    TIMESPAN_INVALID = "timespan_invalid"  # e.g. a max_duration is not a TimeSpan


class BadApiResponseError(EvohomeError):  # a base exception
    """The received JSON is not as expected (e.g. missing a required key).

    The `reason` attr says why (see ResponseErrorReason), so that callers need not
    parse the message. This library always supplies a reason, but it is optional (so
    the reason may be None), so that it can still be raised with only a message.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: ResponseErrorReason | None = None,
        **details: str,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.details: dict[str, str] = details


class InvalidGetConfigError(BadApiResponseError):  # config/account JSON is invalid
    """The account/config JSON is not as expected (e.g. an unknown TCS model type)."""


# TODO: deprecate in v4.0, in favour of the reason of an InvalidGetConfigError
class GhostZoneError(InvalidGetConfigError):  # the zone will be ignored
    """The config JSON of a zone has no model type or zone type (is it a ghost zone?).

    Its reason is MODEL_TYPE_UNKNOWN or ZONE_TYPE_UNKNOWN: check the reason of an
    InvalidGetConfigError instead, as this subclass is to be deprecated.
    """


class InvalidGetStatusError(BadApiResponseError):  # status JSON is invalid
    """The status JSON is not as expected (e.g. an unknown fault type)."""


class InvalidGetScheduleError(BadApiResponseError):  # schedule JSON is invalid/missing
    """The schedule JSON is not as expected, or there is no schedule.

    This is a schedule from the vendor (e.g. via get_schedule()): see
    InvalidSetScheduleError for a schedule supplied by the caller.
    """


# 3. Request failures: the supplied arguments are unusable (e.g. an unsupported zone
#    mode); these are detected before making any API request, so nothing was sent


class RequestErrorReason(StrEnum):
    """Why a request was rejected, before any API call (see BadApiRequestError).

    The values are public API, so that callers can map each one to their own (e.g.
    translated) message: renaming or removing a member is a breaking change, but
    adding one is not. They are named param_problem (e.g. mode_unknown).
    """

    # the mode of a TCS/zone/DHW (see InvalidSetModeError)
    MODE_UNKNOWN = "mode_unknown"  # the mode is not a valid enum value
    MODE_UNSUPPORTED = "mode_unsupported"  # the mode is not among the allowed modes
    TIMESPAN_REQUIRED = "timespan_required"  # the mode cannot be permanent
    TIMESPAN_NOT_ALLOWED = "timespan_not_allowed"  # the mode can only be permanent
    TIMESPAN_CONFLICTING = "timespan_conflicting"  # e.g. both an until and a duration
    TIMESPAN_UNSUPPORTED = "timespan_unsupported"  # e.g. a duration, for a period mode
    TIMESPAN_INVALID = "timespan_invalid"  # e.g. a naive until, or not a datetime
    TIMESPAN_OUT_OF_RANGE = "timespan_out_of_range"  # too large for a datetime
    TIMESPAN_NOT_IN_FUTURE = "timespan_not_in_future"  # it would have ended already
    TEMPERATURE_REQUIRED = "temperature_required"
    TEMPERATURE_NOT_ALLOWED = "temperature_not_allowed"
    TEMPERATURE_INVALID = "temperature_invalid"  # e.g. NaN, or infinity
    STATE_REQUIRED = "state_required"
    STATE_NOT_ALLOWED = "state_not_allowed"
    STATE_UNKNOWN = "state_unknown"  # the state is not a valid enum value
    STATE_UNSUPPORTED = "state_unsupported"  # the state is not among allowed states

    # other requests
    DATETIME_INVALID = "datetime_invalid"  # e.g. a naive datetime, or not a datetime
    SCHEDULE_INVALID = "schedule_invalid"  # e.g. not JSON (or not serializable)
    ZONE_UNKNOWN = "zone_unknown"  # e.g. no zone with that id/idx/name


class BadApiRequestError(EvohomeError):  # a base exception
    """The supplied parameter(s) are not as expected (e.g. unknown/unsupported mode).

    The `reason` attr says why (see RequestErrorReason), so that callers need not parse
    the message. The `details` attr holds only the structured values that apply to the
    reason, for use as the placeholders of a (translated) message (see the subclasses).

    This library always supplies a reason, but it is optional (so the reason may be
    None), so that it can still be raised with only a message (e.g. by a test double).
    """

    def __init__(
        self,
        message: str,
        *,
        reason: RequestErrorReason | None = None,
        **details: str,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.details: dict[str, str] = details


class InvalidSetModeError(BadApiRequestError):  # failed to set a TCS/zone/DHW mode
    """The requested mode is not supported by this TCS/zone/DHW zone.

    Its `details` may have these keys, for use as a message's placeholders:
      mode:         the mode (a snake_case enum value, or the raw input if unknown)
      timing_mode:  the timing mode that the mode's entry expects
      state:        the DHW state (a snake_case enum value, or the raw input if unknown)
      max_duration: the mode's max_duration (reserved: no reason supplies it, yet)

    Which keys are present depends upon the reason (e.g. TIMESPAN_CONFLICTING has none),
    so a message for a reason may only use the placeholders that its reason supplies.
    """


class InvalidSetScheduleError(BadApiRequestError):  # failed to set a schedule
    """The supplied schedule JSON is not supported / is invalid.

    This is a schedule supplied by the caller (e.g. via set_schedule()): see
    InvalidGetScheduleError for a schedule from the vendor.
    """


# 4. State failures: the client does not hold the data needed to answer (after/without
#    a successful API call); fetch the data first


class ClientStateError(EvohomeError):  # a base exception
    """The client's config/status data cannot provide what was asked for."""


class NotFetchedError(ClientStateError):
    """The config/status/schedule JSON has not been fetched yet.

    This is likely because the user has not yet called `EvohomeClient.setup()`,
    `Location.get_status()`, `HotWater.get_schedule()` or `Zone.get_schedule()`.
    """


class StaleConfigError(ClientStateError):
    """The config JSON is inconsistent with the latest status JSON.

    For example, an entity (e.g. a zone) that is in the config is absent from the
    status, or a location is no longer accessible. This is likely because the
    installation has been changed since the config was fetched.
    """


# Backward-compatibility aliases (deprecated names, e.g. as used by the HA integration):
# each is its replacement, but is served by a module __getattr__() that warns when it is
# accessed (e.g. imported, or evaluated in an except clause)
# The previous names of these errors, before they were named after the method (set_*,
# get_*) that raises them; they are still used, e.g. by HA, so do not (yet) warn
# TODO: deprecate in v4.0 (i.e. move them into _DEPRECATED_ALIASES, below)
InvalidConfigError = InvalidGetConfigError
InvalidModeRequestError = InvalidSetModeError
InvalidScheduleError = InvalidGetScheduleError
InvalidScheduleRequestError = InvalidSetScheduleError
InvalidStatusError = InvalidGetStatusError


_DEPRECATED_ALIASES: Final[dict[str, type[EvohomeError]]] = {
    "ApiRequestFailedError": ApiCallFailedError,  # renamed to ApiCallFailedError
    "InvalidSystemModeError": InvalidSetModeError,  # merged into it
}

if TYPE_CHECKING:  # at runtime, they are served by __getattr__(), below
    ApiRequestFailedError = ApiCallFailedError
    InvalidSystemModeError = InvalidSetModeError


def deprecated_getattr(
    module: str,
    names: Collection[str],
) -> Callable[[str], type[EvohomeError]]:
    """Return a module __getattr__() that serves the named deprecated aliases.

    Each access to an alias emits a DeprecationWarning that names its replacement, and
    is attributed to the caller's line (e.g. its import, or its except clause).
    """

    def module_getattr(name: str) -> type[EvohomeError]:
        if name not in names:
            raise AttributeError(f"module {module!r} has no attribute {name!r}")

        new = _DEPRECATED_ALIASES[name]
        warnings.warn(
            f"{name} is deprecated: use {new.__name__} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return new

    return module_getattr


# hidden from type checkers, which would otherwise accept any name in this module
if not TYPE_CHECKING:
    __getattr__ = deprecated_getattr(__name__, _DEPRECATED_ALIASES)
