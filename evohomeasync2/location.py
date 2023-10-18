#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of a TCC location."""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Final, NoReturn

from .const import URL_BASE
from .gateway import Gateway
from .schema import SCH_LOCN_STATUS
from .schema.const import (
    SZ_COUNTRY,
    SZ_GATEWAYS,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_LOCATION_OWNER,
    SZ_LOCATION_TYPE,
    SZ_NAME,
    SZ_TIME_ZONE,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
)

if TYPE_CHECKING:
    from . import EvohomeClient, ControlSystem
    from .typing import _LocationIdT


_LOGGER = logging.getLogger(__name__)


class Location:
    """Instance of an account's Location."""

    def __init__(self, client: EvohomeClient, loc_config: dict) -> None:
        self.client = client
        self._client = client._client

        self._config: Final[dict] = loc_config[SZ_LOCATION_INFO]
        assert self.locationId, "Invalid config dict"

        self._gateways: list[Gateway] = []
        self.gateways: dict[str, Gateway] = {}  # gwy by id

        for gwy_config in loc_config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_config)

            self._gateways.append(gwy)
            self.gateways[gwy.gatewayId] = gwy

    @property
    def country(self) -> str:
        return self._config[SZ_COUNTRY]

    @property
    def locationOwner(self) -> dict:
        return self._config[SZ_LOCATION_OWNER]

    @property
    def locationId(self) -> _LocationIdT:
        return self._config[SZ_LOCATION_ID]

    @property
    def locationType(self) -> str:
        return self._config[SZ_LOCATION_TYPE]

    @property
    def name(self) -> str:
        return self._config[SZ_NAME]

    @property
    def timeZone(self) -> dict:
        return self._config[SZ_TIME_ZONE]

    @property
    def useDaylightSaveSwitching(self) -> bool:
        return self._config[SZ_USE_DAYLIGHT_SAVE_SWITCHING]

    async def status(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "Location.status() is deprecated, use .refresh_status()"
        )

    async def refresh_status(self) -> dict:
        """Update the Location with its latest status (also returns the status)."""

        url = f"location/{self.locationId}/status?includeTemperatureControlSystems=True"
        response = await self._client("GET", f"{URL_BASE}/{url}")
        loc_status: dict = SCH_LOCN_STATUS(response)
        self._update_state(loc_status)
        return loc_status

    def _update_state(self, state: dict) -> None:
        tcs: ControlSystem  # mypy
        tcs_status: dict  # mypy

        for gwy_status in state["gateways"]:
            gateway = self.gateways[gwy_status["gatewayId"]]

            for tcs_status in gwy_status["temperatureControlSystems"]:
                tcs = gateway.control_systems[tcs_status["systemId"]]

                tcs._update_state(
                    {
                        "systemModeStatus": tcs_status["systemModeStatus"],
                        "activeFaults": tcs_status["activeFaults"],
                    }
                )

                if dhw_status := tcs_status.get("dhw"):
                    tcs.hotwater._update_state(dhw_status)  # type: ignore[union-attr]

                for zone_status in tcs_status["zones"]:
                    tcs.zones_by_id[zone_status["zoneId"]]._update_state(zone_status)
