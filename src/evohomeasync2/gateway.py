#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC gateways."""
from __future__ import annotations

from typing import TYPE_CHECKING, Final

from . import exceptions as exc
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
from .zone import log_any_faults

if TYPE_CHECKING:
    import logging

    from . import Broker, Location
    from .schema import _EvoDictT, _GatewayIdT


class Gateway:
    """Instance of a location's gateway."""

    STATUS_SCHEMA: Final = SCH_GATEWAY
    TYPE: Final[str] = SZ_GATEWAY

    def __init__(self, location: Location, config: _EvoDictT) -> None:
        self.location = location  # parent

        self._broker: Broker = location._broker
        self._logger: logging.Logger = location._logger

        self._status: _EvoDictT = {}
        self._config: Final[_EvoDictT] = config[SZ_GATEWAY_INFO]

        try:
            assert self.gatewayId, "Invalid config dict"
        except AssertionError as err:
            raise exc.InvalidSchema(str(err)) from err
        self._id = self.gatewayId

        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        tcs_config: _EvoDictT

        for tcs_config in config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.systemId] = tcs

    def __str__(self) -> str:
        return f"{self._id} ({self.TYPE})"

    @property
    def gatewayId(self) -> _GatewayIdT:
        ret: _GatewayIdT = self._config[SZ_GATEWAY_ID]
        return ret

    @property
    def mac(self) -> str:
        ret: str = self._config[SZ_MAC]
        return ret

    @property
    def isWiFi(self) -> bool:
        ret: bool = self._config[SZ_IS_WI_FI]
        return ret

    def _update_status(self, status: _EvoDictT) -> None:
        self._status = status
        log_any_faults(f"{self._id} ({self.TYPE})", self._logger, status)

        for tcs_status in self._status[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = self.control_systems[tcs_status[SZ_SYSTEM_ID]]
            tcs._update_status(tcs_status)
