#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for vendor's RESTful API JSON."""
from __future__ import annotations

try:
    from .account import SCH_USER_ACCOUNT as SCH_USER_ACCOUNT
    from .account import SCH_OAUTH_TOKEN
    from .config import SCH_LOCATION_INSTALLATION_INFO as SCH_LOCN_CONFIG
    from .config import SCH_USER_LOCATIONS_INSTALLATION_INFO as SCH_FULL_CONFIG
    from .schedule import SCH_SCHEDULE_GET as SCH_SCHEDULE
    from .status import SCH_DHW as SCH_DHW_STATUS
    from .status import SCH_LOCATION_STATUS as SCH_LOCN_STATUS
    from .status import SCH_TEMPERATURE_CONTROL_SYSTEM as SCH_TCS_STATUS
    from .status import SCH_ZONE as SCH_ZONE_STATUS

except ModuleNotFoundError:  # No module named 'voluptuous'
    SCH_DHW_STATUS = dict
    SCH_FULL_CONFIG = list
    SCH_LOCN_CONFIG = dict
    SCH_LOCN_STATUS = dict
    SCH_OAUTH_TOKEN = dict
    SCH_TCS_STATUS = dict
    SCH_USER_ACCOUNT = dict
    SCH_SCHEDULE = dict
    SCH_ZONE_STATUS = dict
