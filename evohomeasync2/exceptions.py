#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#


class volErrorInvalid(Exception):  # used as a proxy for vol.error.Invalid
    pass


class EvoBaseError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(EvoBaseError):
    """Exception raised when unable to get an access_token."""


class InvalidSchedule(EvoBaseError):
    """The schedule is invalid."""


class SingleTcsError(EvoBaseError):
    """There is not exactly one TCS available."""


class InvalidResponse(EvoBaseError):
    """Request failed for some reason."""
