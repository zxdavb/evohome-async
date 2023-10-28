#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API."""
from __future__ import annotations


class EvohomeError(Exception):
    """The base exception class for evohome-async."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidSchedule(EvohomeError):
    """The supplied schedule has an invalid schema."""


class NoDefaultTcsError(EvohomeError):
    """There is not exactly one TCS in the user's installation."""


class FailedRequest(EvohomeError):
    """The API request failed for some reason (no/invalid/unexpected response).

    Could be caused by other than aiohttp.ClientResponseError, for example:
    aiohttp.ConnectionError.  If the cause was a ClientResponseError, then the
    `status` attr will not be None.
    """

    def __init__(self, message: str, status: None | int = None) -> None:
        super().__init__(message)
        self.status = status  # iff cause was aiohttp.ClientResponseError


class RateLimitExceeded(FailedRequest):
    """API request failed because the vendor's API rate limit was exceeded."""


class AuthenticationError(FailedRequest):
    """Unable to authenticate (unable to obtain an access token).

    The cause could be any FailedRequest, including RateLimitExceeded.
    """
