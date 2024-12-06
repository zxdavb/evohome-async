#!/usr/bin/env python3
"""An async client for the v2 Resideo TCC API."""

from __future__ import annotations


class _EvohomeBaseError(Exception):
    """The base class for all exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvohomeError(_EvohomeBaseError):
    """The base class for all exceptions."""


class InvalidSchemaError(EvohomeError):  # a base exception
    """The received JSON is not as expected (e.g. missing a required key)."""


class InvalidParameterError(InvalidSchemaError):
    """The supplied parameter(s) is/are invalid (e.g. unknown/unsupported mode)."""


class InvalidScheduleError(InvalidParameterError):
    """The supplied schedule JSON is not as expected."""


class SystemConfigError(EvohomeError):  # a base exception
    """The system config JSON is missing or somehow invalid."""


class NoSystemConfigError(SystemConfigError):
    """The system config JSON is missing (has it been fetched?).

    This is likely because the user has not yet been authenticated (or authentication
    has failed).
    """


class NoSingleTcsError(SystemConfigError):
    """There is no default TCS (e.g. more than one location)."""


class ApiRequestFailedError(EvohomeError):  # a base exception
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by any aiohttp.ClientError, for example: ConnectionError.  If the
    cause was a ClientResponseError, then the `status` attr will have an integer value.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status  # iff cause was aiohttp.ClientResponseError


class RateLimitExceededError(ApiRequestFailedError):
    """The API request failed because the vendor's API rate limit was exceeded."""


class AuthenticationFailedError(ApiRequestFailedError):
    """Unable to authenticate the user credentials (unable to obtain an access token).

    The cause could be any ApiRequestFailedError, including RateLimitExceeded.
    """
