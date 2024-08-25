#!/usr/bin/env python3
"""Tests for the evohome-async client library."""

from __future__ import annotations

import logging


class ClientStub:
    broker = None
    _logger = logging.getLogger(__name__)


class GatewayStub:
    _broker = None
    _logger = logging.getLogger(__name__)
    location = None
