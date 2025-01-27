"""Tests for evohome-async."""

from __future__ import annotations

from typing import Final

from evohome.auth import HOSTNAME
from evohomeasync2.auth import _APPLICATION_ID as _APPLICATION_ID_V2

#
# normally, we want debug flags to be False
_DBG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema
_DBG_TEST_CRED_URLS = False  # avoid 429s: dont invalidate the credential cache
_DBG_USE_REAL_AIOHTTP = False  # use 'real' aiohttp to reach vendor's servers

#
# used to construct the default token cache
TEST_USERNAME: Final = "username@email.com"
TEST_PASSWORD: Final = "P@ssw0rd!!"  # noqa: S105

# vendors API URLs - the older API
URL_CRED_V0 = f"https://{HOSTNAME}/WebAPI/api/session"
URL_BASE_V0 = f"https://{HOSTNAME}/WebAPI/api"

# - the newer API
URL_CRED_V2 = f"https://{HOSTNAME}/Auth/OAuth/Token"
URL_BASE_V2 = f"https://{HOSTNAME}/WebAPI/emea/api/v1"

HEADERS_BASE = {
    "Accept": "application/json",
    "Connection": "Keep-Alive",
}
HEADERS_CRED_V0 = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
}
HEADERS_CRED_V2 = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Authorization": "Basic " + _APPLICATION_ID_V2,
}
