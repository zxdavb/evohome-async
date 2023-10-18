#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for RESTful API Config JSON."""
from __future__ import annotations

from .account import SCH_USER_ACCOUNT  # noqa: ignore[F401]
from .config import SCH_USER_LOCATIONS_INSTALLATION_INFO as SCH_FULL_CONFIG # noqa: ignore[F401]
from .status import SCH_LOCATION_STATUS as SCH_LOCN_STATUS  # noqa: ignore[F401]
