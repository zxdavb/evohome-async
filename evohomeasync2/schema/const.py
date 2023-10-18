#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 - Constants."""

from enum import EnumCheck, StrEnum, verify
import re
from typing import Final


# all debug flags should be False for published code
_DEBUG_DONT_OBSFUCATE = False  # used for pytest scripts


REGEX_DHW_ID = r"[0-9]*"
REGEX_EMAIL_ADDRESS = r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"
REGEX_GATEWAY_ID = r"[0-9]*"
REGEX_LOCATION_ID = r"[0-9]*"
REGEX_SYSTEM_ID = r"[0-9]*"
REGEX_ZONE_ID = r"[0-9]*"

SZ_ACCESS_TOKEN = "access_token"
SZ_ACTIVE_FAULTS = "activeFaults"
SZ_ALLOWED_MODES = "allowedModes"
SZ_ALLOWED_SETPOINT_MODES = "allowedSetpointModes"
SZ_ALLOWED_STATES = "allowedStates"
SZ_ALLOWED_SYSTEM_MODES = "allowedSystemModes"

SZ_CAN_BE_PERMANENT = "canBePermanent"
SZ_CAN_BE_TEMPORARY = "canBeTemporary"
SZ_CAN_CONTROL_COOL = "canControlCool"
SZ_CAN_CONTROL_HEAT = "canControlHeat"
SZ_CITY = "city"
SZ_COUNTRY = "country"
SZ_CRC = "crc"
SZ_CURRENT_OFFSET_MINUTES = "currentOffsetMinutes"

SZ_DHW = "dhw"
SZ_DHW_ID = "dhwId"
SZ_DHW_STATE_CAPABILITIES_RESPONSE = "dhwStateCapabilitiesResponse"
SZ_DISPLAY_NAME = "displayName"

SZ_EXPIRES_IN = "expires_in"

SZ_FAULT_TYPE = "faultType"
SZ_FIRSTNAME = "firstname"
SZ_FOLLOW_SCHEDULE = "FollowSchedule"

SZ_GATEWAY_ID = "gatewayId"
SZ_GATEWAY_INFO = "gatewayInfo"
SZ_GATEWAYS = "gateways"

SZ_HEATING_ZONE = "HeatingZone"

SZ_IS_AVAILABLE = "isAvailable"
SZ_IS_WI_FI = "isWiFi"
SZ_IS_PERMANENT = "isPermanent"

SZ_LANGUAGE = "language"
SZ_LASTNAME = "lastname"
SZ_LOCATION_ID = "locationId"
SZ_LOCATION_INFO = "locationInfo"
SZ_LOCATION_OWNER = "locationOwner"
SZ_LOCATION_TYPE = "locationType"

SZ_MAC = "mac"
SZ_MAX_DURATION = "maxDuration"
SZ_MAX_HEAT_SETPOINT = "maxHeatSetpoint"
SZ_MAX_SWITCHPOINTS_PER_DAY = "maxSwitchpointsPerDay"
SZ_MIN_HEAT_SETPOINT = "minHeatSetpoint"
SZ_MIN_SWITCHPOINTS_PER_DAY = "minSwitchpointsPerDay"
SZ_MODE = "mode"
SZ_MODEL_TYPE = "modelType"

SZ_NAME = "name"

SZ_OFFSET_MINUTES = "offsetMinutes"

SZ_PERMANENT_OVERRIDE = "PermanentOverride"
SZ_POSTCODE = "postcode"

SZ_RADIATOR_ZONE = "RadiatorZone"
SZ_REFRESH_TOKEN = "refresh_token"

SZ_SCHEDULE_CAPABILITIES = "scheduleCapabilities"
SZ_SCHEDULE_CAPABILITIES_RESPONSE = "scheduleCapabilitiesResponse"
SZ_SCOPE = "scope"
SZ_SETPOINT_CAPABILITIES = "setpointCapabilities"
SZ_SETPOINT_MODE = "setpointMode"
SZ_SETPOINT_STATUS = "setpointStatus"
SZ_SETPOINT_VALUE_RESOLUTION = "setpointValueResolution"
SZ_SINCE = "since"
SZ_STATE = "state"
SZ_STATE_STATUS = "stateStatus"
SZ_STREET_ADDRESS = "streetAddress"
SZ_SUPPORTS_DAYLIGHT_SAVING = "supportsDaylightSaving"
SZ_SYSTEM_ID = "systemId"
SZ_SYSTEM_MODE = "systemMode"
SZ_SYSTEM_MODE_STATUS = "systemModeStatus"

SZ_TARGET_HEAT_TEMPERATURE = "targetHeatTemperature"
SZ_TEMPERATURE = "temperature"
SZ_TEMPERATURE_CONTROL_SYSTEMS = "temperatureControlSystems"
SZ_TEMPERATURE_STATUS = "temperatureStatus"
SZ_TEMPORARY_OVERRIDE = "TemporaryOverride"
SZ_TIME_ZONE = "timeZone"
SZ_TIME_ZONE_ID = "timeZoneId"
SZ_TIMING_MODE = "timingMode"
SZ_TIMING_RESOLUTION = "timingResolution"
SZ_TOKEN_TYPE = "token_type"

SZ_UNTIL = "until"
SZ_USE_DAYLIGHT_SAVE_SWITCHING = "useDaylightSaveSwitching"
SZ_USER_ID = "userId"
SZ_USERNAME = "username"

SZ_VALUE_RESOLUTION = "valueResolution"

SZ_ZONE_ID = "zoneId"
SZ_ZONE_TYPE = "zoneType"
SZ_ZONES = "zones"


@verify(EnumCheck.UNIQUE)
class ZoneMode(StrEnum):
    FOLLOW_SCHEDULE: Final[str] = SZ_FOLLOW_SCHEDULE
    PERMANENT_OVERRIDE: Final[str] = SZ_PERMANENT_OVERRIDE
    TEMORARY_OVERRIDE: Final[str] = SZ_TEMPORARY_OVERRIDE


@verify(EnumCheck.UNIQUE)
class DhwState(StrEnum):
    OFF: Final[str] = "On"
    ON: Final[str] = "Off"


@verify(EnumCheck.UNIQUE)
class SystemMode(StrEnum):
    AUTO: Final[str] = "Auto"
    AUTO_WITH_ECO: Final[str] = "AutoWithEco"
    AUTO_WITH_RESET: Final[str] = "AutoWithReset"
    AWAY: Final[str] = "Away"
    CUSTOM: Final[str] = "Custom"
    DAY_OFF: Final[str] = "DayOff"
    HEATING_OFF: Final[str] = "HeatingOff"


@verify(EnumCheck.UNIQUE)
class FaultType(StrEnum):
    TZACL: Final[str] = "TempZoneActuatorCommunicationLost"
    TZALB: Final[str] = "TempZoneActuatorLowBattery"
    TZSCL: Final[str] = "TempZoneSensorCommunicationLost"
    TZSLB: Final[str] = "TempZoneSensorLowBattery"


@verify(EnumCheck.UNIQUE)
class TcsModelType(StrEnum):
    EVO_TOUCH: Final[str] = "EvoTouch"


@verify(EnumCheck.UNIQUE)
class ZoneModelType(StrEnum):
    HEATING_ZONE: Final[str] = "HeatingZone"
    ROUND_WIRELESS: Final[str] = "RoundWireless"
    UNKNOWN: Final[str] = "Unknown"


@verify(EnumCheck.UNIQUE)
class ZoneType(StrEnum):
    RADIATOR_ZONE: Final[str] = "RadiatorZone"
    THERMOSTAT: Final[str] = "Thermostat"  # ZoneValves
    ZONE_VALVES: Final[str] = "ZoneValves"
    UNKNOWN: Final[str] = "Unknown"


def obfuscate(value: bool | int | str):
    if _DEBUG_DONT_OBSFUCATE:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"obfuscate() expects bool | int | str, got {type(value)}")
    if re.match(REGEX_EMAIL_ADDRESS, value):
        return "nobody@nowhere.com"
    return "********"
