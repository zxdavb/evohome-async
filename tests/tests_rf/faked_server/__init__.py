#!/usr/bin/env python3
"""Mocked vendor RESTful API via a hacked aiohttp."""

from __future__ import annotations

# from . import aiohttp  # noqa: F401
from .aiohttp import ClientSession  # noqa: F401
from .const import GHOST_ZONE_ID  # noqa: F401
from .vendor import FakedServer  # noqa: F401
