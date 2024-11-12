#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from .auth import AbstractSessionManager, Auth  # noqa: F401
from .exceptions import (  # noqa: F401
    AuthenticationFailedError,
    EvohomeError,
    InvalidSchemaError,
    RateLimitExceededError,
    RequestFailedError,
)
from .main import EvohomeClientOld as _EvohomeClient
from .schema import (  # noqa: F401
    SZ_ALLOWED_MODES,
    SZ_CHANGEABLE_VALUES,
    SZ_DEVICE_ID,
    SZ_DEVICES,
    SZ_DHW_OFF,
    SZ_DHW_ON,
    SZ_DOMESTIC_HOT_WATER,
    SZ_EMEA_ZONE,
    SZ_HEAT_SETPOINT,
    SZ_HOLD,
    SZ_ID,
    SZ_INDOOR_TEMPERATURE,
    SZ_LOCATION_ID,
    SZ_MODE,
    SZ_NAME,
    SZ_NEXT_TIME,
    SZ_QUICK_ACTION,
    SZ_QUICK_ACTION_NEXT_TIME,
    SZ_SCHEDULED,
    SZ_SETPOINT,
    SZ_STATUS,
    SZ_TEMP,
    SZ_TEMPORARY,
    SZ_THERMOSTAT,
    SZ_THERMOSTAT_MODEL_TYPE,
    SZ_USER_INFO,
    SZ_VALUE,
)

__version__ = "1.2.0"


class EvohomeClient(_EvohomeClient):
    """An async client for v0 of the Resideo TCC API."""
