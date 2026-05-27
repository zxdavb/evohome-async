"""evohomeasync schema - shared types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    from .schemas import _DhwIdT, _GatewayIdT, _LocationIdT, _UserIdT, _ZoneIdT


class EvoFailureDictT(TypedDict):
    """Typed dict for code/message responses from the vendor servers."""

    code: str
    message: str


class EvoSessionDictT(TypedDict):
    """POST api/session"""

    session_id: str
    user_info: EvoUserAccountDictT


class EvoUserAccountInfoDictT(TypedDict):  # NOTE: is not EvoUserAccountDictT
    """GET api/accountInfo"""

    user_id: _UserIdT
    username: str  # email address
    firstname: str
    lastname: str
    street_address: str
    city: str
    # state: str  # missing?
    zipcode: str
    country: str  # GB
    telephone: str
    user_language: str


class EvoUserAccountDictT(EvoUserAccountInfoDictT):  # NOT EvoUserAccountInfoT
    """GET api/userAccounts?userId={userId}"""

    is_activated: bool
    device_count: int  # NotRequired?
    tenant_id: int  # NotRequired?
    security_question_1: str  # NotRequired?
    security_question_2: str  # NotRequired?
    security_question_3: str  # NotRequired?
    latest_eula_accepted: bool  # NotRequired?


class EvoLocInfoDictT(TypedDict):  # c.f. TccLocationResponseT
    location_id: _LocationIdT
    name: str
    street_address: str
    city: str
    state: str
    country: str
    zipcode: str
    type: str  # LocationType: "Commercial" | "Residential"
    has_station: bool
    devices: list[EvoDevInfoDictT]
    weather: EvoWeatherDictT  # WeatherResponse
    daylight_saving_time_enabled: bool
    time_zone: EvoTimeZoneInfoDictT
    is_location_owner: bool
    location_owner_id: int
    location_owner_name: str
    location_owner_user_name: str
    can_searchforcontractors: bool
    contractor: NotRequired[dict[str, Any]]  # ContractorResponse


class EvoGwyInfoDictT(TypedDict):  # c.f. TccDeviceResponseT
    gateway_id: _GatewayIdT
    device_type: int
    mac_id: str
    location_id: int
    serial_number: str
    pcb_number: str


# These keys are in the JSON, but not in the developer docs for the API
class EvoTcsInfoDictT(EvoLocInfoDictT):
    domain_id: int
    one_touch_actions_suspended: bool
    one_touch_buttons: list[str]
    thermostat_version: str


class EvoDevInfoDictT(EvoGwyInfoDictT):
    device_id: _DhwIdT | _ZoneIdT
    name: str
    thermostat_model_type: str  # DOMESTIC_HOT_WATER or a zone, e.g. EMEA_ZONE
    schedule_capable: bool
    hold_until_capable: bool
    thermostat: EvoThermostatInfoDictT
    humidifier: dict[str, Any]  # HumidifierResponse
    dehumidifier: dict[str, Any]  # DehumidifierResponse
    fan: dict[str, Any]  # FanResponse
    schedule: dict[str, Any]  # ScheduleResponse
    alert_settings: dict[str, Any]  # AlertSettingsResponse
    is_upgrading: bool
    is_alive: bool
    instance: int


class EvoThermostatInfoDictT(TypedDict):
    units: str  # displayedUnits: Fahrenheit or Celsius
    indoor_temperature: float
    outdoor_temperature: float
    outdoor_temperature_available: bool
    outdoor_humidity: float
    outdoor_humidity_available: bool
    indoor_humidity: float
    indoor_temperature_status: str  # Measured|NotAvailable|SensorError|SensorFault
    indoor_humidity_status: str
    outdoor_temperature_status: str
    outdoor_humidity_status: str
    is_commercial: bool
    allowed_modes: list[str]  # ThermostatMode
    deadband: float
    min_heat_setpoint: float
    max_heat_setpoint: float
    min_cool_setpoint: float
    max_cool_setpoint: float
    cool_rate: float
    heat_rate: float
    is_pre_cool_capable: bool
    changeable_values: Any  # thermostatChangeableValues
    equipment_output_status: str  # Off | Heating | Cooling
    schedule_capable: bool
    vacation_hold_changeable: bool
    vacation_hold_cancelable: bool
    schedule_heat_sp: float
    schedule_cool_sp: float
    serial_number: str
    pcb_number: str


class EvoWeatherDictT(TypedDict):
    condition: str  # an enum
    temperature: float
    units: str  # Fahrenheit (precision 1.0) or Celsius (0.5)
    humidity: int
    phrase: str


class EvoTimeZoneInfoDictT(TypedDict):
    id: str
    display_name: str
    offset_minutes: int
    current_offset_minutes: int
    using_daylight_saving_time: bool
