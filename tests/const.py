"""Constants shared by the offline tests and the real-API tests."""

from __future__ import annotations

import os
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
# (the gateway carries out its tasks one at a time, so a task may wait behind others)
TIMEOUT_COMM_TASK: Final = 60  # seconds
# ...the same, but for a v1 PUT (one was seen to take 29s, 2026-10-07)
TIMEOUT_COMM_TASK_V1: Final = 45  # seconds

#
# the location under test, by its id (which is the same in v1 and v2, e.g. v1's 2738909
# is v2's '2738909'): only against the vendor's servers, see get_loc() (tests/common.py)
TEST_LOC_ID: Final = os.getenv("TEST_LOC_ID") or None

#
# the fixtures (folders of tests/tests/fixtures_v2) used by test_v2_apis_edges.py, as
# they have old/new system modes, to test fallback and error handling logic
EDGE_FIXTURES: Final = ("default", "hass_118169")
# ...of which, those with a DHW (for its test_dhw_* tests, as hass_118169 has no DHW)
EDGE_FIXTURES_WITH_DHW: Final = ("default",)

#
#
# used to construct the default token cache
TEST_USERNAME: Final = "username@email.com"
TEST_PASSWORD: Final = "P@ssw0rd!!"  # noqa: S105

# vendors API URLs - the older API
URL_CRED_V1 = f"https://{HOSTNAME}/WebAPI/api/session"
URL_BASE_V1 = f"https://{HOSTNAME}/WebAPI/api"

# - the newer API
URL_CRED_V2 = f"https://{HOSTNAME}/Auth/OAuth/Token"
URL_BASE_V2 = f"https://{HOSTNAME}/WebAPI/emea/api/v1"

HEADERS_BASE = {
    "Accept": "application/json",
    "Connection": "Keep-Alive",
}
HEADERS_CRED_V1 = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
}
HEADERS_CRED_V2 = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Authorization": "Basic " + _APPLICATION_ID_V2,
}
