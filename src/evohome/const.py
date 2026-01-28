"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Final

# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DONT_OBFUSCATE = False  # default is to redact sensitive JSON in debug output

HOSTNAME: Final = "tccna.resideo.com"

REGEX_EMAIL_ADDRESS = re.compile(
    r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"
)


# No need to indicate "Content-Type" as default is "charset=utf-8", with:
# - POST: "Content-Type": "application/json"                  (default)
# - GETs: "Content-Type": "application/x-www-form-urlencoded" (not required)
# - PUTs: "Content-Type": "application/json"                  (as used here)

HEADERS_BASE = {
    "Accept": "application/json",
    "Connection": "Keep-Alive",
    # "Content-Type": "application/json",
}
HEADERS_CRED = HEADERS_BASE | {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
}

HINT_CHECK_NETWORK = (
    "Unable to contact the vendor's server. Check your network "
    "and review the vendor's status page, https://status.resideo.com."
)
HINT_WAIT_A_WHILE = (
    "You have exceeded the server's API rate limit. Wait a while "
    "and try again (consider reducing your polling interval)."
)
HINT_BAD_CREDS = (
    "Failed to authenticate. Check the username/password. Note that some "
    "special characters accepted via the vendor's website are not valid here."
)

ERR_MSG_LOOKUP_BASE: dict[int, str] = {  # common to authentication / authorization
    HTTPStatus.BAD_GATEWAY: HINT_CHECK_NETWORK,
    HTTPStatus.INTERNAL_SERVER_ERROR: HINT_CHECK_NETWORK,
    HTTPStatus.SERVICE_UNAVAILABLE: HINT_CHECK_NETWORK,
    HTTPStatus.TOO_MANY_REQUESTS: HINT_WAIT_A_WHILE,
}
# WIP: POST authentication url (i.e. /Auth/OAuth/Token)
_OUT_ERR_MSG_LOOKUP_CRED: dict[int, str] = ERR_MSG_LOOKUP_BASE | {
    HTTPStatus.BAD_REQUEST: "Invalid user credentials (check the username/password)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid URL?)",
    HTTPStatus.UNAUTHORIZED: "Invalid access token (dev/test only?)",
}
# WIP: GET/PUT resource url (e.g. /WebAPI/emea/api/v1/...)
_OUT_ERR_MSG_LOOKUP_AUTH: dict[int, str] = ERR_MSG_LOOKUP_BASE | {
    HTTPStatus.BAD_REQUEST: "Bad request (invalid data/json?)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid entity type?)",
    HTTPStatus.UNAUTHORIZED: "Unauthorized (expired access token/unknown entity id?)",
}
