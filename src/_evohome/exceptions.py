"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations


class _EvohomeBaseError(Exception):
    """The base class for all exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvohomeError(_EvohomeBaseError):
    """The base class for all exceptions."""


# These occur whilst a RESTful API call is being made


class _ApiCallFailedError(EvohomeError):
    """The API request failed for some reason (no/invalid/unexpected response)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status  # useful, available if via aiohttp.ClientResponseError


class ApiCallFailedError(_ApiCallFailedError):  # a base exception, API failed
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


# Request/Response failures (of a RESTful API call)


class BadApiSchemaError(ApiCallFailedError):  # a base exception, API data bad
    """The received/supplied JSON is not as expected (e.g. missing a required key)."""


class BadApiResponseError(BadApiSchemaError):
    """The received JSON is not as expected (e.g. missing a required key)."""


class BadApiRequestError(BadApiSchemaError):
    """The supplied parameter(s) are not as expected (e.g. unknown/unsupported mode)."""


class InvalidSystemModeError(BadApiRequestError):  # failed to set a TCS mode
    """The requested system mode is not supported by this TCS."""


class InvalidZoneModeError(BadApiRequestError):  # failed to set a zone mode/temperature
    """The requested mode is not supported by this zone."""


class InvalidDhwModeError(InvalidZoneModeError):  # failed to set a DHW zone mode/state
    """The requested mode is not supported by this DHW zone."""


class BadScheduleUploadedError(BadApiRequestError):  # failed to set a zone/DHW schedule
    """The supplied schedule JSON is invalid / was not accepted by the vendor."""


# Other, higher failures (after/without a successful API call)


class _ConfigStatusError(EvohomeError):  # invalid/missing JSON
    """The config/status JSON is missing or somehow invalid (has it been fetched?)."""


class ConfigError(_ConfigStatusError):  # account/config JSON is invalid/missing
    """The config JSON is missing or somehow invalid (e.g. InvalidSchemaError)."""


class InvalidConfigError(ConfigError):  # account/config JSON is invalid/missing
    """The system config JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet been authenticated (or authentication
    has failed).
    """


class NoSingleTcsError(ConfigError):
    """There is no default TCS (e.g. the user has more than one location)."""


class StatusError(_ConfigStatusError):  # status/schedule JSON is invalid/missing
    """The status JSON is missing or somehow invalid (e.g. BadApiResponseSchemaError)."""


class InvalidStatusError(StatusError):  # status JSON is invalid/missing
    """The status JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Location.update()`.
    """


class InvalidScheduleError(StatusError):  # schedule JSON is invalid/missing
    """The schedule JSON is missing/invalid (has it been fetched?).

    This is likely because the user has not yet called `Zone.get_schedule()`.
    """
