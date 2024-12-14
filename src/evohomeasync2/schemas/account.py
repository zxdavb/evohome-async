#!/usr/bin/env python3
"""evohomeasync schema - for Account JSON of RESTful API."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import voluptuous as vol

from evohome.helpers import noop, obfuscate

from .const import (
    S2_CITY,
    S2_COUNTRY,
    S2_FIRSTNAME,
    S2_LANGUAGE,
    S2_LASTNAME,
    S2_POSTCODE,
    S2_STREET_ADDRESS,
    S2_USER_ID,
    S2_USERNAME,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class TccOAuthTokenResponseT(TypedDict):
    """Typed dict for the OAuth authorization response schema.

    This schemas is snake_case, unlike the RESTful API which is camelCase.
    """

    access_token: str
    expires_in: int
    refresh_token: str
    token_type: str
    scope: str


def factory_post_oauth_token(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the OAuth authorization response schema."""

    # NOTE: These keys are always in snake_case

    return vol.Schema(
        {
            vol.Required("access_token"): vol.All(str, obfuscate),
            vol.Required("expires_in"): vol.Range(min=1770, max=1800),  # usu. 179x
            vol.Required("refresh_token"): vol.All(str, obfuscate),
            vol.Required("token_type"): str,
            vol.Optional("scope"): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
        }
    )


class TccErrorResponseT(TypedDict):
    """Typed dict for error responses from the vendor servers."""

    error: str


def factory_error_response(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the error response schema."""

    return vol.Schema(
        {
            vol.Required("error"): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


class TccUsrAccountResponseT(TypedDict):
    """Typed dict for the user account schema."""

    userId: str
    username: str
    firstname: str
    lastname: str
    streetAddress: str
    city: str
    postcode: str
    country: str
    language: str


def factory_user_account(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the user account schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), obfuscate),
            vol.Required(fnc(S2_FIRSTNAME)): str,
            vol.Required(fnc(S2_LASTNAME)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_STREET_ADDRESS)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_CITY)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_POSTCODE)): vol.All(str, obfuscate),
            vol.Required(fnc(S2_COUNTRY)): str,
            vol.Required(fnc(S2_LANGUAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


class TccFailureResponseT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    code: str
    message: str


def factory_status_response(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the error response schema."""

    entry_schema = vol.Schema(
        {
            vol.Required("code"): str,
            vol.Required("message"): str,
        },
        extra=vol.PREVENT_EXTRA,
    )

    return vol.Schema(vol.All([entry_schema], vol.Length(min=1)))
