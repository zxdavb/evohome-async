"""Schema for vendor's TCC v2 API - for PUT state of TCS/Zone/DHW.

The convention for JSON keys is camelCase, but the API appears to be case-insensitive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from .const import DhwState, SystemMode, ZoneMode


class TccSetDhwModeT(TypedDict):
    """PUT /domesticHotWater/{dhw_id}/state"""

    mode: ZoneMode
    state: NotRequired[DhwState | None]  # required by override modes
    untilTime: NotRequired[str | None]  # required by TemporaryOverride


class TccSetTcsModeT(TypedDict):
    """PUT /temperatureControlSystem/{tcs_id}/mode"""

    systemMode: SystemMode
    permanent: bool
    timeUntil: NotRequired[str]  # TODO: dtm?


class TccSetZonModeT(TypedDict):
    """PUT /temperatureZone/{zon_id}/heatSetpoint"""

    setpointMode: ZoneMode
    heatSetpointValue: NotRequired[float]  # required by override modes
    timeUntil: NotRequired[str]  # required by TemporaryOverride
