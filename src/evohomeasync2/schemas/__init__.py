#!/usr/bin/env python3
"""evohomeasync schema - for vendor's RESTful API JSON."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import voluptuous as vol

from evohome.helpers import noop

from .account import (  # noqa: F401
    TccErrorResponseT,
    TccFailureResponseT,
    TccOAuthTokenResponseT,
    TccUsrAccountResponseT,
    factory_error_response,
    factory_post_oauth_token,
    factory_status_response,
    factory_user_account,
)
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
from .schedule import factory_schedule_dhw, factory_schedule_zone
from .status import (
    factory_dhw_status,
    factory_gwy_status,
    factory_loc_status,
    factory_tcs_status,
    factory_zone_status,
)

if TYPE_CHECKING:
    from collections.abc import Callable

#
# HTTP GET/PUT & POST schemas are camelCase, not snake_case...

TCC_ERROR_RESPONSE: Final = factory_error_response()
TCC_STATUS_RESPONSE: Final = factory_status_response()

# POST /Auth/OAuth/Token  # TODO: add this
TCC_POST_OAUTH_TOKEN: Final = factory_post_oauth_token()

# GET /userAccount
TCC_GET_USR_ACCOUNT: Final = factory_user_account()

# GET /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
TCC_GET_USR_LOCATIONS: Final = factory_user_locations_installation_info()

# GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True
TCC_GET_LOC_INSTALLATION_INFO: Final = factory_locations_installation_info()

# GET /location/{loc_id}/status?includeTemperatureControlSystems=True
TCC_GET_LOC_STATUS: Final = factory_loc_status()

# GET /gateway/{gwy_id}/status...
TCC_GET_GWY_STATUS: Final = factory_gwy_status()

# GET /temperatureControlSystem/{tcs_id}/status
TCC_GET_TCS_STATUS: Final = factory_tcs_status()

# GET /domesticHotWater/{dhw_id}/status
TCC_GET_DHW_STATUS: Final = factory_dhw_status()

# GET /temperatureZone/{zone_id}/heatSetpoint
# TODO:

# GET /temperatureZone/{zone_id}/status
TCC_GET_ZON_STATUS: Final = factory_zone_status()

# GET /domesticHotWater/{dhw_id}/schedule
TCC_GET_DHW_SCHEDULE: Final = factory_schedule_dhw()

# PUT /domesticHotWater/{dhw_id}/schedule
TCC_PUT_DHW_SCHEDULE: Final = TCC_GET_DHW_SCHEDULE

# GET /temperatureZone/{zone_id}/schedule
TCC_GET_ZON_SCHEDULE: Final = factory_schedule_zone()

# PUT /temperatureZone/{zone_id}/schedule
TCC_PUT_ZON_SCHEDULE: Final = TCC_GET_ZON_SCHEDULE


# for convenience...
def factory_get_schedule(fnc: Callable[[str], str] = noop) -> vol.Schema:
    """Factory for the schedule schema."""

    from . import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE

    return vol.Schema(
        vol.Any(TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE),
        extra=vol.PREVENT_EXTRA,
    )


TCC_GET_SCHEDULE: Final = factory_get_schedule()
TCC_PUT_SCHEDULE: Final = TCC_GET_SCHEDULE
