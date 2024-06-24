#!/usr/bin/env python3
"""Provides handling of TCC gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from .controlsystem import ControlSystem
from .schema.const import (
    SZ_GATEWAY,
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_IS_WI_FI,
    SZ_MAC,
    SZ_SYSTEM_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
)
from .schema.status import SCH_GATEWAY
from .zone import ActiveFaultsBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Location
    from .schema import _EvoDictT, _GatewayIdT


class Gateway(ActiveFaultsBase):
    """Instance of a location's gateway."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_GATEWAY
    TYPE: Final = SZ_GATEWAY  # type: ignore[misc]

    def __init__(self, location: Location, config: _EvoDictT) -> None:
        super().__init__(
            config[SZ_GATEWAY_INFO][SZ_GATEWAY_ID], location._broker, location._logger
        )

        self.location = location

        self._config: Final[_EvoDictT] = config[SZ_GATEWAY_INFO]
        self._status: _EvoDictT = {}

        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        tcs_config: _EvoDictT
        for tcs_config in config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.systemId] = tcs

    @property
    def gatewayId(self) -> _GatewayIdT:
        return self._id

    @property
    def mac(self) -> str:
        ret: str = self._config[SZ_MAC]
        return ret

    @property
    def isWiFi(self) -> bool:
        ret: bool = self._config[SZ_IS_WI_FI]
        return ret

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

        for tcs_status in self._status[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            if tcs := self.control_systems.get(tcs_status[SZ_SYSTEM_ID]):
                tcs._update_status(tcs_status)

            else:
                self._logger.warning(
                    f"{self}: system_id='{tcs_status[SZ_SYSTEM_ID]}' not known"
                    ", (has the gateway configuration been changed?)"
                )
