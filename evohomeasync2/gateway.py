#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of a TCC gateway."""

from __future__ import annotations
from typing import TYPE_CHECKING, Final

from .controlsystem import ControlSystem
from .schema.const import (
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_IS_WI_FI,
    SZ_MAC,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
)

if TYPE_CHECKING:
    from . import Location
    from .typing import _GatewayIdT

# _LOGGER = logging.getLogger(__name__)


class Gateway:
    """Instance of a location's Gateway."""

    def __init__(self, location: Location, gwy_config: dict) -> None:
        self.location = location  # parent

        self._config: Final[dict] = gwy_config[SZ_GATEWAY_INFO]
        assert self.gatewayId, "Invalid config dict"

        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        for tcs_config in gwy_config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.systemId] = tcs

    # config attrs...
    @property
    def gatewayId(self) -> _GatewayIdT:
        return self._config[SZ_GATEWAY_ID]

    @property
    def mac(self) -> str:
        return self._config[SZ_MAC]

    @property
    def isWiFi(self) -> bool:
        return self._config[SZ_IS_WI_FI]
