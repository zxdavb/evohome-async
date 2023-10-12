#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#


class EvoBaseError(Exception):
    pass


class AuthenticationError(EvoBaseError):
    """Exception raised when unable to get an access_token."""

    def __init__(self, message: str) -> None:
        """Construct the AuthenticationError object."""

        self.message = message
        super().__init__(message)


class SingleTcsError(EvoBaseError):
    """There is not exactly one TCS available."""

    def __init__(self, message: str) -> None:
        """Construct the AuthenticationError object."""

        self.message = message
        super().__init__(message)


class InvalidSchedule(EvoBaseError):
    """There is not exactly one TCS available."""

    def __init__(self, message: str) -> None:
        """Construct the AuthenticationError object."""

        self.message = message
        super().__init__(message)
