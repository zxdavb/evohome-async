"""Schema for vendor's TCC v2 API - for PUT state of TCS/Zone/DHW.

The convention for JSON keys is camelCase, but the API appears to be case-insensitive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from .const import DhwStateEnum, SystemModeEnum, ZoneModeEnum


class TccSetDhwModeT(TypedDict):
    """PUT /domesticHotWater/{dhw_id}/state"""

    mode: ZoneModeEnum  # strEnum
    state: NotRequired[DhwStateEnum | None]  # strEnum, required by override modes
    untilTime: NotRequired[str | None]  # required by TemporaryOverride


class TccSetTcsModeT(TypedDict):
    """PUT /temperatureControlSystem/{tcs_id}/mode"""

    systemMode: SystemModeEnum  # strEnum
    permanent: bool
    timeUntil: NotRequired[str]  # TODO: dtm?


class TccSetZonModeT(TypedDict):
    """PUT /temperatureZone/{zon_id}/heatSetpoint"""

    setpointMode: ZoneModeEnum  # strEnum
    heatSetpointValue: NotRequired[float]  # required by override modes
    timeUntil: NotRequired[str]  # required by TemporaryOverride
