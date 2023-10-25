#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provides handling of TCC locations."""

from __future__ import annotations
from typing import TYPE_CHECKING, Final, NoReturn

import aiohttp

from .broker import vol
from .exceptions import FailedRequest
from .gateway import Gateway
from .schema import SCH_LOCN_STATUS
from .schema.const import (
    SZ_COUNTRY,
    SZ_GATEWAYS,
    SZ_LOCATION,
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


class _LocationDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def status(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError(
            "Location.status() is deprecated, use .refresh_status()"
        )


class Location(_LocationDeprecated):
    """Instance of an account's location."""

    STATUS_SCHEMA = SCH_LOCN_STATUS
    _type = SZ_LOCATION

    def __init__(self, client: EvohomeClient, config: dict) -> None:
        self.client = client

        self._broker = client._broker
        self._logger = client._logger

        self._config: Final[dict] = config[SZ_LOCATION_INFO]

        assert self.locationId, "Invalid config dict"
        self._id = self.locationId

        self._gateways: list[Gateway] = []
        self.gateways: dict[str, Gateway] = {}  # gwy by id

        for gwy_config in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_config)

            self._gateways.append(gwy)
            self.gateways[gwy.gatewayId] = gwy

    def __str__(self) -> str:
        return f"{self._id} ({self._type})"

    # config attrs...
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

    async def refresh_status(self) -> dict:
        """Update the Location with its latest status (also returns the status)."""

        try:
            status = await self._broker.get(
                f"{self._type}/{self._id}/status?includeTemperatureControlSystems=True",
                schema=self.STATUS_SCHEMA
            )
        except (aiohttp.ClientConnectionError, vol.Invalid) as exc:
            raise FailedRequest(f"Unable to get the Location state: {exc}")

        self._update_status(status)
        return status

    def _update_status(self, loc_status: dict) -> None:
        tcs: ControlSystem  # mypy
        tcs_status: dict  # mypy

        for gwy_status in loc_status["gateways"]:
            gwy = self.gateways[gwy_status["gatewayId"]]
            gwy._update_status(gwy_status)

            for tcs_status in gwy_status["temperatureControlSystems"]:
                tcs = gwy.control_systems[tcs_status["systemId"]]
                tcs._update_status(tcs_status)

                if dhw_status := tcs_status.get("dhw"):
                    tcs.hotwater._update_status(dhw_status)  # type: ignore[union-attr]

                for zone_status in tcs_status["zones"]:
                    tcs.zones_by_id[zone_status["zoneId"]]._update_status(zone_status)
