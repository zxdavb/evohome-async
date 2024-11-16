#!/usr/bin/env python3
"""evohomeasync schema - for vendor's RESTful API JSON."""

from __future__ import annotations

from typing import Final

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
from .helpers import camel_to_snake, convert_keys_to_snake_case, obfuscate  # noqa: F401
from .schedule import (  # noqa: F401
    SCH_PUT_SCHEDULE,
    SCH_PUT_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_ZONE,
    SCH_SCHEDULE,
    SCH_SCHEDULE_DHW,
    SCH_SCHEDULE_ZONE,
    _ScheduleT,
    convert_to_get_schedule,
    convert_to_put_schedule,
)
from .status import (  # noqa: F401
    factory_dhw_status,
    factory_gwy_status,
    factory_loc_status,
    factory_tcs_status,
    factory_zone_status,
)
from .typedefs import _EvoDictT, _EvoLeafT, _EvoListT, _EvoSchemaT, _ModeT  # noqa: F401

# GET /userAccount
SCH_GET_USER_ACCOUNT: Final = factory_user_account()

# GET /location/{location_id}/installationInfo?includeTemperatureControlSystems=True
SCH_GET_LOCATION_INSTALLATION_INFO: Final = factory_locations_installation_info()

# GET /location/installationInfo?userId={user_id}&includeTemperatureControlSystems=True
SCH_GET_USER_LOCATIONS: Final = factory_user_locations_installation_info()

# GET /location/{self.id}/status?includeTemperatureControlSystems=True
SCH_GET_LOCN_STATUS: Final = factory_loc_status()
