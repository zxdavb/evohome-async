"""The exceptions raised by the async clients for the Resideo TCC API.

They are grouped by what the caller can do about them:

  EvohomeError
  │
  ├── ApiCallFailedError                  # no usable reply (not a 200): fix/try later
  │   ├── ApiRateLimitExceededError       # trying later on will help
  │   │   └── AuthRateLimitExceededError  # is also an AuthenticationFailedError
  │   ├── AuthenticationFailedError
  │   │   └── BadUserCredentialsError     # trying again will not help
  │   └── ApiCallRejectedError            # trying again will not help
  │
  ├── BadApiRequestError                  # the arguments are unusable (no API call)
  │   ├── InvalidModeRequestError
  │   └── InvalidScheduleRequestError
  │
  ├── BadApiResponseError                 # the reply (a 200) is not as expected
  │   ├── InvalidConfigError
  │   │   └── GhostZoneError
  │   ├── InvalidStatusError
  │   └── InvalidScheduleError
  │
  └── ClientStateError                    # the client lacks the data: fetch it first
      ├── NotFetchedError
      ├── StaleConfigError
      └── NoSingleTcsError                # can't use Evo.tcs attr (to be deprecated)
"""

from __future__ import annotations

from http import HTTPStatus


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
    """The vendor rejected a PUT request (e.g. 400, SystemModeChangeTimeUntilNotSet).

    The request was sent, but the vendor refused it, so nothing will have changed.
    Trying again will not help. Unlike a BadApiRequestError, the arguments passed
    this library's checks, so the request (or this library) must change.
    """


# 2. Response failures: there was a reply, but it is not as expected; trying again will
#    not help, as either the vendor's JSON or this library's schemas must change. Can be:
#    a) failing schema validation (immediately after a HTTP GET), or (later on)
#    b) internally inconsistent (e.g. a zone without a model type)


class BadApiResponseError(EvohomeError):  # a base exception
    """The received JSON is not as expected (e.g. missing a required key)."""


class InvalidConfigError(BadApiResponseError):  # config/account JSON is invalid
    """The account/config JSON is not as expected (e.g. an unknown TCS model type)."""


class GhostZoneError(InvalidConfigError):  # the zone will be ignored
    """The config JSON of a zone has no model type or zone type (is it a ghost zone?)."""


class InvalidStatusError(BadApiResponseError):  # status JSON is invalid
    """The status JSON is not as expected (e.g. an unknown fault type)."""


class InvalidScheduleError(BadApiResponseError):  # schedule JSON is invalid/missing
    """The schedule JSON is not as expected, or there is no schedule."""


# 3. Request failures: the supplied arguments are unusable (e.g. an unsupported zone
#    mode); these are detected before making any API request, so nothing was sent


class BadApiRequestError(EvohomeError):  # a base exception
    """The supplied parameter(s) are not as expected (e.g. unknown/unsupported mode)."""


class InvalidModeRequestError(BadApiRequestError):  # failed to set a TCS/zone/DHW mode
    """The requested mode is not supported by this TCS/zone/DHW zone."""


class InvalidScheduleRequestError(BadApiRequestError):  # failed to set a schedule
    """The supplied schedule JSON is not supported / is invalid."""


# 4. State failures: the client does not hold the data needed to answer (after/without
#    a successful API call); fetch the data first


class ClientStateError(EvohomeError):  # a base exception
    """The client's config/status data cannot provide what was asked for."""


class NotFetchedError(ClientStateError):
    """The config/status/schedule JSON has not been fetched yet.

    This is likely because the user has not yet called `EvohomeClient.update()`,
    `Location.update()` or `Zone.get_schedule()`.
    """


class StaleConfigError(ClientStateError):
    """The config JSON is inconsistent with the latest status JSON.

    For example, an entity (e.g. a zone) that is in the config is absent from the
    status, or a location is no longer accessible. This is likely because the
    installation has been changed since the config was fetched.
    """


class NoSingleTcsError(ClientStateError):
    """There is no default TCS (e.g. the user has more than one location)."""


# Backward-compatibility aliases (deprecated names, e.g. as used by the HA integration)
ApiRequestFailedError = ApiCallFailedError  # renamed to ApiCallFailedError
BadScheduleUploadedError = InvalidScheduleRequestError  # renamed
InvalidSystemModeError = InvalidModeRequestError  # merged into InvalidModeRequestError
