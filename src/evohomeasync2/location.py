#!/usr/bin/env python3
"""Provides handling of TCC locations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NoReturn

from . import exceptions as exc
from .gateway import Gateway
from .schema import SCH_LOCN_STATUS
from .schema.const import (
    SZ_COUNTRY,
    SZ_GATEWAY_ID,
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
    import logging

    import voluptuous as vol

    from . import Broker, EvohomeClient
    from .schema import _EvoDictT, _LocationIdT


class _LocationDeprecated:
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    async def status(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .status() is deprecated, use .refresh_status()"
        )


class Location(_LocationDeprecated):
    """Instance of an account's location."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_LOCN_STATUS
    TYPE: Final = SZ_LOCATION

    def __init__(self, client: EvohomeClient, config: _EvoDictT) -> None:
        self.client = client

        self._broker: Broker = client.broker
        self._logger: logging.Logger = client._logger

        self._id: Final[_LocationIdT] = config[SZ_LOCATION_INFO][SZ_LOCATION_ID]

        self._config: Final[_EvoDictT] = config[SZ_LOCATION_INFO]
        self._status: _EvoDictT = {}

        self._gateways: list[Gateway] = []
        self.gateways: dict[str, Gateway] = {}  # gwy by id

        gwy_config: _EvoDictT
        for gwy_config in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_config)

            self._gateways.append(gwy)
            self.gateways[gwy.gatewayId] = gwy

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id='{self._id}')"

    @property
    def locationId(self) -> _LocationIdT:
        return self._id

    @property
    def country(self) -> str:
        ret: str = self._config[SZ_COUNTRY]
        return ret

    @property
    def locationOwner(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_LOCATION_OWNER]
        return ret

    @property
    def locationType(self) -> str:
        ret: str = self._config[SZ_LOCATION_TYPE]
        return ret

    @property
    def name(self) -> str:
        ret: str = self._config[SZ_NAME]
        return ret

    @property
    def timeZone(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[SZ_TIME_ZONE]
        return ret

    @property
    def useDaylightSaveSwitching(self) -> bool:
        ret: bool = self._config[SZ_USE_DAYLIGHT_SAVE_SWITCHING]
        return ret

    async def refresh_status(self) -> _EvoDictT:
        """Update the entire Location with its latest status (returns the status)."""

        status: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self._id}/status?includeTemperatureControlSystems=True",
            schema=self.STATUS_SCHEMA,
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: _EvoDictT) -> None:
        # No ActiveFaults in location node of status

        self._status = status

        for gwy_status in self._status[SZ_GATEWAYS]:
            if gwy := self.gateways.get(gwy_status[SZ_GATEWAY_ID]):
                gwy._update_status(gwy_status)

            else:
                self._logger.warning(
                    f"{self}: gateway_id='{gwy_status[SZ_GATEWAY_ID]} not known"
                    ", (has the location configuration been changed?)"
                )
