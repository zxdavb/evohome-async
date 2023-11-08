#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for vendor's RESTful API JSON."""
from __future__ import annotations

try:
    import voluptuous as vol  # type: ignore[import-untyped]

    from .account import SCH_USER_ACCOUNT as SCH_USER_ACCOUNT
    from .config import (
        SCH_LOCATION_INSTALLATION_INFO as SCH_LOCN_CONFIG,
        SCH_USER_LOCATIONS_INSTALLATION_INFO as SCH_FULL_CONFIG,
    )
    from .schedule import SCH_GET_SCHEDULE, SCH_PUT_SCHEDULE
    from .status import (
        SCH_DHW as SCH_DHW_STATUS,
        SCH_LOCATION_STATUS as SCH_LOCN_STATUS,
        SCH_TEMPERATURE_CONTROL_SYSTEM as SCH_TCS_STATUS,
        SCH_ZONE as SCH_ZONE_STATUS,
    )

except (AttributeError, ModuleNotFoundError):  # No module named 'voluptuous'
    from .helpers import vol  # noqa: F401

    SCH_DHW_STATUS = dict
    SCH_FULL_CONFIG = list
    SCH_LOCN_CONFIG = dict
    SCH_LOCN_STATUS = dict
    SCH_OAUTH_TOKEN = dict
    SCH_TCS_STATUS = dict
    SCH_USER_ACCOUNT = dict
    SCH_GET_SCHEDULE = dict
    SCH_PUT_SCHEDULE = dict
    SCH_ZONE_STATUS = dict

from .const import (  # noqa: F401
    DHW_STATES,
    SYSTEM_MODES,
    ZONE_MODES,
    DhwState,
    SystemMode,
    ZoneMode,
)
from .schedule import convert_to_get_schedule  # noqa: F401
from .typing import (  # noqa: F401  # noqa: F401  # noqa: F401
    _DhwIdT,
    _EvoDictT,
    _EvoLeafT,
    _EvoListT,
    _EvoSchemaT,
    _FilePathT,
    _GatewayIdT,
    _LocationIdT,
    _ModeT,
    _SystemIdT,
    _UserIdT,
    _ZoneIdT,
)
