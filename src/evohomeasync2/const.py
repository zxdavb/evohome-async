#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the updated Evohome API."""

from typing import Final

from .schema import DhwState as DhwState, SystemMode as SystemMode, ZoneMode as ZoneMode

URL_HOST = "https://tccna.honeywell.com"

AUTH_URL = f"{URL_HOST}/Auth/OAuth/Token"
URL_BASE = f"{URL_HOST}/WebAPI/emea/api/v1"

HDR_STRFTIME = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers
API_STRFTIME = "%Y-%m-%dT%H:%M:%SZ"  # used by API

AUTH_HEADER_ACCEPT = (
    "application/json, application/xml, "
    "text/json, text/x-json, "
    "text/javascript, text/xml"
)

_AUTH_HEADER_BASIC = (
    "Basic "
    "NGEyMzEwODktZDJiNi00MWJkLWE1ZWItMTZhMGE0MjJiOTk5OjFhMTVjZGI4LTQyZGUtNDA3Y"
    "i1hZGQwLTA1OWY5MmM1MzBjYg=="
)

AUTH_HEADER = {
    "Accept": AUTH_HEADER_ACCEPT,
    "Authorization": _AUTH_HEADER_BASIC,
}

AUTH_PAYLOAD = {
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Host": "rs.alarmnet.com/",
    "Cache-Control": "no-store no-cache",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
}

CREDS_REFRESH_TOKEN = {
    "grant_type": "refresh_token",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous",
    "refresh_token": None,
}

CREDS_USER_PASSWORD = {
    "grant_type": "password",
    "scope": "EMEA-V1-Basic EMEA-V1-Anonymous EMEA-V1-Get-Current-User-Account",
    "Username": None,
    "Password": None,
}


# These are used in TCS.temperatures convenience function
SZ_ID: Final = "id"
SZ_NAME: Final = "name"
SZ_TEMP: Final = "temp"
SZ_THERMOSTAT: Final = "thermostat"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"
