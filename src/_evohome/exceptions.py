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
from enum import EnumCheck, StrEnum, verify
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Final

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
    """The comm task of a PUT failed, or there is no comm task to follow.

    The PUT was accepted by the vendor, but either its task failed (its state is
    "Failed"), so the change did not reach the system (e.g. the gateway is offline),
    or the response was not a comm task, so whether it will is unknown.
    """


# 2. Response failures: there was a reply, but it is not as expected; trying again will
#    not help, as either the vendor's JSON or this library's schemas must change. Can be:
#    a) failing schema validation (immediately after a HTTP GET), or (later on)
#    b) internally inconsistent (e.g. a zone without a model type)


@verify(EnumCheck.UNIQUE)
class ResponseErrorReason(StrEnum):
    """Why a response was not as expected (see BadApiResponseError).

    The values are public API, so that callers can map each one to their own (e.g.
    translated) message: renaming or removing a member is a breaking change, but
    adding one is not. They are named PARAM_PROBLEM, and their values are prefixed
    get_, so that they are unique (e.g. CONFIG_INVALID = get_config_invalid).
    """

    RESPONSE_INVALID = "get_response_invalid"  # it failed validation (a GET)

    ACCOUNT_INVALID = "get_account_invalid"  # it failed validation (e.g. no user_id)
    COMM_TASK_MISMATCHED = "get_comm_task_mismatched"  # a GET's response
    CONFIG_INVALID = "get_config_invalid"  # it failed validation
    SCHEDULE_INVALID = "get_schedule_invalid"  # it failed validation
    SCHEDULE_MISSING = "get_schedule_missing"  # e.g. it is empty
    STATUS_INVALID = "get_status_invalid"  # it failed validation
    SWITCHPOINTS_MISSING = "get_switchpoints_missing"  # e.g. for a day
    TIMESPAN_INVALID = "get_timespan_invalid"  # e.g. of a max_duration
    ZONE_INVALID = "get_zone_invalid"  # a catch-all for invalid zones
    ZONE_MODEL_UNKNOWN = "get_zone_model_unknown"  # of a zone (a ghost zone?)
    ZONE_TYPE_UNKNOWN = "get_zone_type_unknown"  # of a zone (a ghost zone?)


class BadApiResponseError(EvohomeError):  # a base exception
    """The received JSON is not as expected (e.g. missing a required key).

    The `reason` attr says why (see ResponseErrorReason), so that callers need not
    parse the message. This library always supplies a reason, but it is optional, so
    that the error can still be raised with only a message: then its reason is the
    class's default (e.g. STATUS_INVALID, for an InvalidGetStatusError), so is never
    None.
    """

    _default_reason: ClassVar[ResponseErrorReason] = (
        ResponseErrorReason.RESPONSE_INVALID
    )

    def __init__(
        self,
        message: str,
        *,
        reason: ResponseErrorReason | None = None,
        **details: str,
    ) -> None:
        super().__init__(message)
        self.reason = reason or self._default_reason  # never None
        self.details: dict[str, str] = details


class InvalidGetConfigError(BadApiResponseError):  # config/account JSON is invalid
    """The account/config JSON is not as expected (e.g. an unknown TCS model type)."""

    _default_reason: ClassVar[ResponseErrorReason] = ResponseErrorReason.CONFIG_INVALID


# TODO: deprecate in v4.0, in favour of the reason of an InvalidGetConfigError
class GhostZoneError(InvalidGetConfigError):  # the zone will be ignored
    """The config JSON of a zone has no model type or zone type (is it a ghost zone?).

    Its reason is usually ZONE_MODEL_UNKNOWN or ZONE_TYPE_UNKNOWN: check the reason
    of an InvalidGetConfigError instead, as this subclass is to be deprecated.
    """

    _default_reason: ClassVar[ResponseErrorReason] = ResponseErrorReason.ZONE_INVALID


class InvalidGetStatusError(BadApiResponseError):  # status JSON is invalid
    """The status JSON is not as expected (e.g. an unknown fault type)."""

    _default_reason: ClassVar[ResponseErrorReason] = ResponseErrorReason.STATUS_INVALID


class InvalidGetScheduleError(BadApiResponseError):  # schedule JSON is invalid/missing
    """The schedule JSON is not as expected, or there is no schedule.

    This is a schedule from the vendor (e.g. via get_schedule()): see
    InvalidSetScheduleError for a schedule supplied by the caller.
    """

    _default_reason: ClassVar[ResponseErrorReason] = (
        ResponseErrorReason.SCHEDULE_INVALID
    )


# 3. Request failures: the supplied arguments are unusable (e.g. an unsupported zone
#    mode); these are detected before making any API request, so nothing was sent


@verify(EnumCheck.UNIQUE)
class RequestErrorReason(StrEnum):
    """Why a request was rejected, before any API call (see BadApiRequestError).

    The values are public API, so that callers can map each one to their own (e.g.
    translated) message: renaming or removing a member is a breaking change, but
    adding one is not. They are named PARAM_PROBLEM, and their values are prefixed
    set_, so that they are unique (e.g. MODE_UNKNOWN = set_mode_unknown).
    """

    REQUEST_INVALID = "set_request_invalid"  # a generic catch-all

    # the mode of a TCS/zone/DHW (see InvalidSetModeError)
    MODE_INVALID = "set_mode_invalid"  # a generic catch-all for invalid modes
    MODE_UNKNOWN = "set_mode_unknown"  # the mode is not a valid enum value
    MODE_UNSUPPORTED = "set_mode_unsupported"  # the mode is not among the allowed modes
    TIMESPAN_REQUIRED = "set_timespan_required"  # the mode cannot be permanent
    TIMESPAN_NOT_ALLOWED = "set_timespan_not_allowed"  # the mode can only be permanent
    TIMESPAN_CONFLICTING = "set_timespan_conflicting"  # e.g. an until and a duration
    TIMESPAN_UNSUPPORTED = "set_timespan_unsupported"  # e.g. a duration, not a period
    TIMESPAN_INVALID = "set_timespan_invalid"  # e.g. a naive until, or not a datetime
    TIMESPAN_OUT_OF_RANGE = "set_timespan_out_of_range"  # too large for a datetime
    TIMESPAN_NOT_IN_FUTURE = "set_timespan_not_in_future"  # it would have ended already
    TEMPERATURE_REQUIRED = "set_temperature_required"
    TEMPERATURE_NOT_ALLOWED = "set_temperature_not_allowed"
    TEMPERATURE_INVALID = "set_temperature_invalid"  # e.g. NaN, or infinity
    STATE_REQUIRED = "set_state_required"
    STATE_NOT_ALLOWED = "set_state_not_allowed"
    STATE_UNKNOWN = "set_state_unknown"  # the state is not a valid enum value
    STATE_UNSUPPORTED = "set_state_unsupported"  # the state is not among allowed states

    # other requests
    DATETIME_INVALID = "set_datetime_invalid"  # e.g. a string that is not a datetime
    SCHEDULE_INVALID = "set_schedule_invalid"  # e.g. not JSON (or not serializable)
    TIMEZONE_REQUIRED = "set_timezone_required"  # a datetime is naive (has no tzinfo)
    ZONE_UNKNOWN = "set_zone_unknown"  # e.g. no zone with that id/idx/name


class BadApiRequestError(EvohomeError):  # a base exception
    """The supplied parameter(s) are not as expected (e.g. unknown/unsupported mode).

    The `reason` attr says why (see RequestErrorReason), so that callers need not parse
    the message. The `details` attr holds only the structured values that apply to the
    reason, for use as the placeholders of a (translated) message (see the subclasses).

    This library always supplies a reason, but it is optional, so that the error can
    still be raised with only a message (e.g. by a test double): then its reason is the
    class's default (e.g. MODE_INVALID, for an InvalidSetModeError), so is never None.
    """

    _default_reason: ClassVar[RequestErrorReason] = RequestErrorReason.REQUEST_INVALID

    def __init__(
        self,
        message: str,
        *,
        reason: RequestErrorReason | None = None,
        **details: str,
    ) -> None:
        super().__init__(message)
        self.reason = reason or self._default_reason  # never None
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

    _default_reason: ClassVar[RequestErrorReason] = RequestErrorReason.MODE_INVALID


class InvalidSetScheduleError(BadApiRequestError):  # failed to set a schedule
    """The supplied schedule JSON is not supported / is invalid.

    This is a schedule supplied by the caller (e.g. via set_schedule()): see
    InvalidGetScheduleError for a schedule from the vendor.
    """

    _default_reason: ClassVar[RequestErrorReason] = RequestErrorReason.SCHEDULE_INVALID


# 4. State failures: the client does not hold the data needed to answer (after/without
#    a successful API call); fetch the data first


@verify(EnumCheck.UNIQUE)
class ClientStateErrorReason(StrEnum):
    """Why the client cannot provide what was asked for (see ClientStateError).

    The values are public API, so that callers can map each one to their own (e.g.
    translated) message: renaming or removing a member is a breaking change, but
    adding one is not. They are named PARAM_PROBLEM, and their values are prefixed
    cfg_, so that they are unique (e.g. LOCATION_NO_TCS = cfg_location_no_tcs).
    """

    CONFIG_INVALID = "cfg_config_invalid"  # a catch-all for config problems

    CONFIG_NOT_FETCHED = "cfg_config_not_fetched"  # call setup()
    CONFIG_STALE = "cfg_config_stale"  # e.g. the status lacks a zone of the config
    LOCATION_INACCESSIBLE = "cfg_location_inaccessible"  # e.g. deleted, or unshared
    # TODO: remove in v4.0: only the (deprecated) single-TCS shortcuts raise these, i.e.
    # EvohomeClient.tcs (a client's TCS, via its single location), and (v1 only)
    # Location.get_temperatures()
    LOCATION_NOT_SINGLE = "cfg_location_not_single"  # the account has 0, or 2+
    LOCATION_NO_TCS = "cfg_location_no_tcs"  # a location has 0 or 1 TCS
    SCHEDULE_NOT_FETCHED = "cfg_schedule_not_fetched"  # call get_schedule()
    STATUS_NOT_FETCHED = "cfg_status_not_fetched"  # call Location.get_status()


class ClientStateError(EvohomeError):  # a base exception
    """The client's config/status data cannot provide what was asked for.

    The `reason` attr says why (see ClientStateErrorReason), so that callers need not
    parse the message. This library always supplies a reason, but it is optional, so
    that the error can still be raised with only a message: then its reason is the
    class's default (e.g. CONFIG_STALE, for a StaleConfigError), so is never None.
    """

    _default_reason: ClassVar[ClientStateErrorReason] = (
        ClientStateErrorReason.CONFIG_INVALID
    )

    def __init__(
        self,
        message: str,
        *,
        reason: ClientStateErrorReason | None = None,
        **details: str,
    ) -> None:
        super().__init__(message)
        self.reason = reason or self._default_reason  # never None
        self.details: dict[str, str] = details


class NotFetchedError(ClientStateError):
    """The config/status/schedule JSON has not been fetched yet.

    This is likely because the user has not yet called `EvohomeClient.setup()`,
    `Location.get_status()`, `HotWater.get_schedule()` or `Zone.get_schedule()`.
    """

    _default_reason: ClassVar[ClientStateErrorReason] = (
        ClientStateErrorReason.CONFIG_NOT_FETCHED
    )


class StaleConfigError(ClientStateError):
    """The config JSON is inconsistent with the latest status JSON.

    For example, an entity (e.g. a zone) that is in the config is absent from the
    status, or a location is no longer accessible. This is likely because the
    installation has been changed since the config was fetched.
    """

    _default_reason: ClassVar[ClientStateErrorReason] = (
        ClientStateErrorReason.CONFIG_STALE
    )


# The previous names of these errors, before they were named after the method (set_*,
# get_*) that raises them; they are still used, e.g. by HA, so do not (yet) warn
# TODO: deprecate in v4.0 (i.e. move them into _DEPRECATED_ALIASES, below)
InvalidConfigError = InvalidGetConfigError
InvalidModeRequestError = InvalidSetModeError
InvalidScheduleError = InvalidGetScheduleError
InvalidScheduleRequestError = InvalidSetScheduleError
InvalidStatusError = InvalidGetStatusError


# Backward-compatibility aliases (deprecated names, e.g. as used by the HA integration):
# each is its replacement, but is served by a module __getattr__() that warns when it is
# accessed (e.g. imported, or evaluated in an except clause)
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
