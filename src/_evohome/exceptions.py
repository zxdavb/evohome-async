"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations


class _EvohomeBaseError(Exception):
    """The base class for all exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvohomeError(_EvohomeBaseError):
    """The base class for all exceptions."""


# Request/Response failures (of a RESTful API call)...
# - API requests unable to be made
# - API requests made, but a 'bad' response received


class _ApiCallFailedError(EvohomeError):
    """The API request failed for some reason (no/invalid/unexpected response)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status  # useful, available if via aiohttp.ClientResponseError


class ApiCallFailedError(_ApiCallFailedError):  # a base exception
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by any aiohttp.ClientError, for example: ConnectionError.  If the
    cause was a ClientResponseError, then the `status` attr will have an integer value.
    """


class ApiRateLimitExceededError(ApiCallFailedError):
    """The API request failed because the vendor's API rate limit was exceeded."""


class AuthenticationFailedError(_ApiCallFailedError):
    """Unable to authenticate the user credentials (unable to obtain an access token).

    The cause could be any ApiCallFailedError, including RateLimitExceeded.
    """


class BadUserCredentialsError(AuthenticationFailedError):
    """Unable to authenticate the user credentials (unknown client_id or wrong secret).

    Reauthenticating will not help as the user credentials are proven to be invalid.
    """


# Request/Response failures (of a RESTful API call)...
# - API requests unable to be made
# - API requests made, but a 'bad' response received


class BadApiSchemaError(ApiCallFailedError):  # base exception
    """The received/supplied JSON is not as expected (e.g. missing a required key)."""


# 2. Requests exceptions (e.g. unknown/unsupported mode):
# - usually detected immediately before, making the API request, or
# - as a result of a failed request


class BadApiRequestError(BadApiSchemaError):  # base for all failed API requests
    """The supplied parameter(s) are not as expected (e.g. unknown/unsupported mode)."""


class InvalidSystemModeError(BadApiRequestError):  # failed to set a TCS mode
    """The requested system mode is not supported by this TCS."""


class InvalidZoneModeError(BadApiRequestError):  # failed to set a zone mode/temperature
    """The requested mode is not supported by this heating zone."""


class InvalidDhwModeError(InvalidZoneModeError):  # failed to set a DHW zone mode/state
    """The requested mode is not supported by this DHW zone."""


class BadScheduleUploadedError(BadApiRequestError):  # failed to set a zone/DHW schedule
    """The supplied schedule JSON is not supported / is invalid."""


# 3. Response exceptions (e.g. missing zones) - can be determine as:
# a) failing schema validation (immediately after a HTTP GET), or (later on)
# b) internally inconsistent (e.g. TCS with duplicate zone IDs), or
# c) status inconsistent with status JSON (i.e. config has changed since it was fetched)


class BadApiResponseError(BadApiSchemaError):  # base for all invalid API responses
    """The received JSON is not as expected (e.g. missing a required key)."""


class _ConfigStatusError(EvohomeError):  # JSON failed validation / is inconsistent
    """The config/status JSON is missing or somehow invalid (has it been fetched?)."""


class ConfigError(_ConfigStatusError):  # base for invalid/stale config/account JSON
    """The config JSON is missing or somehow invalid (e.g. InvalidSchemaError)."""


class InvalidConfigError(ConfigError):  # config/account JSON is invalid/missing
    """The system config JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet been authenticated (or authentication
    has failed).
    """


class StaleConfigError(ConfigError):  # config JSON is stale (inconsistent with status)
    """The config JSON is inconsistent with the latest status JSON.

    For example, an entity (e.g. a zone) that is in the config is absent from the
    status, likely because the installation has been changed since the config was
    fetched.
    """


class NoSingleTcsError(ConfigError):
    """There is no default TCS (e.g. the user has more than one location)."""


class StatusError(_ConfigStatusError):  # base for invalid/inconsistent status JSON
    """The status JSON is missing or somehow invalid (e.g. BadApiResponseSchemaError)."""


class InvalidStatusError(StatusError):  # status JSON is invalid/inconsistent
    """The status JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Location.update()`.
    """


class InvalidScheduleError(InvalidStatusError):  # schedule JSON is invalid/inconsistent
    """The schedule JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Zone.get_schedule()`.
    """


# Backward-compatibility aliases (deprecated names used by HA integration)
ApiRequestFailedError = ApiCallFailedError  # renamed to ApiCallFailedError
