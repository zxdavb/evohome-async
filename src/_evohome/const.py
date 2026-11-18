"""Constants shared by the v1 and v2 clients."""

from __future__ import annotations

from enum import StrEnum
from http import HTTPStatus
from typing import Final

from aiohttp import hdrs

# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DONT_REDACT_SECRETS = False  # default is to redact sensitive JSON in debug output

HOSTNAME: Final = "tccna.resideo.com"

# the message of a NotFetchedError of the config (the others are with their users)
_ERR_NO_CONFIG: Final = "{} not available until after EvohomeClient.setup() is called"


class ContentType(StrEnum):
    """The media types of a request/response (the stdlib has no such constants)."""

    JSON = "application/json"
    TEXT_HTML = "text/html"
    TEXT_PLAIN = "text/plain"


# No need for a Content-Type header, as aiohttp sets it from the body:
# - POSTs: data=  -> application/x-www-form-urlencoded (the auth requests)
# - PUTs:  json=  -> application/json
# - GETs:  (no body)

HEADERS_BASE = {
    hdrs.ACCEPT: ContentType.JSON,
    hdrs.CONNECTION: "Keep-Alive",  # TODO: remove: HTTP/1.1 keeps alive by default
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
