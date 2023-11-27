#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked vendor RESTful API via a hacked aiohttp."""
from __future__ import annotations

from . import aiohttp  # noqa: F401
from .const import GHOST_ZONE_ID  # noqa: F401
from .vendor import MockedServer  # noqa: F401
