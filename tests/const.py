"""Tests for evohome-async."""

from __future__ import annotations

from typing import Final

from _evohome.const import HOSTNAME
from evohomeasync2.auth import _APPLICATION_ID as _APPLICATION_ID_V2

#
# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema
_DBG_TEST_CRED_URLS = False  # avoid 429s: dont invalidate the credential cache
_DBG_TEST_UNUSED_APIS = False  # also invoke vendor APIs that the client doesn't use
_DBG_USE_REAL_AIOHTTP = False  # use 'real' aiohttp to reach vendor's servers
_DBG_WAIT_FOR_COMM_TASKS = False  # poll each comm task until it succeeds

#
# the longest that a request may take to return (a GET, PUT, etc.)
TIMEOUT_REAL_AIOHTTP: Final = 5  # seconds
# the longest that a PUT's comm task may take to succeed (only if waited for), else skip
TIMEOUT_COMM_TASK: Final = 15  # seconds
# ...the same, but for a v1 PUT (one was seen to take 29s, 2026-10-07)
TIMEOUT_COMM_TASK_V0: Final = 45  # seconds

#
# the location under test, as an index into the user's list of locations: index the
# vendor's JSON with it, or use get_loc() (tests_rf/common.py) for a Location object
TEST_LOC_IDX: Final = 0  # the test account has only one location
# TODO: select the location by its id, not by an index: it is assumed that the v1
# and v2 APIs list the same locations, in the same order, but that is unconfirmed
# (the ids are the same in both, e.g. v1's 2738909 is v2's '2738909'). If not, the v1
# tests would use a different location to that reset by reset_systems() (via v2).

#
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
