#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the updated Evohome API."""

from __future__ import annotations


class EvohomeBaseError(Exception):
    """The base exception class for evohome-async."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvohomeError(EvohomeBaseError):
    """The base exception class for evohome-async."""


class DeprecationError(EvohomeBaseError):
    """The method or property has changed, or is otherwise deprecated."""


class InvalidSchema(EvohomeError):
    """The config/status JSON is invalid (e.g. missing an entity id)."""


class InvalidParameter(EvohomeError):
    """The supplied parameter(s) is/are invalid (e.g. unknown/unsupported mode)."""


class InvalidSchedule(InvalidSchema):
    """The schedule has an invalid schema."""


class NoSingleTcsError(EvohomeError):
    """There is not exactly one TCS in the user's installation."""


class RequestFailed(EvohomeError):
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by any aiohttp.ClientError, for example: ConnectionError.  If the
    cause was a ClientResponseError, then the `status` attr will have an integer value.
    """

    def __init__(self, message: str, status: None | int = None) -> None:
        super().__init__(message)
        self.status = status  # iff cause was aiohttp.ClientResponseError


class RateLimitExceeded(RequestFailed):
    """API request failed because the vendor's API rate limit was exceeded."""


class AuthenticationFailed(RequestFailed):
    """Unable to authenticate (unable to obtain an access token).

    The cause could be any FailedRequest, including RateLimitExceeded.
    """
