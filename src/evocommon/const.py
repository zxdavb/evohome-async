#!/usr/bin/env python3
"""evohomeasync - shared constants."""

from __future__ import annotations

# all _DBG_* flags should be False for published code
_DBG_DONT_OBFUSCATE = False  # default is to obfuscate sensitive JSON in debug output

REGEX_EMAIL_ADDRESS = r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"
