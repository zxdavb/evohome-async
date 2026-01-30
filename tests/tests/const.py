"""Tests for evohome-async - helper functions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from _evohome.const import HINT_BAD_CREDS, HINT_CHECK_NETWORK

TEST_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TEST_DIR / "fixtures"


MSG_INVALID_SESSION: Final = (
    "The session_id has been rejected (will re-authenticate): "
    "GET https://tccna.resideo.com/WebAPI/api/accountInfo: "
    '401 Unauthorized, response=[{"code": "Unauthorized", "message": "Unauthorized"}]'
)

MSG_INVALID_TOKEN: Final = (
    "The access_token has been rejected (will re-authenticate): "  # noqa: S105
    "GET https://tccna.resideo.com/WebAPI/emea/api/v1/userAccount: "
    '401 Unauthorized, response=[{"code": "Unauthorized", "message": "Unauthorized"}]'
)


LOG_01 = ("evohome_cli.auth", logging.DEBUG, "Fetching access_token...")
LOG_02 = ("evohome_cli.auth", logging.DEBUG, " - authenticating with the refresh_token")  # fmt: off
LOG_03 = ("evohome_cli.auth", logging.DEBUG, "Expired/invalid refresh_token")
LOG_04 = ("evohome_cli.auth", logging.DEBUG, " - authenticating with client_id/secret")  # fmt: off

LOG_21 = ("evohome_cli.auth", logging.DEBUG, "Fetching session_id...")
LOG_24 = ("evohome_cli.auth", logging.DEBUG, " - authenticating with client_id/secret")  # fmt: off

LOG_90 = ("evohome_cli.auth", logging.ERROR, HINT_BAD_CREDS)
LOG_99 = ("evohome_cli.auth", logging.ERROR, HINT_CHECK_NETWORK)

LOG_00 = ("evohomeasync", logging.WARNING, MSG_INVALID_SESSION)
LOG_09 = ("evohomeasync.auth", logging.ERROR, HINT_CHECK_NETWORK)

LOG_20 = ("evohomeasync2", logging.WARNING, MSG_INVALID_TOKEN)
LOG_29 = ("evohomeasync2.auth", logging.ERROR, HINT_CHECK_NETWORK)
