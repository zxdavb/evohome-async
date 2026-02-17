"""Mocked vendor RESTful API via a hacked aiohttp."""

from __future__ import annotations

from .aiohttp import ClientSession
from .const import GHOST_ZONE_ID
from .vendor import FakedServer

__all__ = ["GHOST_ZONE_ID", "ClientSession", "FakedServer"]
