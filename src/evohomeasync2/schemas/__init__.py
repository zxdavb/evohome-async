#!/usr/bin/env python3
"""evohomeasync schema - for vendor's RESTful API JSON."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import voluptuous as vol

from evohome.helpers import noop

from .account import factory_user_account
from .config import (
    factory_locations_installation_info,
    factory_user_locations_installation_info,
)
from .const import (  # noqa: F401
    DHW_STATES,
    SYSTEM_MODES,
    ZONE_MODES,
    DhwState,
    SystemMode,
    ZoneMode,
)
from .schedule import factory_schedule_dhw, factory_schedule_zone  # noqa: F401
from .status import (
    factory_dhw_status,
    factory_gwy_status,  # noqa: F401
    factory_loc_status,
    factory_tcs_status,
    factory_zone_status,
)
from .typedefs import _EvoDictT, _EvoLeafT, _EvoListT, _EvoSchemaT, _ModeT  # noqa: F401

#
# HTTP GET/PUT (& POST) schemas are camelCase, not snake_case...

# GET /userAccount
SCH_GET_USER_ACCOUNT: Final = factory_user_account()

# GET /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
SCH_GET_USER_LOCATIONS: Final = factory_user_locations_installation_info()

# GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True
SCH_GET_LOCATION_INSTALLATION_INFO: Final = factory_locations_installation_info()

# GET /location/{loc_id}/status?includeTemperatureControlSystems=True
SCH_GET_LOCN_STATUS: Final = factory_loc_status()

# GET /temperatureControlSystem/{tcs_id}/status"
SCH_GET_TCS_STATUS: Final = factory_tcs_status()

# GET /domesticHotWater/{dhw_id}/status"
SCH_GET_DHW_STATUS: Final = factory_dhw_status()

# GET /temperatureZone/{zone_id}/heatSetpoint"
# TODO:

# GET /temperatureZone/{zone_id}/status"
SCH_GET_ZONE_STATUS: Final = factory_zone_status()

# GET /domesticHotWater/{dhw_id}/schedule"
SCH_GET_SCHEDULE_DHW: Final = factory_schedule_dhw()

# PUT /domesticHotWater/{dhw_id}/schedule"
# TODO: same as SCH_GET_SCHEDULE_DHW?

# GET /temperatureZone/{zone_id}/schedule"
SCH_GET_SCHEDULE_ZONE: Final = factory_schedule_zone()

# PUT /temperatureZone/{zone_id}/schedule"
# TODO: same as SCH_GET_SCHEDULE_ZONE?


# for convenience...
def factory_get_schedule(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the schedule schema."""

    from . import SCH_GET_SCHEDULE_DHW, SCH_GET_SCHEDULE_ZONE

    return vol.Schema(
        vol.Any(SCH_GET_SCHEDULE_DHW, SCH_GET_SCHEDULE_ZONE),
        extra=vol.PREVENT_EXTRA,
    )


SCH_GET_SCHEDULE: Final = factory_get_schedule()
