#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of a TCC gateway."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .controlsystem import ControlSystem

if TYPE_CHECKING:
    from . import EvohomeClient, Location
    from .typing import _GatewayIdT


# _LOGGER = logging.getLogger(__name__)


class Gateway:
    """Instance of a location's Gateway."""

    gatewayId: _GatewayIdT
    #

    def __init__(
        self, client: EvohomeClient, location: Location, gwy_config: dict
    ) -> None:
        self.client = client
        self.location = location

        self.__dict__.update(gwy_config["gatewayInfo"])
        assert self.gatewayId, "Invalid config dict"

        self._control_systems: list[ControlSystem] = []
        self.control_systems: dict[str, ControlSystem] = {}  # tcs by id

        for tcs_config in gwy_config["temperatureControlSystems"]:
            tcs = ControlSystem(client, location, self, tcs_config)

            self._control_systems.append(tcs)
            self.control_systems[tcs.systemId] = tcs
