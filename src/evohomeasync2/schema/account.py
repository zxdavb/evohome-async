#!/usr/bin/env python3
"""evohomeasync schema - for Account JSON of RESTful API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import voluptuous as vol

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
from .helpers import do_nothing, obfuscate as _obfuscate, snake_to_camel


def _factory_user_account(fnc: Callable[[str], str] = do_nothing) -> vol.Schema:
    """Factory for the user account schema."""

    return vol.Schema(
        {
            vol.Required(fnc(S2_USER_ID)): str,
            vol.Required(fnc(S2_USERNAME)): vol.All(vol.Email(), _obfuscate),
            vol.Required(fnc(S2_FIRSTNAME)): str,
            vol.Required(fnc(S2_LASTNAME)): vol.All(str, _obfuscate),
            vol.Required(fnc(S2_STREET_ADDRESS)): vol.All(str, _obfuscate),
            vol.Required(fnc(S2_CITY)): vol.All(str, _obfuscate),
            vol.Required(fnc(S2_POSTCODE)): vol.All(str, _obfuscate),
            vol.Required(fnc(S2_COUNTRY)): str,
            vol.Required(fnc(S2_LANGUAGE)): str,
        },
        extra=vol.PREVENT_EXTRA,
    )


# GET /userAccount
SCH_USER_ACCOUNT: Final = _factory_user_account(snake_to_camel)
