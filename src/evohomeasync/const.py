"""Shared constants for the vendor's TCC v1 API.

Vendor strings are camelCase (JSON keys), PascalCase (StrEnums).
"""

from typing import Final

# POST authentication url (i.e. /WebAPI/api/session)
URL_CRED: Final = "WebAPI/api/session"

# GET/PUT resource url (i.e. /WebAPI/api/...)
URL_BASE: Final = "WebAPI/api"

# GET/PUT resource urls, relative to URL_BASE
URL_ACCOUNT_INFO: Final = "accountInfo"
URL_COMM_TASK: Final = "commTasks?commTaskId={comm_task_id}"
URL_DHW_MODE: Final = "devices/{device_id}/thermostat/changeableValues"
URL_LOCATIONS: Final = "locations?userId={user_id}&allData=True"
URL_TCS_MODE: Final = "evoTouchSystems?locationId={location_id}"
URL_ZON_MODE: Final = "devices/{device_id}/thermostat/changeableValues/heatSetpoint"

SZ_ALLOWED_MODES: Final = "allowed_modes"
SZ_COUNTRY: Final = "country"
SZ_CURRENT_OFFSET_MINUTES: Final = "current_offset_minutes"
SZ_DAYLIGHT_SAVING_TIME_ENABLED: Final = "daylight_saving_time_enabled"
SZ_DEVICE_ID: Final = "device_id"
SZ_DEVICE_TYPE: Final = "device_type"
SZ_DEVICES: Final = "devices"
SZ_GATEWAY_ID: Final = "gateway_id"
SZ_ID: Final = "id"  # of a time_zone, or of a comm task
SZ_INDOOR_TEMPERATURE: Final = "indoor_temperature"
SZ_INDOOR_TEMPERATURE_STATUS: Final = "indoor_temperature_status"
SZ_INSTANCE: Final = "instance"
SZ_IS_AVAILABLE: Final = "is_available"
SZ_LATEST_EULA_ACCEPTED: Final = "latest_eula_accepted"
SZ_LOCATION_ID: Final = "location_id"
SZ_MAC_ID: Final = "mac_id"
SZ_MAX_HEAT_SETPOINT: Final = "max_heat_setpoint"
SZ_MIN_HEAT_SETPOINT: Final = "min_heat_setpoint"
SZ_NAME: Final = "name"
SZ_ONE_TOUCH_ACTIONS_SUSPENDED: Final = "one_touch_actions_suspended"
SZ_ONE_TOUCH_BUTTONS: Final = "one_touch_buttons"
SZ_PCB_NUMBER: Final = "pcb_number"
SZ_SERIAL_NUMBER: Final = "serial_number"
SZ_STATE: Final = "state"  # of a comm task
SZ_TEMPERATURE: Final = "temperature"
SZ_THERMOSTAT: Final = "thermostat"
SZ_THERMOSTAT_MODEL_TYPE: Final = "thermostat_model_type"
SZ_TIME_ZONE: Final = "time_zone"
SZ_USER_ID: Final = "user_id"
SZ_WEATHER: Final = "weather"
