#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config, status & schedule schemas."""
from __future__ import annotations

import os

import evohomeasync2 as evo

from . import _DEBUG_USE_MOCK_AIOHTTP
from . import mocked_server as mock


if _DEBUG_USE_MOCK_AIOHTTP:
    from .mocked_server import aiohttp
else:
    import aiohttp


def credentials():
    username = os.getenv("PYTEST_USERNAME") or "spotty.blackcat@gmail.com"
    password = os.getenv("PYTEST_PASSWORD") or "zT9@5KmWELYeqasdf99"

    # with open() as f:
    #     lines = f.readlines()
    # username = lines[0].strip()
    # password = lines[1].strip()

    return username, password


def session():
    if not _DEBUG_USE_MOCK_AIOHTTP:
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return aiohttp.ClientSession(mocked_server=mock.MockedServer(None, None))


def extract_oauth_tokens(client: evo.EvohomeClient):
    return (
        client.refresh_token,
        client.access_token,
        client.access_token_expires,
    )
