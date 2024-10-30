#!/usr/bin/env python3
"""evohomeasync2 schema - for vendor's RESTful API JSON."""

from __future__ import annotations

from .account import (  # noqa: F401
    SCH_OAUTH_TOKEN,
    SCH_USER_ACCOUNT,
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_EXPIRES_IN,
    SZ_REFRESH_TOKEN,
)
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
from .helpers import camel_to_snake, convert_keys_to_snake_case  # noqa: F401
from .schedule import (  # noqa: F401
    SCH_GET_SCHEDULE,
    SCH_GET_SCHEDULE_DHW,
    SCH_GET_SCHEDULE_ZONE,
    SCH_PUT_SCHEDULE,
    SCH_PUT_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_ZONE,
    _ScheduleT,
    convert_to_get_schedule,
    convert_to_put_schedule,
)
from .status import (  # noqa: F401
    SCH_DHW as SCH_DHW_STATUS,
    SCH_GATEWAY as SCH_GWY_STATUS,
    SCH_LOCATION_STATUS as SCH_LOCN_STATUS,
    SCH_TEMPERATURE_CONTROL_SYSTEM as SCH_TCS_STATUS,
    SCH_ZONE as SCH_ZONE_STATUS,
)
from .typedefs import _EvoDictT, _EvoLeafT, _EvoListT, _EvoSchemaT, _ModeT  # noqa: F401
