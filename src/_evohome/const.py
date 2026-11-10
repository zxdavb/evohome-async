"""Constants shared by the v1 and v2 clients."""

from __future__ import annotations

import re
from enum import StrEnum
from http import HTTPStatus
from typing import Final

from aiohttp import hdrs

# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DONT_REDACT_SECRETS = False  # default is to redact sensitive JSON in debug output

HOSTNAME: Final = "tccna.resideo.com"

# the messages of NotFetchedError
_ERR_NO_CONFIG: Final = "{} not available until after EvohomeClient.setup() is called"
_ERR_NO_STATUS: Final = (
    "{} has no state, has it been fetched via Location.get_status()?"
)
_ERR_NO_SCHEDULE: Final = "{} has no schedule, has it been fetched via .get_schedule()?"

REGEX_EMAIL_ADDRESS = re.compile(
    r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,63})$"
)


class ContentType(StrEnum):
    """The media types of a request/response (the stdlib has no such constants)."""

    JSON = "application/json"
    TEXT_PLAIN = "text/plain"


# No need to indicate "Content-Type" as default is "charset=utf-8", with:
# - POST: "Content-Type": "application/json"                  (default)
# - GETs: "Content-Type": "application/x-www-form-urlencoded" (not required)
# - PUTs: "Content-Type": "application/json"                  (as used here)

HEADERS_BASE = {
    hdrs.ACCEPT: ContentType.JSON,
    hdrs.CONNECTION: "Keep-Alive",  # TODO: remove: HTTP/1.1 keeps alive by default
    # hdrs.CONTENT_TYPE: ContentType.JSON,
}
HEADERS_CRED = HEADERS_BASE | {
    hdrs.CACHE_CONTROL: "no-cache, no-store",
    hdrs.PRAGMA: "no-cache",  # TODO: remove: HTTP/1.0 only, so Cache-Control suffices
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
