#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Schema for vendor's RESTful API JSON."""
from __future__ import annotations

from .account import SCH_OAUTH_TOKEN, SCH_USER_ACCOUNT as SCH_USER_ACCOUNT  # noqa: F401
from .config import (  # noqa: F401
    SCH_LOCATION_INSTALLATION_INFO as SCH_LOCN_CONFIG,
    SCH_USER_LOCATIONS_INSTALLATION_INFO as SCH_FULL_CONFIG,
)
from .const import (  # noqa: F401
    DHW_STATES,
    SYSTEM_MODES,
    ZONE_MODES,
    DhwState,
    SystemMode,
    ZoneMode,
)
from .schedule import (  # noqa: F401
    SCH_GET_SCHEDULE,
    SCH_PUT_SCHEDULE,
    convert_to_get_schedule,
)
from .status import (  # noqa: F401
    SCH_DHW as SCH_DHW_STATUS,
    SCH_LOCATION_STATUS as SCH_LOCN_STATUS,
    SCH_TEMPERATURE_CONTROL_SYSTEM as SCH_TCS_STATUS,
    SCH_ZONE as SCH_ZONE_STATUS,
)
from .typing import (  # noqa: F401
    _DhwIdT,
    _EvoDictT,
    _EvoLeafT,
    _EvoListT,
    _EvoSchemaT,
    _FilePathT,
    _GatewayIdT,
    _LocationIdT,
    _ModeT,
    _ScheduleT,
    _SystemIdT,
    _UserIdT,
    _ZoneIdT,
)
