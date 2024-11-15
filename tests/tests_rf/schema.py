#!/usr/bin/env python3
"""evohome-async - tests"""

from __future__ import annotations

from typing import Final

from evohomeasync2.schema.account import factory_user_account
from evohomeasync2.schema.config import factory_user_locations_installation_info
from evohomeasync2.schema.helpers import camel_to_snake
from evohomeasync2.schema.status import (
    factory_dhw_status,
    factory_loc_status,
    factory_tcs_status,
    factory_zone_status,
)

SCH_DHW_STATUS: Final = factory_dhw_status(camel_to_snake)
SCH_FULL_CONFIG: Final = factory_user_locations_installation_info(camel_to_snake)
SCH_LOCN_STATUS: Final = factory_loc_status(camel_to_snake)
SCH_TCS_STATUS: Final = factory_tcs_status(camel_to_snake)
SCH_USER_ACCOUNT: Final = factory_user_account(camel_to_snake)
SCH_ZONE_STATUS: Final = factory_zone_status(camel_to_snake)
