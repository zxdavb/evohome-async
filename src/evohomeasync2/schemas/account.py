#!/usr/bin/env python3
"""evohomeasync schema - for Account JSON of RESTful API."""

from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol

from common.helpers import noop, obfuscate

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
