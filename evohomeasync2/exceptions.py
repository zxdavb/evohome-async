#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API."""
from __future__ import annotations


class EvohomeError(Exception):
    """The base exception class for evohome-async."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(EvohomeError):
    """Unable to authenticate (unable to obtain an access token)."""


class FailedRequest(EvohomeError):
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by other than aiohttp.ClientResponseError, for example:
    aiohttp.ConnectionError.  If the cause was a ClientResponseError, then the
    `http_status` attr will not be None.
    """

    def __init__(self, message: str, status: None | int = None) -> None:
        super().__init__(message)
        self.status = status  # if cause was aiohttp.ClientResponseError


class RateLimitExceeded(FailedRequest):
    """API request failed because the vendor's API rate limit was exceeded."""


class InvalidSchedule(FailedRequest):
    """The supplied schedule schema is invalid."""


class NoDefaultTcsError(EvohomeError):
    """There is not exactly one TCS in the user's installation."""
