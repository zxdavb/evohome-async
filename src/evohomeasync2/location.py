#!/usr/bin/env python3
"""Provides handling of TCC locations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NoReturn

from . import exceptions as exc
from .gateway import Gateway
from .schema import SCH_LOCN_STATUS, camel_to_snake
from .schema.const import (
    SZ_COUNTRY,
    SZ_GATEWAY_ID,
    SZ_GATEWAYS,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_LOCATION_OWNER,
    SZ_LOCATION_TYPE,
    SZ_NAME,
    SZ_TIME_ZONE,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
    EntityType,
)
from .zone import EntityBase

if TYPE_CHECKING:
    import voluptuous as vol

    from .base import EvohomeClient
    from .schema import _EvoDictT


class _LocationDeprecated:  # pragma: no cover
    """Deprecated attributes and methods removed from the evohome-client namespace."""

    @property
    def locationId(self) -> NoReturn:
        raise exc.DeprecationError(f"{self}: .locationId is deprecated, use .id")

    async def status(self, *args, **kwargs) -> NoReturn:  # type: ignore[no-untyped-def]
        raise exc.DeprecationError(
            f"{self}: .status() is deprecated, use .refresh_status()"
        )


class Location(_LocationDeprecated, EntityBase):
    """Instance of an account's location."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_LOCN_STATUS
    TYPE: Final = EntityType.LOC  # type: ignore[misc]

    def __init__(self, client: EvohomeClient, config: _EvoDictT) -> None:
        super().__init__(
            config[camel_to_snake(SZ_LOCATION_INFO)][camel_to_snake(SZ_LOCATION_ID)],
            client.broker,
            client._logger,
        )

        self.client = client  # proxy for parent

        self._config: Final[_EvoDictT] = config[camel_to_snake(SZ_LOCATION_INFO)]
        self._status: _EvoDictT = {}

        # children
        self._gateways: list[Gateway] = []
        self.gateways: dict[str, Gateway] = {}  # gwy by id

        gwy_config: _EvoDictT
        for gwy_config in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_config)

            self._gateways.append(gwy)
            self.gateways[gwy.id] = gwy

    @property
    def country(self) -> str:
        ret: str = self._config[SZ_COUNTRY]
        return ret

    @property
    def locationOwner(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[camel_to_snake(SZ_LOCATION_OWNER)]
        return ret

    @property
    def locationType(self) -> str:
        ret: str = self._config[camel_to_snake(SZ_LOCATION_TYPE)]
        return ret

    @property
    def name(self) -> str:
        ret: str = self._config[SZ_NAME]
        return ret

    @property
    def timeZone(self) -> _EvoDictT:
        ret: _EvoDictT = self._config[camel_to_snake(SZ_TIME_ZONE)]
        return ret

    @property
    def useDaylightSaveSwitching(self) -> bool:
        ret: bool = self._config[camel_to_snake(SZ_USE_DAYLIGHT_SAVE_SWITCHING)]
        return ret

    async def refresh_status(self) -> _EvoDictT:
        """Update the entire Location with its latest status (returns the status)."""

        status: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self.id}/status?includeTemperatureControlSystems=True",
            schema=self.STATUS_SCHEMA,
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: _EvoDictT) -> None:
        # No ActiveFaults in location node of status

        self._status = status

        for gwy_status in self._status[SZ_GATEWAYS]:
            if gwy := self.gateways.get(gwy_status[camel_to_snake(SZ_GATEWAY_ID)]):
                gwy._update_status(gwy_status)

            else:
                self._logger.warning(
                    f"{self}: gateway_id='{gwy_status[camel_to_snake(SZ_GATEWAY_ID)]} not known"
                    ", (has the location configuration been changed?)"
                )
