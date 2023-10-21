#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config, status & schedule schemas."""
from __future__ import annotations

import os

import evohomeasync2 as evo

import mocked_server as mock


def credentials():
    username = os.getenv("PYTEST_USERNAME")
    password = os.getenv("PYTEST_PASSWORD")

    return username, password


def session():
    session = mock.ClientSession(mocked_server=mock.MockedServer(None, None))
    # session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return session


def extract_oauth_tokens(client: evo.EvohomeClient):
    return (
        client.refresh_token,
        client.access_token,
        client.access_token_expires,
    )
