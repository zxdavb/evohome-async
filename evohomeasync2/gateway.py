#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
)
from .schema.status import SCH_GATEWAY

if TYPE_CHECKING:
    from . import Location
    from .typing import _GatewayIdT


class Gateway:
    """Instance of a location's gateway."""

    STATUS_SCHEMA = SCH_GATEWAY
    _type = SZ_GATEWAY

    def __init__(self, location: Location, config: dict) -> None:
        self.location = location  # parent

        self._broker = location._broker
        self._logger = location._logger

        self._status: dict = {}
        self._config: Final[dict] = config[SZ_GATEWAY_INFO]

        assert self.gatewayId, "Invalid config dict"
        self._id = self.gatewayId

        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        for tcs_config in config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.systemId] = tcs

    def __str__(self) -> str:
        return f"{self._id} ({self._type})"

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

    def _update_status(self, gwy_status: dict) -> None:
        self._status = gwy_status
