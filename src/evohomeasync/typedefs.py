"""evohomeasync schema - shared types.

These mirror the voluptuous schemas in schemas.py (after their keys are converted to
snake_case), and so a key is NotRequired here whenever it is vol.Optional there: that
is, whenever this library does not need it. This is deliberately not the same thing as
the vendor omitting it - the Tcc*T typed dicts remain the record of the vendor's API.
"""

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
    firstname: NotRequired[str]
    lastname: NotRequired[str]
    street_address: NotRequired[str]
    city: NotRequired[str]
    # state: str  # missing?
    zipcode: NotRequired[str]
    country: NotRequired[str]  # GB
    telephone: NotRequired[str]
    user_language: NotRequired[str]


class EvoUserAccountDictT(EvoUserAccountInfoDictT):  # NOT EvoUserAccountInfoT
    """GET api/userAccounts?userId={userId}"""

    is_activated: NotRequired[bool]
    device_count: NotRequired[int]
    tenant_id: NotRequired[int]
    security_question_1: NotRequired[str]
    security_question_2: NotRequired[str]
    security_question_3: NotRequired[str]
    latest_eula_accepted: NotRequired[bool]


class EvoLocInfoDictT(TypedDict):  # c.f. TccLocationResponseT
    location_id: _LocationIdT
    name: str
    street_address: NotRequired[str]
    city: NotRequired[str]
    state: NotRequired[str]
    country: str
    zipcode: NotRequired[str]
    type: NotRequired[str]  # LocationType: "Commercial" | "Residential"
    has_station: NotRequired[bool]
    devices: list[EvoDevInfoDictT]
    weather: NotRequired[EvoWeatherDictT]  # WeatherResponse
    daylight_saving_time_enabled: bool
    time_zone: EvoTimeZoneInfoDictT
    is_location_owner: NotRequired[bool]
    location_owner_id: int
    location_owner_name: NotRequired[str]
    location_owner_user_name: NotRequired[str]
    can_search_for_contractors: NotRequired[bool]
    contractor: NotRequired[dict[str, Any]]  # ContractorResponse


class EvoGwyInfoDictT(TypedDict):  # c.f. TccDeviceResponseT
    gateway_id: _GatewayIdT
    device_type: NotRequired[int]
    mac_id: str
    location_id: int


# These keys are in the JSON, but not in the developer docs for the API
# NOTE: domain_id/thermostat_version were once here too, but are per-device keys: they
# are not sent at the location level in any known response (c.f. EvoDevInfoDictT)
class EvoTcsInfoDictT(EvoLocInfoDictT):
    one_touch_actions_suspended: NotRequired[bool]
    one_touch_buttons: NotRequired[list[str]]


class EvoDevInfoDictT(EvoGwyInfoDictT):
    device_id: _DhwIdT | _ZoneIdT
    name: str
    # is an int for the Honeywell TH9320WF3003, else DOMESTIC_HOT_WATER or e.g. EMEA_ZONE
    thermostat_model_type: str | int
    schedule_capable: NotRequired[bool]
    hold_until_capable: NotRequired[bool]
    thermostat: EvoThermostatInfoDictT
    humidifier: NotRequired[dict[str, Any]]  # HumidifierResponse
    dehumidifier: NotRequired[dict[str, Any]]  # DehumidifierResponse
    fan: NotRequired[dict[str, Any]]  # FanResponse
    schedule: NotRequired[dict[str, Any]]  # ScheduleResponse
    alert_settings: NotRequired[dict[str, Any]]  # AlertSettingsResponse
    is_upgrading: NotRequired[bool]
    is_alive: NotRequired[bool]
    thermostat_version: NotRequired[str]
    domain_id: NotRequired[int]
    instance: int
    serial_number: NotRequired[str]
    pcb_number: NotRequired[str]
    dr_events: NotRequired[list[Any]]
    system_configuration: NotRequired[dict[str, Any]]


class EvoThermostatInfoDictT(TypedDict):
    units: NotRequired[str]  # displayedUnits: Fahrenheit or Celsius
    indoor_temperature: float
    outdoor_temperature: NotRequired[float]
    outdoor_temperature_available: NotRequired[bool]
    outdoor_humidity: NotRequired[float]
    outdoot_humidity_available: NotRequired[bool]  # NOTE: not a typo
    indoor_humidity: NotRequired[float]
    indoor_temperature_status: str  # Measured|NotAvailable|SensorError|SensorFault
    indoor_humidity_status: NotRequired[str]
    outdoor_temperature_status: NotRequired[str]
    outdoor_humidity_status: NotRequired[str]
    is_commercial: NotRequired[bool]
    allowed_modes: list[str]  # ThermostatMode
    deadband: NotRequired[float]
    min_heat_setpoint: float
    max_heat_setpoint: float
    min_cool_setpoint: NotRequired[float]
    max_cool_setpoint: NotRequired[float]
    cool_rate: NotRequired[float]
    heat_rate: NotRequired[float]
    is_pre_cool_capable: NotRequired[bool]
    changeable_values: NotRequired[Any]  # thermostatChangeableValues
    equipment_output_status: NotRequired[str]  # Off | Heating | Cooling
    schedule_capable: NotRequired[bool]
    vacation_hold_changeable: NotRequired[bool]
    vacation_hold_cancelable: NotRequired[bool]
    schedule_heat_sp: NotRequired[float]
    schedule_cool_sp: NotRequired[float]
    serial_number: NotRequired[str]
    pcb_number: NotRequired[str]


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
