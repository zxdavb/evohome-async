"""
Honeywell Total Connect Comfort (TCC) Web API - Python Schema
=============================================================
Application : EMEA App
API version : 1.0
Base URL    : https://mytotalconnectcomfort.com/WebApi/

Dependencies
------------
    pip install voluptuous

Conventions
-----------
* All TypedDicts mirror the JSON keys exactly (camelCase) as returned/sent
  by the API.  Voluptuous Schema objects enforce the same structure at
  runtime.
* Optional fields use voluptuous.Optional(); fields that may be null in the
  response are wrapped in a union validator via voluptuous.Any(type, None).
* Enums use Python's stdlib ``enum.Enum``; the voluptuous schemas accept the
  *string* value of each enum member (as the JSON serialization uses strings).
"""

from __future__ import annotations

from enum import EnumCheck, StrEnum, verify

import voluptuous as vol
from typing_extensions import TypedDict  # use typing.TypedDict on Python ≥ 3.8

# ============================================================================
# Enumerations
# ============================================================================


@verify(EnumCheck.UNIQUE)
class ThermostatModeEnum(StrEnum):
    """All possible modes the thermostat can be set in."""

    EMERGENCY_HEAT = "EmergencyHeat"
    HEAT = "Heat"
    OFF = "Off"
    COOL = "Cool"
    AUTO_HEAT = "AutoHeat"  # Autochangeover, active heating
    AUTO_COOL = "AutoCool"  # Autochangeover, active cooling
    SOUTHERN_AWAY = "SouthernAway"  # Special dehumidification mode
    DHW_OFF = "DHWOff"  # EMEA Domestic Hot Water - OFF
    DHW_ON = "DHWOn"  # EMEA Domestic Hot Water - ON


@verify(EnumCheck.UNIQUE)
class SetpointStatusEnum(StrEnum):
    """State of a setpoint / overall thermostat hold status."""

    SCHEDULED = "Scheduled"
    TEMPORARY = "Temporary"
    HOLD = "Hold"
    VACATION_HOLD = "VacationHold"


@verify(EnumCheck.UNIQUE)
class DisplayedUnitsEnum(StrEnum):
    """Temperature units displayed by the thermostat."""

    FAHRENHEIT = "Fahrenheit"  # whole-number scale
    CELSIUS = "Celsius"  # 0.5-degree scale


@verify(EnumCheck.UNIQUE)
class EquipmentStatusEnum(StrEnum):
    """Current output status of the HVAC equipment."""

    OFF = "Off"
    HEATING = "Heating"
    COOLING = "Cooling"


@verify(EnumCheck.UNIQUE)
class SensorStatusEnum(StrEnum):
    """Sensor reading quality."""

    MEASURED = "Measured"
    NOT_AVAILABLE = "NotAvailable"
    SENSOR_FAULT = "SensorFault"


@verify(EnumCheck.UNIQUE)
class FanModeEnum(StrEnum):
    """Fan operating modes."""

    AUTO = "Auto"
    ON = "On"
    CIRCULATE = "Circulate"
    FOLLOW_SCHEDULE = "FollowSchedule"


@verify(EnumCheck.UNIQUE)
class HumDehumModeEnum(StrEnum):
    """Humidifier / dehumidifier operating mode."""

    OFF = "Off"  # not running
    AUTO = "Auto"  # running


@verify(EnumCheck.UNIQUE)
class LocationTypeEnum(StrEnum):
    """Type of location."""

    COMMERCIAL = "Commercial"
    RESIDENTIAL = "Residential"


@verify(EnumCheck.UNIQUE)
class ScheduleDayEnum(StrEnum):
    """Day of the week used in schedule periods."""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


@verify(EnumCheck.UNIQUE)
class SchedulePeriodTypeEnum(StrEnum):
    """Period slot identifier within a scheduled day."""

    WAKE_OCC1 = "WakeOcc1"
    LEAVE_OCC2 = "LeaveOcc2"
    RETURN_OCC3 = "ReturnOcc3"
    SLEEP_OCC4 = "SleepOcc4"


@verify(EnumCheck.UNIQUE)
class ScheduleUnitEnum(StrEnum):
    """Temperature unit used in a schedule request/response."""

    CELSIUS = "C"
    FAHRENHEIT = "F"


@verify(EnumCheck.UNIQUE)
class WeatherConditionEnum(StrEnum):
    """Weather condition codes returned by the API."""

    UNKNOWN = "Unknown"
    SUNNY = "Sunny"
    MOSTLY_SUNNY = "MostlySunny"
    PARTLY_SUNNY = "PartlySunny"
    INTERMITTENT_CLOUDS = "IntermittentClouds"
    HAZY_SUNSHINE = "HazySunshine"
    MOSTLY_CLOUDY = "MostlyCloudy"
    CLOUDY = "Cloudy"
    DREARY = "Dreary"
    FOG = "Fog"
    SHOWERS = "Showers"
    MOSTLY_CLOUDY_WITH_SHOWERS = "MostlyCloudyWithShowers"
    PARTLY_SUNNY_WITH_SHOWERS = "PartlySunnyWithShowers"
    THUNDERSTORMS = "Thunderstorms"
    MOSTLY_CLOUDY_WITH_THUNDER_SHOWERS = "MostlyCloudyWithThunderShowers"
    PARTLY_SUNNY_WITH_THUNDER_SHOWERS = "PartlySunnyWithThunderShowers"
    RAIN = "Rain"
    FLURRIES = "Flurries"
    MOSTLY_CLOUDY_WITH_FLURRIES = "MostlyCloudyWithFlurries"
    PARTLY_SUNNY_WITH_FLURRIES = "PartlySunnyWithFlurries"
    SNOW = "Snow"
    MOSTLY_CLOUDY_WITH_SNOW = "MostlyCloudyWithSnow"
    ICE = "Ice"
    SLEET = "Sleet"
    FREEZING_RAIN = "FreezingRain"
    RAIN_AND_SNOW_MIXED = "RainAndSnowMixed"
    HOT = "Hot"
    COLD = "Cold"
    WINDY = "Windy"
    NIGHT_CLEAR = "NightClear"
    NIGHT_MOSTLY_CLEAR = "NightMostlyClear"
    NIGHT_PARTLY_CLOUDY = "NightPartlyCloudy"
    NIGHT_INTERMITTENT_CLOUDS = "NightIntermittentClouds"
    NIGHT_HAZY = "NightHazy"
    NIGHT_MOSTLY_CLOUDY = "NightMostlyCloudy"
    NIGHT_PARTLY_CLOUDY_WITH_SHOWERS = "NightPartlyCloudyWithShowers"
    NIGHT_MOSTLY_CLOUDY_WITH_SHOWERS = "NightMostlyCloudyWithShowers"
    NIGHT_PARTLY_CLOUDY_WITH_THUNDER_SHOWERS = "NightPartlyCloudyWithThunderShowers"
    NIGHT_MOSTLY_CLOUDY_WITH_THUNDER_SHOWERS = "NightMostlyCloudyWithThunderShowers"
    NIGHT_MOSTLY_CLOUDY_WITH_FLURRIES = "NightMostlyCloudyWithFlurries"
    NIGHT_MOSTLY_CLOUDY_WITH_SNOW = "NightMostlyCloudyWithSnow"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enum_values(enum_cls: type) -> list[str]:
    """Return the list of string values for a str-Enum, for use in validators."""
    return [e.value for e in enum_cls]


def _in_enum(enum_cls: type) -> vol.In:
    return vol.In(_enum_values(enum_cls))


# ============================================================================
# TypedDicts  (structural type hints - mirrors the JSON shapes)
# ============================================================================

# --- Shared primitives -------------------------------------------------------


class ChangeSourceDict(TypedDict, total=False):
    partnerName: str | None
    changeTag: str | None


class SetpointDict(TypedDict, total=False):
    value: float  # limited by device HeatLowerSetptLimit / HeatUpperSetptLimit
    status: str | None  # SetpointStatus value
    nextTime: str | None  # ISO-8601 datetime, no timezone


# --- Session / Auth ----------------------------------------------------------


class SessionRequestDict(TypedDict):
    username: str
    password: str
    applicationId: str


class SessionResponseDict(TypedDict, total=False):
    sessionId: str
    # (API docs do not expose the full response schema; sessionId is the key field)


class RecordCreatedResponseDict(TypedDict):
    id: int


# --- User accounts -----------------------------------------------------------


class NewUserAccountRequestDict(TypedDict, total=False):
    email: str
    password: str
    firstname: str
    lastname: str
    streetAddress: str | None
    city: str | None
    state: str | None
    zipcode: str | None
    country: str | None
    telephone: str | None
    userLanguage: str | None
    applicationID: str
    invitationKey: str | None
    sendRegistrationEmail: bool


# --- Location ----------------------------------------------------------------


class NewLocationRequestDict(TypedDict, total=False):
    name: str
    streetAddress: str | None
    city: str | None
    state: str | None
    country: str | None
    zipcode: str | None
    locationType: str  # LocationType value
    daylightSavingTimeEnabled: bool
    timeZoneID: str


class TimeZoneResponseDict(TypedDict, total=False):
    id: str
    displayName: str
    offsetMinutes: int
    currentOffsetMinutes: int
    usingDaylightSavingTime: bool


class WeatherResponseDict(TypedDict, total=False):
    condition: str  # WeatherCondition value
    temperature: float
    units: str  # DisplayedUnits value
    humidity: int
    phrase: str | None


class LocationContractorResponseDict(TypedDict, total=False):
    info: dict | None  # contractorInfoResponse (opaque)
    monitoring: dict | None  # contractorMonitoringResponse (opaque)


class LocationResponseDict(TypedDict, total=False):
    locationID: int
    name: str
    streetAddress: str | None
    city: str | None
    state: str | None
    country: str | None
    zipcode: str | None
    type: str | None  # LocationType value
    hasStation: bool
    devices: list[dict]  # List[DeviceResponseDict]
    weather: WeatherResponseDict | None
    daylightSavingTimeEnabled: bool
    timeZone: TimeZoneResponseDict | None
    isLocationOwner: bool
    locationOwnerID: int | None
    locationOwnerName: str | None
    locationOwnerUserName: str | None
    canSearchForContractors: bool
    contractor: LocationContractorResponseDict | None


# --- Thermostat / Device -----------------------------------------------------


class ThermostatChangeableValuesDict(TypedDict, total=False):
    mode: str  # ThermostatMode value
    heatSetpoint: SetpointDict | None
    coolSetpoint: SetpointDict | None
    status: str | None  # SetpointStatus (top-level)
    nextTime: str | None  # ISO-8601, no timezone
    vacationHoldDays: int | None
    modeChangeSource: ChangeSourceDict | None
    heatSetpointChangeSource: ChangeSourceDict | None
    coolSetpointChangeSource: ChangeSourceDict | None
    vacationHoldChangeSource: ChangeSourceDict | None
    autoChangeoverActiveChangeSource: ChangeSourceDict | None
    emergencyHeatActiveChangeSource: ChangeSourceDict | None


class ThermostatResponseDict(TypedDict, total=False):
    units: str  # DisplayedUnits value
    indoorTemperature: float
    outdoorTemperature: float | None
    outdoorTemperatureAvailable: bool
    outdoorHumidity: float | None
    outdoorHumidityAvailable: bool  # note: API typo preserved
    indoorHumidity: float | None
    indoorTemperatureStatus: str | None  # SensorStatus
    indoorHumidityStatus: str | None  # SensorStatus
    outdoorTemperatureStatus: str | None  # SensorStatus
    outdoorHumidityStatus: str | None  # SensorStatus
    isCommercial: bool
    allowedModes: list[str]  # List[ThermostatMode value]
    deadband: float
    minHeatSetpoint: float
    maxHeatSetpoint: float
    minCoolSetpoint: float
    maxCoolSetpoint: float
    coolRate: float | None
    heatRate: float | None
    isPreCoolCapable: bool
    changeableValues: ThermostatChangeableValuesDict | None
    equipmentOutputStatus: str | None  # EquipmentStatus
    scheduleCapable: bool
    vacationHoldChangeable: bool
    vacationHoldCancelable: bool
    scheduleHeatSp: float | None
    scheduleCoolSp: float | None
    serialNumber: str | None
    pcbNumber: str | None


class FanChangeableValuesDict(TypedDict):
    mode: str  # FanMode value


class FanResponseDict(TypedDict, total=False):
    allowedModes: list[str]  # List[FanMode value]
    changeableValues: FanChangeableValuesDict
    fanRunning: bool


class HumDehumChangeableValuesDict(TypedDict, total=False):
    mode: str  # HumDehumMode value
    setpoint: int | None  # divisible by 5


class HumidifierResponseDict(TypedDict, total=False):
    deviceId: int
    upperLimit: int
    lowerLimit: int
    deadband: int | None
    canChangeSetPoint: bool
    canChangeMode: bool
    changeableValues: HumDehumChangeableValuesDict
    frostIndex: int | None  # 1-10


class DehumidifierResponseDict(TypedDict, total=False):
    deviceId: int
    upperLimit: int
    lowerLimit: int
    canChangeSetPoint: bool
    canChangeMode: bool
    changeableValues: HumDehumChangeableValuesDict


class AlertSettingsResponseDict(TypedDict, total=False):
    deviceID: int
    tempHigherThanActive: bool
    tempHigherThan: float | None
    tempHigherThanMinutes: int | None
    tempLowerThanActive: bool
    tempLowerThan: float | None
    tempLowerThanMinutes: int | None
    humidityHigherThanActive: bool | None
    humidityHigherThan: float | None
    humidityHigherThanMinutes: int | None
    humidityLowerThanActive: bool | None
    humidityLowerThan: float | None
    humidityLowerThanMinutes: int | None
    faultConditionExistsActive: bool
    faultConditionExistsHours: int
    normalConditionsActive: bool
    communicationLostActive: bool
    communicationLostHours: int
    thermostatAlertActive: bool | None
    communicationFailureActive: bool
    communicationFailureMinutes: int
    deviceLostActive: bool
    deviceLostHours: int


class SchedulePeriodDict(TypedDict, total=False):
    day: str  # ScheduleDay value
    periodType: str  # SchedulePeriodType value
    startTime: int  # minutes from midnight
    isCancelled: bool
    heatSetpoint: float | None
    coolSetpoint: float | None
    fanMode: str | None  # FanMode value


class ScheduleRequestDict(TypedDict):
    unit: str  # ScheduleUnit value ("C" or "F")
    schedulePeriods: list[SchedulePeriodDict]


class ScheduleResponseDict(TypedDict, total=False):
    schedulePeriods: list[SchedulePeriodDict]
    maxNumberOfPeriodsInDay: int  # 2, 3 or 4
    unit: str  # "C" or "F"
    modifiedDays: list[str] | None  # List[ScheduleDay value]


class DeviceResponseDict(TypedDict, total=False):
    gatewayId: int
    deviceID: int
    thermostatModelType: int | None
    deviceType: int | None
    name: str
    scheduleCapable: bool
    holdUntilCapable: bool
    thermostat: ThermostatResponseDict | None
    humidifier: HumidifierResponseDict | None
    dehumidifier: DehumidifierResponseDict | None
    fan: FanResponseDict | None
    schedule: ScheduleResponseDict | None
    alertSettings: AlertSettingsResponseDict | None
    isUpgrading: bool
    isAlive: bool
    thermostatVersion: str | None
    macID: str | None
    locationID: int
    domainID: int | None
    instance: int | None
    serialNumber: str | None
    pcbNumber: str | None


class GatewayResponseDict(TypedDict, total=False):
    gatewayID: int
    mac: str
    crc: str | None
    devices: list[DeviceResponseDict]
    locationId: int
    isUpgrading: bool
    isRedlinkGateway: bool


# ============================================================================
# Voluptuous validator helpers
# ============================================================================


def _optional_str() -> vol.Schema:
    return vol.Any(str, None)


def _optional_float() -> vol.Schema:
    return vol.Any(float, int, None)


def _optional_int() -> vol.Schema:
    return vol.Any(int, None)


def _optional_bool() -> vol.Schema:
    return vol.Any(bool, None)


# ============================================================================
# Voluptuous Schemas
# ============================================================================

# --- Shared ------------------------------------------------------------------

CHANGE_SOURCE_SCHEMA = vol.Schema(
    {
        vol.Optional("partnerName"): _optional_str(),
        vol.Optional("changeTag"): _optional_str(),
    },
    extra=vol.ALLOW_EXTRA,
)

SETPOINT_SCHEMA = vol.Schema(
    {
        vol.Required("value"): vol.Any(float, int),
        vol.Optional("status"): vol.Any(_in_enum(SetpointStatusEnum), None),
        vol.Optional("nextTime"): _optional_str(),
    },
    extra=vol.ALLOW_EXTRA,
)

RECORD_CREATED_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): int,
    }
)

# --- Session -----------------------------------------------------------------

SESSION_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Required("applicationId"): str,
    }
)

SESSION_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("sessionId"): str,
    },
    extra=vol.ALLOW_EXTRA,
)

# --- User account ------------------------------------------------------------

NEW_USER_ACCOUNT_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
        vol.Required("firstname"): str,
        vol.Required("lastname"): str,
        vol.Optional("streetAddress"): _optional_str(),
        vol.Optional("city"): _optional_str(),
        vol.Optional("state"): _optional_str(),
        vol.Optional("zipcode"): _optional_str(),
        vol.Optional("country"): _optional_str(),
        vol.Optional("telephone"): _optional_str(),
        vol.Optional("userLanguage"): _optional_str(),
        vol.Required("applicationID"): str,
        vol.Optional("invitationKey"): _optional_str(),
        vol.Optional("sendRegistrationEmail"): bool,
    }
)

# --- Location ----------------------------------------------------------------

NEW_LOCATION_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Optional("streetAddress"): _optional_str(),
        vol.Optional("city"): _optional_str(),
        vol.Optional("state"): _optional_str(),
        vol.Optional("country"): _optional_str(),
        vol.Optional("zipcode"): _optional_str(),
        vol.Optional("locationType"): _in_enum(LocationTypeEnum),
        vol.Optional("daylightSavingTimeEnabled"): bool,
        vol.Required("timeZoneID"): str,
    }
)

TIMEZONE_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("id"): str,
        vol.Optional("displayName"): str,
        vol.Optional("offsetMinutes"): int,
        vol.Optional("currentOffsetMinutes"): int,
        vol.Optional("usingDaylightSavingTime"): bool,
    },
    extra=vol.ALLOW_EXTRA,
)

WEATHER_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("condition"): vol.Any(_in_enum(WeatherConditionEnum), None),
        vol.Optional("temperature"): vol.Any(float, int, None),
        vol.Optional("units"): vol.Any(_in_enum(DisplayedUnitsEnum), None),
        vol.Optional("humidity"): vol.Any(int, None),
        vol.Optional("phrase"): _optional_str(),
    },
    extra=vol.ALLOW_EXTRA,
)

LOCATION_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("locationID"): int,
        vol.Optional("name"): str,
        vol.Optional("streetAddress"): _optional_str(),
        vol.Optional("city"): _optional_str(),
        vol.Optional("state"): _optional_str(),
        vol.Optional("country"): _optional_str(),
        vol.Optional("zipcode"): _optional_str(),
        vol.Optional("type"): vol.Any(_in_enum(LocationTypeEnum), None),
        vol.Optional("hasStation"): bool,
        vol.Optional("devices"): list,  # validated separately
        vol.Optional("weather"): vol.Any(WEATHER_RESPONSE_SCHEMA, None),
        vol.Optional("daylightSavingTimeEnabled"): bool,
        vol.Optional("timeZone"): vol.Any(TIMEZONE_RESPONSE_SCHEMA, None),
        vol.Optional("isLocationOwner"): bool,
        vol.Optional("locationOwnerID"): _optional_int(),
        vol.Optional("locationOwnerName"): _optional_str(),
        vol.Optional("locationOwnerUserName"): _optional_str(),
        vol.Optional("canSearchForContractors"): bool,
        vol.Optional("contractor"): vol.Any(dict, None),
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Thermostat changeable values --------------------------------------------

THERMOSTAT_CHANGEABLE_VALUES_SCHEMA = vol.Schema(
    {
        vol.Optional("mode"): vol.Any(_in_enum(ThermostatModeEnum), None),
        vol.Optional("heatSetpoint"): vol.Any(SETPOINT_SCHEMA, None),
        vol.Optional("coolSetpoint"): vol.Any(SETPOINT_SCHEMA, None),
        vol.Optional("status"): vol.Any(_in_enum(SetpointStatusEnum), None),
        vol.Optional("nextTime"): _optional_str(),
        vol.Optional("vacationHoldDays"): _optional_int(),
        vol.Optional("modeChangeSource"): vol.Any(CHANGE_SOURCE_SCHEMA, None),
        vol.Optional("heatSetpointChangeSource"): vol.Any(CHANGE_SOURCE_SCHEMA, None),
        vol.Optional("coolSetpointChangeSource"): vol.Any(CHANGE_SOURCE_SCHEMA, None),
        vol.Optional("vacationHoldChangeSource"): vol.Any(CHANGE_SOURCE_SCHEMA, None),
        vol.Optional("autoChangeoverActiveChangeSource"): vol.Any(
            CHANGE_SOURCE_SCHEMA, None
        ),
        vol.Optional("emergencyHeatActiveChangeSource"): vol.Any(
            CHANGE_SOURCE_SCHEMA, None
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

THERMOSTAT_CHANGEABLE_VALUES_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required("mode"): _in_enum(ThermostatModeEnum),
        vol.Optional("heatSetpoint"): vol.Any(SETPOINT_SCHEMA, None),
        vol.Optional("coolSetpoint"): vol.Any(SETPOINT_SCHEMA, None),
        vol.Optional("status"): vol.Any(_in_enum(SetpointStatusEnum), None),
        vol.Optional("nextTime"): _optional_str(),
        vol.Optional("vacationHoldDays"): _optional_int(),
    }
)

# --- Thermostat response -----------------------------------------------------

THERMOSTAT_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("units"): vol.Any(_in_enum(DisplayedUnitsEnum), None),
        vol.Optional("indoorTemperature"): vol.Any(float, int),
        vol.Optional("outdoorTemperature"): _optional_float(),
        vol.Optional("outdoorTemperatureAvailable"): bool,
        vol.Optional("outdoorHumidity"): _optional_float(),
        vol.Optional("outdoorHumidityAvailable"): bool,  # API typo preserved
        vol.Optional("indoorHumidity"): _optional_float(),
        vol.Optional("indoorTemperatureStatus"): vol.Any(
            _in_enum(SensorStatusEnum), None
        ),
        vol.Optional("indoorHumidityStatus"): vol.Any(_in_enum(SensorStatusEnum), None),
        vol.Optional("outdoorTemperatureStatus"): vol.Any(
            _in_enum(SensorStatusEnum), None
        ),
        vol.Optional("outdoorHumidityStatus"): vol.Any(
            _in_enum(SensorStatusEnum), None
        ),
        vol.Optional("isCommercial"): bool,
        vol.Optional("allowedModes"): [_in_enum(ThermostatModeEnum)],
        vol.Optional("deadband"): vol.Any(float, int),
        vol.Optional("minHeatSetpoint"): vol.Any(float, int),
        vol.Optional("maxHeatSetpoint"): vol.Any(float, int),
        vol.Optional("minCoolSetpoint"): vol.Any(float, int),
        vol.Optional("maxCoolSetpoint"): vol.Any(float, int),
        vol.Optional("coolRate"): _optional_float(),
        vol.Optional("heatRate"): _optional_float(),
        vol.Optional("isPreCoolCapable"): bool,
        vol.Optional("changeableValues"): vol.Any(
            THERMOSTAT_CHANGEABLE_VALUES_SCHEMA, None
        ),
        vol.Optional("equipmentOutputStatus"): vol.Any(
            _in_enum(EquipmentStatusEnum), None
        ),
        vol.Optional("scheduleCapable"): bool,
        vol.Optional("vacationHoldChangeable"): bool,
        vol.Optional("vacationHoldCancelable"): bool,
        vol.Optional("scheduleHeatSp"): _optional_float(),
        vol.Optional("scheduleCoolSp"): _optional_float(),
        vol.Optional("serialNumber"): _optional_str(),
        vol.Optional("pcbNumber"): _optional_str(),
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Fan ---------------------------------------------------------------------

FAN_CHANGEABLE_VALUES_SCHEMA = vol.Schema(
    {
        vol.Required("mode"): _in_enum(FanModeEnum),
    }
)

FAN_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("allowedModes"): [_in_enum(FanModeEnum)],
        vol.Optional("changeableValues"): FAN_CHANGEABLE_VALUES_SCHEMA,
        vol.Optional("fanRunning"): bool,
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Humidifier / Dehumidifier -----------------------------------------------

HUM_DEHUM_CHANGEABLE_VALUES_SCHEMA = vol.Schema(
    {
        vol.Required("mode"): _in_enum(HumDehumModeEnum),
        vol.Optional("setpoint"): vol.Any(
            vol.All(int, lambda v: v % 5 == 0),  # must be divisible by 5
            None,
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

HUMIDIFIER_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("deviceId"): int,
        vol.Optional("upperLimit"): int,
        vol.Optional("lowerLimit"): int,
        vol.Optional("deadband"): _optional_int(),
        vol.Optional("canChangeSetPoint"): bool,
        vol.Optional("canChangeMode"): bool,
        vol.Optional("changeableValues"): HUM_DEHUM_CHANGEABLE_VALUES_SCHEMA,
        vol.Optional("frostIndex"): vol.Any(
            vol.All(int, vol.Range(min=1, max=10)),
            None,
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

DEHUMIDIFIER_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("deviceId"): int,
        vol.Optional("upperLimit"): int,
        vol.Optional("lowerLimit"): int,
        vol.Optional("canChangeSetPoint"): bool,
        vol.Optional("canChangeMode"): bool,
        vol.Optional("changeableValues"): HUM_DEHUM_CHANGEABLE_VALUES_SCHEMA,
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Alert settings ----------------------------------------------------------

ALERT_SETTINGS_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("deviceID"): int,
        vol.Optional("tempHigherThanActive"): bool,
        vol.Optional("tempHigherThan"): _optional_float(),
        vol.Optional("tempHigherThanMinutes"): _optional_int(),
        vol.Optional("tempLowerThanActive"): bool,
        vol.Optional("tempLowerThan"): _optional_float(),
        vol.Optional("tempLowerThanMinutes"): _optional_int(),
        vol.Optional("humidityHigherThanActive"): _optional_bool(),
        vol.Optional("humidityHigherThan"): vol.Any(
            vol.All(
                vol.Any(float, int),
                vol.Range(min=5, max=95),
                lambda v: v % 5 == 0,
            ),
            None,
        ),
        vol.Optional("humidityHigherThanMinutes"): _optional_int(),
        vol.Optional("humidityLowerThanActive"): _optional_bool(),
        vol.Optional("humidityLowerThan"): vol.Any(
            vol.All(
                vol.Any(float, int),
                vol.Range(min=5, max=95),
                lambda v: v % 5 == 0,
            ),
            None,
        ),
        vol.Optional("humidityLowerThanMinutes"): _optional_int(),
        vol.Optional("faultConditionExistsActive"): bool,
        vol.Optional("faultConditionExistsHours"): int,
        vol.Optional("normalConditionsActive"): bool,
        vol.Optional("communicationLostActive"): bool,
        vol.Optional("communicationLostHours"): int,
        vol.Optional("thermostatAlertActive"): _optional_bool(),
        vol.Optional("communicationFailureActive"): bool,
        vol.Optional("communicationFailureMinutes"): int,
        vol.Optional("deviceLostActive"): bool,
        vol.Optional("deviceLostHours"): int,
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Schedule ----------------------------------------------------------------

SCHEDULE_PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("day"): _in_enum(ScheduleDayEnum),
        vol.Required("periodType"): _in_enum(SchedulePeriodTypeEnum),
        vol.Required("startTime"): int,
        vol.Optional("isCancelled"): bool,
        vol.Optional("heatSetpoint"): _optional_float(),
        vol.Optional("coolSetpoint"): _optional_float(),
        vol.Optional("fanMode"): vol.Any(_in_enum(FanModeEnum), None),
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEDULE_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required("unit"): _in_enum(ScheduleUnitEnum),
        vol.Required("schedulePeriods"): [SCHEDULE_PERIOD_SCHEMA],
    }
)

SCHEDULE_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("schedulePeriods"): [SCHEDULE_PERIOD_SCHEMA],
        vol.Optional("maxNumberOfPeriodsInDay"): vol.In([2, 3, 4]),
        vol.Optional("unit"): vol.Any(_in_enum(ScheduleUnitEnum), None),
        vol.Optional("modifiedDays"): vol.Any([_in_enum(ScheduleDayEnum)], None),
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Device ------------------------------------------------------------------

DEVICE_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("gatewayId"): int,
        vol.Optional("deviceID"): int,
        vol.Optional("thermostatModelType"): _optional_int(),
        vol.Optional("deviceType"): _optional_int(),
        vol.Optional("name"): str,
        vol.Optional("scheduleCapable"): bool,
        vol.Optional("holdUntilCapable"): bool,
        vol.Optional("thermostat"): vol.Any(THERMOSTAT_RESPONSE_SCHEMA, None),
        vol.Optional("humidifier"): vol.Any(HUMIDIFIER_RESPONSE_SCHEMA, None),
        vol.Optional("dehumidifier"): vol.Any(DEHUMIDIFIER_RESPONSE_SCHEMA, None),
        vol.Optional("fan"): vol.Any(FAN_RESPONSE_SCHEMA, None),
        vol.Optional("schedule"): vol.Any(SCHEDULE_RESPONSE_SCHEMA, None),
        vol.Optional("alertSettings"): vol.Any(ALERT_SETTINGS_RESPONSE_SCHEMA, None),
        vol.Optional("isUpgrading"): bool,
        vol.Optional("isAlive"): bool,
        vol.Optional("thermostatVersion"): _optional_str(),
        vol.Optional("macID"): _optional_str(),
        vol.Optional("locationID"): int,
        vol.Optional("domainID"): _optional_int(),
        vol.Optional("instance"): _optional_int(),
        vol.Optional("serialNumber"): _optional_str(),
        vol.Optional("pcbNumber"): _optional_str(),
    },
    extra=vol.ALLOW_EXTRA,
)

# --- Gateway -----------------------------------------------------------------

GATEWAY_RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Optional("gatewayID"): int,
        vol.Optional("mac"): str,
        vol.Optional("crc"): _optional_str(),
        vol.Optional("devices"): [DEVICE_RESPONSE_SCHEMA],
        vol.Optional("locationId"): int,
        vol.Optional("isUpgrading"): bool,
        vol.Optional("isRedlinkGateway"): bool,
    },
    extra=vol.ALLOW_EXTRA,
)


# ============================================================================
# Convenience: top-level response validators
# ============================================================================

LOCATIONS_RESPONSE_SCHEMA = vol.Schema([LOCATION_RESPONSE_SCHEMA])
DEVICES_RESPONSE_SCHEMA = vol.Schema([DEVICE_RESPONSE_SCHEMA])
GATEWAYS_RESPONSE_SCHEMA = vol.Schema([GATEWAY_RESPONSE_SCHEMA])

"""
# Notes

Before finalizing, here are my questions for you — the API docs leave a few things ambiguous:

**1. `SchedulePeriodType` values** — the docs only show `"WakeOcc1"` in the sample payload. The actual period types
depend on the number of periods per day (2, 3 or 4). Do you know the full set of valid values? I've included four
common ones but there are likely more (e.g. `"LeaveOcc2"`, `"ReturnOcc3"`, `"SleepOcc4"`) for a 4-period day.

**2. `LocationType`** — the sample shows `"Commercial"` and the field is labelled "commercial or residential", but the
server-side enum page returned a 404. Should I also include `"Residential"` and anything else? (I've included both for
now.)

**3. `ThermostatModelType`** — the docs say it exists but the model page is 404. Do you have a list of valid model type
integers, or should it remain an unconstrained `int`?

**4. Strict vs. permissive validation** — I've used `extra=vol.ALLOW_EXTRA` throughout so that response schemas don't
reject unknown fields if Honeywell adds properties in a minor version bump. Would you prefer `vol.PREVENT_EXTRA` for
stricter validation, or keep it permissive?

**5. `nextTime` datetime format** — the API docs say *"format without TimeZone specification YYYY-MM-DD HH:MM:SS"* but
the sample payloads show ISO-8601 with timezone offset (e.g. `"2026-04-05T09:27:11.49+00:00"`). Should the schema
enforce the no-timezone format with a regex, or just accept any string?
"""
