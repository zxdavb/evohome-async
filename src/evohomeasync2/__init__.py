#!/usr/bin/env python3
"""evohomeasync provides an async client for the v2 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from .auth import AbstractTokenManager, Auth  # noqa: F401
from .control_system import ControlSystem  # noqa: F401
from .exceptions import (  # noqa: F401
    AuthenticationFailedError,
    EvohomeBaseError,
    EvohomeError,
    InvalidParameterError,
    InvalidScheduleError,
    InvalidSchemaError,
    NoSingleTcsError,
    NoSystemConfigError,
    RateLimitExceededError,
    RequestFailedError,
    SystemConfigBaseError,
)
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location  # noqa: F401
from .main import EvohomeClientOld as _EvohomeClient
from .zone import Zone  # noqa: F401

__version__ = "1.2.0"


class EvohomeClient(_EvohomeClient):
    """An async client for v2 of the Resideo TCC API."""
