#!/usr/bin/env python3
"""Tests for evohome-async."""

from __future__ import annotations

from typing import Final

from evohomeasync.auth import HOSTNAME as HOSTNAME_V0
from evohomeasync2.auth import _APPLICATION_ID, HOSTNAME as HOSTNAME_V2

# used to construct the default token cache
TEST_USERNAME: Final = "username@email.com"
TEST_PASSWORD: Final = "P@ssw0rd!!"  # noqa: S105

# vendors API URLs - the older API
URL_AUTH_V0 = f"https://{HOSTNAME_V0}/WebAPI/api/session"
URL_BASE_V0 = f"https://{HOSTNAME_V0}/WebAPI/api/"

# - the newer API
URL_AUTH_V2 = f"https://{HOSTNAME_V2}/Auth/OAuth/Token"
URL_BASE_V2 = f"https://{HOSTNAME_V2}/WebAPI/emea/api/v1/"

HEADERS_AUTH_V0 = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
}
HEADERS_AUTH_V2 = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
    "Authorization": "Basic " + _APPLICATION_ID,
}
