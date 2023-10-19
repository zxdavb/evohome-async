#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#


class FakedVoluptuous:  # voluptuous is an optional dependency
    class Invalid(Exception):  # used as a proxy for vol.error.Invalid
        pass


class EvoBaseError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(EvoBaseError):
    """Exception raised when unable to authenticate."""

    def __init__(self, message: str, status: None | int = None) -> None:
        self.message = f"Unable to obtain an Access Token: {message}"
        super().__init__(message)
        self.status = status


class InvalidSchedule(EvoBaseError):
    """The schedule is invalid."""


class SingleTcsError(EvoBaseError):
    """There is not exactly one TCS available."""


class InvalidResponse(EvoBaseError):
    """Request failed for some reason."""


class RateLimitExceeded(EvoBaseError):
    """Request failed for some reason."""
