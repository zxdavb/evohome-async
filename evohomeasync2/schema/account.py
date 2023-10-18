#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Account JSON."""
from __future__ import annotations

import voluptuous as vol  # type: ignore[import]

from .const import (
    SZ_ACCESS_TOKEN,
    SZ_CITY,
    SZ_COUNTRY,
    SZ_EXPIRES_IN,
    SZ_FIRSTNAME,
    SZ_LANGUAGE,
    SZ_LASTNAME,
    SZ_POSTCODE,
    SZ_REFRESH_TOKEN,
    SZ_SCOPE,
    SZ_STREET_ADDRESS,
    SZ_TOKEN_TYPE,
    SZ_USER_ID,
    SZ_USERNAME,
)
from .const import obfuscate as _obfuscate


SCH_OAUTH_TOKEN = vol.Schema(
    {
        vol.Required(SZ_ACCESS_TOKEN): vol.All(str, _obfuscate),
        vol.Required(SZ_EXPIRES_IN): int,  # 1800 seconds
        vol.Required(SZ_REFRESH_TOKEN): vol.All(str, _obfuscate),
        vol.Required(SZ_TOKEN_TYPE): str,
        vol.Optional(SZ_SCOPE): str,  # "EMEA-V1-Basic EMEA-V1-Anonymous"
    }
)

SCH_USER_ACCOUNT = vol.Schema(
    {
        vol.Required(SZ_USER_ID): str,
        vol.Required(SZ_USERNAME): vol.All(vol.Email(), _obfuscate),
        vol.Required(SZ_FIRSTNAME): str,
        vol.Required(SZ_LASTNAME): vol.All(str, _obfuscate),
        vol.Required(SZ_STREET_ADDRESS): vol.All(str, _obfuscate),
        vol.Required(SZ_CITY): vol.All(str, _obfuscate),
        vol.Required(SZ_POSTCODE): vol.All(str, _obfuscate),
        vol.Required(SZ_COUNTRY): str,
        vol.Required(SZ_LANGUAGE): str,
    },
    extra=vol.PREVENT_EXTRA,
)
