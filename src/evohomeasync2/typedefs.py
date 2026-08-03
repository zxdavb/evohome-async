"""evohomeasync schema - shared types (WIP).

TypeDicts may not be complete (the API is undocumented), but all keys referenced
by this library are present

API endpoints marked 'extrapolated' are inferred by symmetry - they are not
exercised by the test suite and may not exist
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from datetime import datetime as dt

    from .const import (
        DayOfWeek,
        DhwState,
        FanMode,
        FaultType,
        LocationType,
        SystemMode,
        TcsModelType,
        TimingMode,
        ZoneMode,
        ZoneModelType,
        ZoneType,
    )


#######################################################################################
# Schema for the POSTs for the vendor's RESTful API


# POST /Auth/OAuth/Token
class EvoAuthTokensResponseT(TypedDict):
    """Response to `POST /Auth/OAuth/Token`."""

    access_token: str
    expires_in: int  # seconds until access token expires
    refresh_token: str
    scope: str
    token_type: str


#######################################################################################
# Schema for the GETs for the vendor's RESTful API - config/status endpoints


# GET /userAccount
class EvoUsrAccountResponseT(TypedDict):
    """Response to `GET /userAccount`."""

    user_id: str


# GET Entity Configuration...


# GET /location/installationInfo?userId={user_id}&include...  (a list of these dicts)
# GET /location/{loc_id}/installationInfo??includeTemperatureControlSystems=True
class EvoLocConfigResponseT(TypedDict):
    """Response to `GET /locations.../installationInfo...`.

    Response to: `GET /location/installationInfo?userId={user_id}&?includeTemperatureControlSystems=True`
    - the response is a list of these dicts

    Response to: `GET /location/{loc_id}/installationInfo?includeTemperatureControlSystems=True`
    - the response is a single dict
    """

    location_info: EvoLocationInfoT
    gateways: list[EvoGwyConfigResponseT]


class EvoLocationInfoT(TypedDict):
    """Location configuration information."""

    location_id: str
    name: str
    street_address: str
    city: str
    country: str
    postcode: str
    location_type: LocationType
    use_daylight_save_switching: bool
    time_zone: EvoTimeZoneT
    location_owner: EvoLocationOwnerT


class EvoTimeZoneT(TypedDict):
    """Time zone information."""

    time_zone_id: str
    display_name: str
    offset_minutes: int
    current_offset_minutes: int
    supports_daylight_saving: bool


class EvoLocationOwnerT(TypedDict):
    user_id: str
    username: str
    firstname: str
    lastname: str


# GET /gateway/{gwy_id}/... (extrapolated)
class EvoGwyConfigResponseT(TypedDict):
    """Response to `GET /gateway/{gwy_id}/...`."""

    gateway_info: EvoGatewayInfoT
    temperature_control_systems: list[EvoTcsConfigResponseT]


class EvoGatewayInfoT(TypedDict):
    gateway_id: str
    mac: str
    crc: str
    is_wi_fi: bool


# GET /temperatureControlSystem/{tcs_id}/... (extrapolated)
class _EvoTcsConfigResponseBaseT(TypedDict):
    system_id: str
    model_type: TcsModelType
    allowed_system_modes: list[EvoAllowedSystemModesT]


class EvoAllowedSystemModesT(TypedDict):
    system_mode: SystemMode
    can_be_permanent: Literal[True]  # only ever seen: True
    can_be_temporary: bool
    max_duration: NotRequired[str]  # when can_be_temporary is True
    timing_resolution: NotRequired[str]  # when can_be_temporary is True
    timing_mode: NotRequired[TimingMode]  # when can_be_temporary is True


class EvoTcsConfigResponseT(_EvoTcsConfigResponseBaseT):
    """Response to `GET /temperatureControlSystem/{tcs_id}/...`."""

    # system_id: str
    # model_type: str
    # allowed_system_modes: list[dict[str, Any]]
    zones: list[EvoZonConfigResponseT]
    dhw: NotRequired[EvoDhwConfigResponseT]


# GET /temperatureZone/{zon_id}/... (extrapolated)
class EvoZonConfigResponseT(TypedDict):
    """Response to `GET /temperatureZone/{zon_id}/...`."""

    zone_id: str
    model_type: ZoneModelType
    name: str
    setpoint_capabilities: EvoZonSetpointCapabilitiesT
    # Some FocusProWifiRetail do not include ScheduleCapabilities in their config
    # but it is always present for Evohome
    schedule_capabilities: NotRequired[EvoZonScheduleCapabilitiesT]
    zone_type: ZoneType
    allowed_fan_modes: NotRequired[list[EvoAllowedFanModesT]]  # FocusProWifi


class EvoZonSetpointCapabilitiesT(TypedDict):
    allowed_setpoint_modes: list[ZoneMode]
    can_control_cool: bool
    can_control_heat: bool
    max_heat_setpoint: float
    min_heat_setpoint: float
    value_resolution: float
    max_duration: str
    timing_resolution: str
    # following seen on FocusProWifi, not Evohome...
    max_cool_setpoint: NotRequired[float]
    min_cool_setpoint: NotRequired[float]
    setpoint_deadband: NotRequired[float]
    vacation_hold_capabilities: NotRequired[EvoVacationHoldCapabilitiesT]


class EvoVacationHoldCapabilitiesT(TypedDict):
    is_changeable: bool
    is_cancelable: bool
    # the three below are either all present, or all absent
    max_duration: NotRequired[str]
    min_duration: NotRequired[str]
    timing_resolution: NotRequired[str]


class _EvoScheduleCapabilitiesT(TypedDict):  # shared by Zone and DHW
    max_switchpoints_per_day: int
    min_switchpoints_per_day: int
    timing_resolution: str


class EvoZonScheduleCapabilitiesT(_EvoScheduleCapabilitiesT):
    setpoint_value_resolution: float


class EvoAllowedFanModesT(TypedDict):
    fan_mode: FanMode


# GET /domesticHotWater/{dhw_id}/... (extrapolated)
class EvoDhwConfigResponseT(TypedDict):
    """Response to `GET /domesticHotWater/{dhw_id}/...`."""

    dhw_id: str
    # FocusProWifiRetail may not include DhwScheduleCapabilitiesResponse in their config
    # but it is always present for Evohome
    schedule_capabilities_response: NotRequired[EvoDhwScheduleCapabilitiesT]
    dhw_state_capabilities_response: EvoDhwStateCapabilitiesT


class EvoDhwScheduleCapabilitiesT(_EvoScheduleCapabilitiesT):
    pass


class EvoDhwStateCapabilitiesT(TypedDict):
    allowed_states: list[DhwState]
    allowed_modes: list[ZoneMode]
    max_duration: str
    timing_resolution: str


# GET Entity Status...


# GET /location/{loc_id}/status?includeTemperatureControlSystems=True
class _EvoLocStatusResponseBaseT(TypedDict):
    location_id: str


class EvoLocStatusResponseT(_EvoLocStatusResponseBaseT):
    """Response to `GET /location/{loc_id}/status?includeTemperatureControlSystems=True`."""

    gateways: list[EvoGwyStatusResponseT]


# GET /gateway/{gwy_id}/status (extrapolated)
class _EvoGwyStatusResponseBaseT(TypedDict):
    gateway_id: str
    active_faults: list[EvoActiveFaultT]


class EvoGwyStatusResponseT(_EvoGwyStatusResponseBaseT):
    """Response to `GET /gateway/{gwy_id}/status`."""

    temperature_control_systems: list[EvoTcsStatusResponseT]


class EvoActiveFaultT(TypedDict):
    fault_type: FaultType | str  # may be unknown/unexpected value, so allow str
    since: dt  # TZ-naive, no 'Z' suffix in the vendor string


# GET /temperatureControlSystem/{tcs_id}/status
class _EvoTcsStatusResponseBaseT(TypedDict):
    system_id: str
    active_faults: list[EvoActiveFaultT]
    system_mode_status: EvoSystemModeStatusT


class EvoTcsStatusResponseT(_EvoTcsStatusResponseBaseT):
    """Response to `GET /temperatureControlSystem/{tcs_id}/status`."""

    zones: list[EvoZonStatusResponseT]
    dhw: NotRequired[EvoDhwStatusResponseT]


class EvoSystemModeStatusT(TypedDict):
    mode: SystemMode
    is_permanent: bool
    time_until: NotRequired[dt]  # TZ-aware


# GET /temperatureZone/{zon_id}/status
class EvoZonStatusResponseT(TypedDict):
    """Response to `GET /temperatureZone/{zon_id}/status`."""

    zone_id: str
    active_faults: list[EvoActiveFaultT]
    setpoint_status: EvoZonSetpointStatusT
    temperature_status: EvoTemperatureStatusT
    name: str
    fan_status: NotRequired[EvoFanStatusT]  # FocusProWifi


class EvoZonSetpointStatusT(TypedDict):
    setpoint_mode: ZoneMode
    target_heat_temperature: float
    until: NotRequired[dt]  # TZ-aware


class EvoTemperatureStatusT(TypedDict):
    is_available: bool
    temperature: NotRequired[float]


class EvoFanStatusT(TypedDict):
    fan_mode: FanMode
    can_be_changed: bool


# GET /domesticHotWater/{dhw_id}/status
class EvoDhwStatusResponseT(TypedDict):
    """Response to `GET /domesticHotWater/{dhw_id}/status`."""

    dhw_id: str
    active_faults: list[EvoActiveFaultT]
    state_status: EvoDhwStateStatusT
    temperature_status: EvoTemperatureStatusT


class EvoDhwStateStatusT(TypedDict):
    mode: ZoneMode
    state: DhwState
    until: NotRequired[dt]  # TZ-aware


#######################################################################################
# Schema for the PUTs for the vendor's RESTful API - set state endpoints


# PUT /domesticHotWater/{dhw_id}/state
class EvoSetDhwStateT(TypedDict):
    mode: ZoneMode
    state: NotRequired[DhwState]  # required by override modes
    until_time: NotRequired[dt | str]  # required by TemporaryOverride


# PUT /temperatureControlSystem/{tcs_id}/mode
class EvoSetSystemModeT(TypedDict):
    system_mode: SystemMode
    permanent: bool
    time_until: NotRequired[dt | str]  # required by TemporaryOverride


# PUT /temperatureZone/{zon_id}/heatSetpoint
class EvoSetZoneHeatSetpointT(TypedDict):
    setpoint_mode: ZoneMode
    heat_setpoint_value: NotRequired[float]  # required by override modes
    time_until: NotRequired[dt | str]  # required by TemporaryOverride


#######################################################################################
# Schema for the GET/PUT the vendor's RESTful API - Zone/DHW Schedules...


# GET /domesticHotWater/{dhw_id}/schedule
class EvoDhwScheduleResponseT(TypedDict):
    """Response to `GET /domesticHotWater/{dhw_id}/schedule`."""

    daily_schedules: list[EvoDhwScheduleDayOfWeekT]


class EvoScheduleDhwT(EvoDhwScheduleResponseT):  # for export/import to/from file
    """Schedule for a DHW, for export/import to/from file."""

    dhw_id: str
    name: NotRequired[str]


class EvoDhwScheduleDayOfWeekT(TypedDict):
    day_of_week: DayOfWeek
    switchpoints: list[EvoDhwScheduleSwitchpointT]


class EvoDhwScheduleSwitchpointT(TypedDict):
    dhw_state: DhwState
    time_of_day: str


# GET /temperatureZone/{zon_id}/schedule
class EvoZonScheduleResponseT(TypedDict):
    """Response to `GET /temperatureZone/{zon_id}/schedule`."""

    daily_schedules: list[EvoZonScheduleDayOfWeekT]


class EvoScheduleZoneT(EvoZonScheduleResponseT):  # for export/import to/from file
    """Schedule for a zone, for export/import to/from file."""

    zone_id: str
    name: NotRequired[str]


class EvoZonScheduleDayOfWeekT(TypedDict):
    day_of_week: DayOfWeek
    switchpoints: list[EvoZonScheduleSwitchpointT]


class EvoZonScheduleSwitchpointT(TypedDict):
    heat_setpoint: float
    time_of_day: str


# These are to be deprecated in favour of the above
class EvoSwitchpointT(TypedDict):
    time_of_day: str
    dhw_state: NotRequired[DhwState]  # mutex with heat_setpoint
    heat_setpoint: NotRequired[float]


class EvoDayOfWeekT(TypedDict):
    day_of_week: DayOfWeek
    switchpoints: list[EvoSwitchpointT]


class EvoDailySchedulesT(TypedDict):
    daily_schedules: list[EvoDayOfWeekT]


class EvoScheduleT(EvoDailySchedulesT):  # for export/import to/from file
    """Schedule for a zone or DHW, for export/import to/from file."""

    dhw_id: NotRequired[str]  # exactly one of these two IDs will be present
    zone_id: NotRequired[str]
    name: NotRequired[str]  # would normally be present, but be OK if not


#######################################################################################
# Schema for the entity's own attrs, as returned by its .config / .status properties...
#
# These are what the library exposes; the Evo*ResponseT types above are what a GET
# returns. For the container entities (LOC, GWY, TCS) the two differ, as the GET
# response also carries their children's config/status - so these derive from the
# Evo*EntryT that both have in common. The leaf entities (ZON, DHW) have no children,
# so their pair is equivalent and these derive from the Evo*ResponseT directly.


class EvoLocConfigT(EvoLocationInfoT):
    """Configuration of a location."""


class EvoGwyConfigT(EvoGatewayInfoT):
    """Configuration of a gateway."""


class EvoTcsConfigT(_EvoTcsConfigResponseBaseT):
    """Configuration of a temperature control system."""


class EvoZonConfigT(EvoZonConfigResponseT):
    """Configuration of a zone."""


class EvoDhwConfigT(EvoDhwConfigResponseT):
    """Configuration of a DHW."""


#


class EvoLocStatusT(_EvoLocStatusResponseBaseT):
    """Status of a location."""


class EvoGwyStatusT(_EvoGwyStatusResponseBaseT):
    """Status of a gateway."""


class EvoTcsStatusT(_EvoTcsStatusResponseBaseT):
    """Status of a temperature control system."""


class EvoZonStatusT(EvoZonStatusResponseT):
    """Status of a zone."""


class EvoDhwStatusT(EvoDhwStatusResponseT):
    """Status of a DHW."""


#######################################################################################
# Pythonic voluptuous schemas...
#
# These validate the JSON returned by the vendor API (after its keys have been
# converted to snake_case by AbstractAuth.request) and coerce the enum string values
# to the user-facing enum members above (e.g. "Auto" -> SystemMode.AUTO). The matching
# vendor-cased schemas (TCC_GET_*) remain in schemas/__init__.py.


# EVO_USR_ACCOUNT: Final = factory_user_account(Case.PYTHONIC)
# EVO_USR_LOCATIONS: Final = factory_user_locations_installation_info(Case.PYTHONIC)
# EVO_LOC_CONFIG: Final = factory_location_installation_info(Case.PYTHONIC)

# EVO_LOC_STATUS: Final = factory_loc_status(Case.PYTHONIC)
# EVO_GWY_STATUS: Final = factory_gwy_status(Case.PYTHONIC)
# EVO_TCS_STATUS: Final = factory_tcs_status(Case.PYTHONIC)
# EVO_DHW_STATUS: Final = factory_dhw_status(Case.PYTHONIC)
# EVO_ZON_STATUS: Final = factory_zon_status(Case.PYTHONIC)

# EVO_DHW_SCHEDULE: Final = factory_dhw_schedule(Case.PYTHONIC)
# EVO_ZON_SCHEDULE: Final = factory_zon_schedule(Case.PYTHONIC)
