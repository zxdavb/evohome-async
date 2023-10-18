#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Config JSON."""
from __future__ import annotations

from .account import SCH_USER_ACCOUNT as SCH_USER_ACCOUNT  # noqa: ignore[F401]
from .account import SCH_OAUTH_TOKEN  # noqa: ignore[F401]
from .config import (  # noqa: ignore[F401]
    SCH_LOCATION_INSTALLATION_INFO as SCH_LOCN_CONFIG,
    SCH_USER_LOCATIONS_INSTALLATION_INFO as SCH_FULL_CONFIG,
)
from .status import SCH_LOCATION_STATUS as SCH_LOCN_STATUS  # noqa: ignore[F401]
