"""Schema for the vendor's TCC v2 API - for PUT state of TCS/Zone/DHW.

These TypedDict & StrEnums serve as documentation of the vendor's API, even if they are
unused by this library. There are corresponding factory functions for the voluptuous
schemas, which can be used to validate/coerce the vendor's responses.

The vendor's convention for well-known strings:
- camelCase for JSON keys, URL params (e.g. "userId", "streetAddress", "period")
- PascalCase for JSON values that are enum strings (e.g. "TemporaryOverride", "Period")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from evohomeasync2.const import DhwState, SystemMode, ZoneMode


class TccSetDhwModeT(TypedDict):
    """PUT /domesticHotWater/{dhw_id}/state"""

    mode: ZoneMode
    state: NotRequired[DhwState | None]  # required by override modes
    untilTime: NotRequired[str | None]  # required by TemporaryOverride mode


class TccSetTcsModeT(TypedDict):
    """PUT /temperatureControlSystem/{tcs_id}/mode"""

    systemMode: SystemMode
    permanent: bool
    timeUntil: NotRequired[str]


class TccSetZonModeT(TypedDict):
    """PUT /temperatureZone/{zon_id}/heatSetpoint"""

    setpointMode: ZoneMode
    heatSetpointValue: NotRequired[float]  # required by override modes
    timeUntil: NotRequired[str]  # required by TemporaryOverride mode
