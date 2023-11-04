#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync provides an async client for the *original* Evohome API.

It is a faithful async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
from __future__ import annotations

from .client import EvohomeClient  # noqa: F401
from .exceptions import (  # noqa: F401
    AuthenticationFailed,
    EvohomeError,
    InvalidSchema,
    RateLimitExceeded,
    RequestFailed,
)


__version__ = "0.4.4"
