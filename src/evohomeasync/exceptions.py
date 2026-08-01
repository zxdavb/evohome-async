"""An async client for the v0 Resideo TCC API."""

from __future__ import annotations

from _evohome import exceptions as _base
from _evohome.exceptions import (
    ApiCallFailedError,
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiSchemaError,
    BadScheduleUploadedError,
    BadUserCredentialsError,
    EvohomeError,
    InvalidScheduleError,
    StatusError,
)

# Below are the exceptions actually raised by this package's own code (as opposed to
# the ones above, which are only ever raised by the shared _evohome base classes).
# They are redefined here (rather than re-exported) so that they report this package
# as their __module__, not the internal _evohome package.


class ConfigError(_base.ConfigError):
    """The config JSON is missing or somehow invalid (e.g. InvalidSchemaError)."""


class InvalidConfigError(ConfigError, _base.InvalidConfigError):
    """The system config JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet been authenticated (or authentication
    has failed).
    """


class NoSingleTcsError(ConfigError, _base.NoSingleTcsError):
    """There is no default TCS (e.g. the user has more than one location)."""


class BadApiResponseError(_base.BadApiResponseError):
    """The received JSON is not as expected (e.g. missing a required key)."""


class InvalidStatusError(_base.InvalidStatusError):
    """The status JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Client.update()`.
    """


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
    "InvalidScheduleError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "StatusError",
]
