#!/usr/bin/env python3
"""Provides handling of TCC gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import voluptuous as vol

from .control_system import ControlSystem
from .schema import SCH_GWY_STATUS
from .schema.const import (
    S2_GATEWAY_ID,
    S2_GATEWAY_INFO,
    S2_IS_WI_FI,
    S2_MAC,
    S2_SYSTEM_ID,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    EntityType,
)
from .zone import ActiveFaultsBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Location
    from .schema import _EvoDictT


class Gateway(ActiveFaultsBase):
    """Instance of a location's gateway."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_GWY_STATUS
    TYPE: Final = EntityType.GWY  # type: ignore[misc]

    def __init__(self, location: Location, config: _EvoDictT) -> None:
        super().__init__(
            config[S2_GATEWAY_INFO][S2_GATEWAY_ID],
            location._broker,
            location._logger,
        )

        self.location = location  # parent

        self._config: Final[_EvoDictT] = config[S2_GATEWAY_INFO]
        self._status: _EvoDictT = {}

        # children
        self.control_systems: list[ControlSystem] = []
        self.control_system_by_id: dict[str, ControlSystem] = {}  # tcs by id

        tcs_config: _EvoDictT
        for tcs_config in config[S2_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_config)

            self.control_systems.append(tcs)
            self.control_system_by_id[tcs.id] = tcs

    @property
    def mac(self) -> str:
        ret: str = self._config[S2_MAC]
        return ret

    @property
    def is_wi_fi(self) -> bool:
        ret: bool = self._config[S2_IS_WI_FI]
        return ret

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

        for tcs_status in self._status[S2_TEMPERATURE_CONTROL_SYSTEMS]:
            if tcs := self.control_system_by_id.get(tcs_status[S2_SYSTEM_ID]):
                tcs._update_status(tcs_status)

            else:
                self._logger.warning(
                    f"{self}: system_id='{tcs_status[S2_SYSTEM_ID]}' not known"
                    ", (has the gateway configuration been changed?)"
                )
