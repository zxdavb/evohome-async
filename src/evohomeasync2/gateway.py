#!/usr/bin/env python3
"""Provides handling of TCC gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NoReturn

import voluptuous as vol

from . import exceptions as exc
from .controlsystem import ControlSystem
from .schema import SCH_GWY_STATUS, camel_to_snake
from .schema.const import (
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_IS_WI_FI,
    SZ_MAC,
    SZ_SYSTEM_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    EntityType,
)
from .zone import ActiveFaultsBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Location
    from .schema import _EvoDictT


class _GatewayDeprecated:  # pragma: no cover
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def gatewayId(self) -> NoReturn:
        raise exc.DeprecationError(f"{self}: .gatewayId is deprecated, use .id")


class Gateway(_GatewayDeprecated, ActiveFaultsBase):
    """Instance of a location's gateway."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_GWY_STATUS
    TYPE: Final = EntityType.GWY  # type: ignore[misc]

    def __init__(self, location: Location, config: _EvoDictT) -> None:
        super().__init__(
            config[camel_to_snake(SZ_GATEWAY_INFO)][camel_to_snake(SZ_GATEWAY_ID)],
            location._broker,
            location._logger,
        )

        self.location = location  # parent

        self._config: Final[_EvoDictT] = config[camel_to_snake(SZ_GATEWAY_INFO)]
        self._status: _EvoDictT = {}

        # children
        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        tcs_config: _EvoDictT
        for tcs_config in config[camel_to_snake(SZ_TEMPERATURE_CONTROL_SYSTEMS)]:
            tcs = ControlSystem(self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.id] = tcs

    @property
    def mac(self) -> str:
        ret: str = self._config[SZ_MAC]
        return ret

    @property
    def isWiFi(self) -> bool:
        ret: bool = self._config[camel_to_snake(SZ_IS_WI_FI)]
        return ret

    def _update_status(self, status: _EvoDictT) -> None:
        super()._update_status(status)  # process active faults

        self._status = status

        for tcs_status in self._status[camel_to_snake(SZ_TEMPERATURE_CONTROL_SYSTEMS)]:
            if tcs := self.control_systems.get(
                tcs_status[camel_to_snake(SZ_SYSTEM_ID)]
            ):
                tcs._update_status(tcs_status)

            else:
                self._logger.warning(
                    f"{self}: system_id='{tcs_status[camel_to_snake(SZ_SYSTEM_ID)]}' not known"
                    ", (has the gateway configuration been changed?)"
                )
