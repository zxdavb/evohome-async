"""evohomeasync provides an async client for the v2 Resideo TCC API."""

from typing import Final

# HDR_STRFTIME: Final = "%Y-%m-%d %H:%M:%S"  # used by HTTP headers
API_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"  # used by API


# These keys are snake_case equivalents of schema strings
SZ_ACTIVE_FAULTS: Final = "active_faults"
SZ_ALLOWED_MODES: Final = "allowed_modes"
SZ_ALLOWED_SETPOINT_MODES: Final = "allowed_setpoint_modes"
SZ_ALLOWED_SYSTEM_MODES: Final = "allowed_system_modes"
SZ_CAN_BE_PERMANENT: Final = "can_be_permanent"
SZ_CAN_BE_TEMPORARY: Final = "can_be_temporary"
SZ_COUNTRY: Final = "country"
SZ_CURRENT_OFFSET_MINUTES: Final = "current_offset_minutes"
SZ_DAILY_SCHEDULES: Final = "daily_schedules"
SZ_DHW: Final = "dhw"
SZ_DHW_ID: Final = "dhw_id"
SZ_DHW_STATE: Final = "dhw_state"
SZ_DHW_STATE_CAPABILITIES_RESPONSE: Final = "dhw_state_capabilities_response"
SZ_FAULT_TYPE: Final = "fault_type"
SZ_GATEWAY_ID: Final = "gateway_id"
SZ_GATEWAY_INFO: Final = "gateway_info"
SZ_GATEWAYS: Final = "gateways"
SZ_HEAT_SETPOINT: Final = "heat_setpoint"
SZ_IS_AVAILABLE: Final = "is_available"
SZ_LOCATION_ID: Final = "location_id"
SZ_LOCATION_INFO: Final = "location_info"
SZ_LOCATION_OWNER: Final = "location_owner"
SZ_MAC: Final = "mac"
SZ_MAX_HEAT_SETPOINT: Final = "max_heat_setpoint"
SZ_MIN_HEAT_SETPOINT: Final = "min_heat_setpoint"
SZ_MODE: Final = "mode"
SZ_MODEL_TYPE: Final = "model_type"
SZ_NAME: Final = "name"
SZ_OFFSET_MINUTES: Final = "offset_minutes"
SZ_SCHEDULE_CAPABILITIES: Final = "schedule_capabilities"
SZ_SCHEDULE_CAPABILITIES_RESPONSE: Final = "schedule_capabilities_response"
SZ_SETPOINT_CAPABILITIES: Final = "setpoint_capabilities"
SZ_SETPOINT_MODE: Final = "setpoint_mode"
SZ_SETPOINT_STATUS: Final = "setpoint_status"
SZ_SINCE: Final = "since"
SZ_STATE: Final = "state"
SZ_STATE_STATUS: Final = "state_status"
SZ_SYSTEM_ID: Final = "system_id"
SZ_SYSTEM_MODE: Final = "system_mode"
SZ_SYSTEM_MODE_STATUS: Final = "system_mode_status"
SZ_TARGET_HEAT_TEMPERATURE: Final = "target_heat_temperature"
SZ_TEMPERATURE: Final = "temperature"
SZ_TEMPERATURE_STATUS: Final = "temperature_status"
SZ_TEMPERATURE_CONTROL_SYSTEMS: Final = "temperature_control_systems"
SZ_TIME_OF_DAY: Final = "time_of_day"
SZ_TIME_UNTIL: Final = "time_until"
SZ_TIME_ZONE: Final = "time_zone"
SZ_TIME_ZONE_ID: Final = "time_zone_id"
SZ_TIMING_MODE: Final = "timing_mode"
SZ_UNTIL: Final = "until"
SZ_USE_DAYLIGHT_SAVE_SWITCHING: Final = "use_daylight_save_switching"
SZ_USER_ID: Final = "user_id"
SZ_ZONE_ID: Final = "zone_id"
SZ_ZONE_TYPE: Final = "zone_type"
SZ_ZONES: Final = "zones"


SZ_IS_PERMANENT: Final = "is_permanent"

# These keys are not in the vendor's schema
SZ_ID: Final = "id"
SZ_PERMANENT: Final = "permanent"
SZ_SCHEDULE: Final = "schedule"
SZ_SETPOINT: Final = "setpoint"
SZ_THERMOSTAT: Final = "thermostat"
