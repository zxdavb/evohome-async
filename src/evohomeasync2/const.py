#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the updated Evohome TCC API."""

from typing import Final

import voluptuous as vol

from .schema import (
    DhwState as DhwState,
    SystemMode as SystemMode,
    ZoneMode as ZoneMode,
    obfuscate as _obfuscate,
)

URL_HOST: Final = "https://tccna.honeywell.com"

AUTH_URL: Final = f"{URL_HOST}/Auth/OAuth/Token"
URL_BASE: Final = f"{URL_HOST}/WebAPI/emea/api/v1"

HDR_STRFTIME: Final = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"  # used by API

AUTH_HEADER_ACCEPT: Final = (
    "application/json, application/xml, "
    "text/json, text/x-json, "
    "text/javascript, text/xml"
)

_AUTH_HEADER_BASIC: Final = (
    "Basic "
    "NGEyMzEwODktZDJiNi00MWJkLWE1ZWItMTZhMGE0MjJiOTk5OjFhMTVjZGI4LTQyZGUtNDA3Y"
    "i1hZGQwLTA1OWY5MmM1MzBjYg=="
)

AUTH_HEADER: Final = {
    "Accept": AUTH_HEADER_ACCEPT,
    "Authorization": _AUTH_HEADER_BASIC,
}

AUTH_PAYLOAD: Final = {
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Host": "rs.alarmnet.com/",
    "Cache-Control": "no-store no-cache",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
}

CREDS_REFRESH_TOKEN: Final = {
    "grant_type": "refresh_token",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
    "refresh_token": "",
}

CREDS_USER_PASSWORD: Final = {
    "grant_type": "password",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous EMEA-V1-Get-Current-User-Account",
    "Username": "",
    "Password": "",
}


# These snake_case equivalents of schema strings
# S2_SYSTEM_MODE: Final = "system_mode"
# SZ_USER_ID: Final = "user_id"


# These are used in TCS.temperatures convenience function
SZ_ID: Final = "id"
SZ_NAME: Final = "name"
SZ_TEMP: Final = "temp"
SZ_THERMOSTAT: Final = "thermostat"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"


# These are used for v1/v2 authentication (not part of a schema)
SZ_USERNAME: Final = "Username"
SZ_PASSWORD: Final = "Password"

SZ_ACCESS_TOKEN: Final = "access_token"
SZ_ACCESS_TOKEN_EXPIRES: Final = "access_token_expires"
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
