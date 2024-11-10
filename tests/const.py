#!/usr/bin/env python3
"""Tests for evohome-async."""

from __future__ import annotations

from typing import Final

from evohomeasync.auth import HOSTNAME as HOSTNAME_V0
from evohomeasync2.auth import _APPLICATION_ID, HOSTNAME as HOSTNAME_V1

# used to construct the default token cache
TEST_USERNAME: Final = "spotty.blackcat@gmail.com"  # SECRET "username@email.com"
TEST_PASSWORD: Final = "ziQajn732m5JYQ!"  # "P@ssw0rd!!"  # noqa: S105

# vendors API URLs - the older API
URL_AUTH_V0 = f"https://{HOSTNAME_V0}/WebAPI/api/session"
URL_BASE_V0 = f"https://{HOSTNAME_V0}/WebAPI/api/"

# - the newer API
URL_AUTH_V1 = f"https://{HOSTNAME_V1}/Auth/OAuth/Token"
URL_BASE_V1 = f"https://{HOSTNAME_V1}/WebAPI/emea/api/v1/"

HEADERS_AUTH_V0 = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
}
HEADERS_AUTH_V1 = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Connection": "Keep-Alive",
    "Authorization": "Basic " + _APPLICATION_ID,
}
