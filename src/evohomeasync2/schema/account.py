#!/usr/bin/env python3
"""evohomeasync2 schema - for Account JSON of RESTful API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import voluptuous as vol

from .const import (
    SZ_CITY,
    SZ_COUNTRY,
    SZ_FIRSTNAME,
    SZ_LANGUAGE,
    SZ_LASTNAME,
    SZ_POSTCODE,
    SZ_STREET_ADDRESS,
    SZ_USER_ID,
    SZ_USERNAME,
    obfuscate as _obfuscate,
)
from .helpers import snake_to_camel

# These are vendor-specific constants, used for authentication
SZ_ACCESS_TOKEN: Final = "access_token"
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"  # not part of a schema
SZ_EXPIRES_IN: Final = "expires_in"
SZ_REFRESH_TOKEN: Final = "refresh_token"
SZ_SCOPE: Final = "scope"
SZ_TOKEN_TYPE: Final = "token_type"


SCH_OAUTH_TOKEN: Final = vol.Schema(
    {
        vol.Required(SZ_ACCESS_TOKEN): vol.All(str, _obfuscate),
        vol.Required(SZ_EXPIRES_IN): int,  # 1800 seconds
        vol.Required(SZ_REFRESH_TOKEN): vol.All(str, _obfuscate),
        vol.Required(SZ_TOKEN_TYPE): str,
        vol.Optional(SZ_SCOPE): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
    }
)


def _factory_user_account(fnc: Callable | None) -> vol.Schema:
    """Factory for the user account schema."""

    if fnc is None:
        def fnc(x: str) -> str:
            return x

    return vol.Schema(
        {
            vol.Required(fnc(SZ_USER_ID)): str,
            vol.Required(fnc(SZ_USERNAME)): vol.All(vol.Email(), _obfuscate),
            vol.Required(fnc(SZ_FIRSTNAME)): str,
            vol.Required(fnc(SZ_LASTNAME)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_STREET_ADDRESS)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_CITY)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_POSTCODE)): vol.All(str, _obfuscate),
            vol.Required(fnc(SZ_COUNTRY)): str,
            vol.Required(fnc(SZ_LANGUAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


SCH_USER_ACCOUNT: Final = _factory_user_account(snake_to_camel)
