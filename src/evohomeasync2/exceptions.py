"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations

from _evohome import exceptions as _base
from _evohome.exceptions import (
    ApiCallFailedError,
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiSchemaError,
    BadUserCredentialsError,
    ConfigError,
    EvohomeError,
    StatusError,
)

# Below are the exceptions actually raised by this package's own code (as opposed to
# the ones above, which are only ever raised by the shared _evohome base classes).
# They are redefined here (rather than re-exported) so that they report this package
# as their __module__, not the internal _evohome package.


class BadApiResponseError(_base.BadApiResponseError):
    """The received JSON is not as expected (e.g. missing a required key)."""


class InvalidConfigError(_base.InvalidConfigError):
    """The system config JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet been authenticated (or authentication
    has failed).
    """


class NoSingleTcsError(_base.NoSingleTcsError):
    """There is no default TCS (e.g. the user has more than one location)."""


class InvalidStatusError(_base.InvalidStatusError):
    """The status JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Location.update()`.
    """


class InvalidScheduleError(_base.InvalidScheduleError):
    """The schedule JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Zone.get_schedule()`.
    """


class BadScheduleUploadedError(_base.BadScheduleUploadedError):
    """The supplied schedule JSON is invalid / was not accepted by the vendor."""


class InvalidSystemModeError(_base.InvalidSystemModeError):
    """The requested system mode is not supported by this TCS."""


class InvalidZoneModeError(_base.InvalidZoneModeError):
    """The requested mode is not supported by this zone."""


class InvalidDhwModeError(InvalidZoneModeError, _base.InvalidDhwModeError):
    """The requested mode is not supported by this DHW zone."""


__all__ = [
    "ApiCallFailedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",  # deprecated alias for ApiCallFailedError
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadApiSchemaError",
    "BadScheduleUploadedError",
    "BadUserCredentialsError",
    "ConfigError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidDhwModeError",
    "InvalidScheduleError",
    "InvalidStatusError",
    "InvalidSystemModeError",
    "InvalidZoneModeError",
    "NoSingleTcsError",
    "StatusError",
]
