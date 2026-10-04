"""evohomeasync provides an async client for the v0 Resideo TCC API.

It is an async port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

from __future__ import annotations

from .auth import AbstractSessionManager
from .entities import ControlSystem, Gateway, HotWater, Location, Zone
from .exceptions import (
    ApiCallFailedError,
    ApiRateLimitExceededError,
    ApiRequestFailedError,
    AuthenticationFailedError,
    BadApiRequestError,
    BadApiResponseError,
    BadApiSchemaError,
    BadScheduleUploadedError,
    BadUserCredentialsError,
    ConfigError,
    EvohomeError,
    InvalidConfigError,
    InvalidScheduleError,
    InvalidStatusError,
    NoSingleTcsError,
    StatusError,
)
from .main import EvohomeClient
from .schemas import (  # noqa: F401
    S1_ALLOWED_MODES as SZ_ALLOWED_MODES,
    S1_CHANGEABLE_VALUES as SZ_CHANGEABLE_VALUES,
    S1_DEVICE_ID as SZ_DEVICE_ID,
    S1_DEVICES as SZ_DEVICES,
    S1_HEAT_SETPOINT as SZ_HEAT_SETPOINT,
    S1_INDOOR_TEMPERATURE as SZ_INDOOR_TEMPERATURE,
    S1_LOCATION_ID as SZ_LOCATION_ID,
    S1_MODE as SZ_MODE,
    S1_NAME as SZ_NAME,
    S1_NEXT_TIME as SZ_NEXT_TIME,
    S1_QUICK_ACTION as SZ_QUICK_ACTION,
    S1_QUICK_ACTION_NEXT_TIME as SZ_QUICK_ACTION_NEXT_TIME,
    S1_STATUS as SZ_STATUS,
    S1_THERMOSTAT as SZ_THERMOSTAT,
    S1_THERMOSTAT_MODEL_TYPE as SZ_THERMOSTAT_MODEL_TYPE,
    S1_USER_INFO as SZ_USER_INFO,
    S1_VALUE as SZ_VALUE,
    TccCommTaskState,
    TccDhwMode,
    TccEquipmentOutputStatus,
    TccLocationType,
    TccSensorStatus,
    TccSetpointStatus,
    TccSystemMode,
    TccThermostatMode,
    TccThermostatModelType,
)

__all__ = [  # noqa: RUF022
    "EvohomeClient",
    "AbstractSessionManager",
    #
    "Location",
    "Gateway",
    "ControlSystem",
    "Zone",
    "HotWater",
    #
    "TccCommTaskState",
    "TccDhwMode",
    "TccEquipmentOutputStatus",
    "TccLocationType",
    "TccSensorStatus",
    "TccSetpointStatus",
    "TccSystemMode",
    "TccThermostatMode",
    "TccThermostatModelType",
    #
    "ApiCallFailedError",
    "ApiRateLimitExceededError",
    "ApiRequestFailedError",
    "AuthenticationFailedError",
    "BadApiRequestError",
    "BadApiResponseError",
    "BadApiSchemaError",
    "BadScheduleUploadedError",
    "BadUserCredentialsError",
    "ConfigError",
    "EvohomeError",
    "InvalidConfigError",
    "InvalidScheduleError",
    "InvalidStatusError",
    "NoSingleTcsError",
    "StatusError",
]
