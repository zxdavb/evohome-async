#!/usr/bin/env python3
"""Provides handling of TCC locations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from .gateway import Gateway
from .schema import SCH_LOCN_STATUS, convert_keys_to_snake_case
from .schema.const import (
    S2_COUNTRY,
    S2_GATEWAY_ID,
    S2_GATEWAYS,
    S2_LOCATION_ID,
    S2_LOCATION_INFO,
    S2_LOCATION_OWNER,
    S2_LOCATION_TYPE,
    S2_NAME,
    S2_TIME_ZONE,
    S2_USE_DAYLIGHT_SAVE_SWITCHING,
    EntityType,
    LocationType,
)
from .zone import EntityBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import _EvohomeClientNew as EvohomeClientNew
    from .schema import _EvoDictT


class Location(EntityBase):
    """Instance of an account's location."""

    STATUS_SCHEMA: Final[vol.Schema] = SCH_LOCN_STATUS
    TYPE: Final = EntityType.LOC  # type: ignore[misc]

    def __init__(self, client: EvohomeClientNew, config: _EvoDictT) -> None:
        super().__init__(
            config[S2_LOCATION_INFO][S2_LOCATION_ID],
            client.auth,
            client._logger,
        )

        self.client = client  # proxy for parent

        self._config: Final[_EvoDictT] = config[S2_LOCATION_INFO]
        self._status: _EvoDictT = {}

        # children
        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}  # gwy by id

        gwy_config: _EvoDictT
        for gwy_config in config[S2_GATEWAYS]:
            gwy = Gateway(self, gwy_config)

            self.gateways.append(gwy)
            self.gateway_by_id[gwy.id] = gwy

    @property
    def country(self) -> str:
        # "Belgium"
        # "CzechRepublic"
        # "Netherlands"
        # "UnitedKingdom"

        ret: str = self._config[S2_COUNTRY]
        return ret

    @property
    def location_owner(self) -> _EvoDictT:
        """
        "locationOwner": {
            "userId": "1234567",
            "username": "username@email.com",
            "firstname": "John",
            "lastname": "Smith"
        }
        """

        ret: _EvoDictT = self._config[S2_LOCATION_OWNER]
        return convert_keys_to_snake_case(ret)

    @property
    def location_type(self) -> LocationType:
        ret: LocationType = self._config[S2_LOCATION_TYPE]
        return ret

    @property
    def name(self) -> str:
        ret: str = self._config[S2_NAME]
        return ret

    @property
    def time_zone(self) -> _EvoDictT:
        """
        "timeZone": {
            "timeZoneId": "GMTStandardTime",
            "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
            "offsetMinutes": 0,
            "currentOffsetMinutes": 60,
            "supportsDaylightSaving": true
        }
        """

        # "GMTStandardTime":           "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
        # "CentralEuropeStandardTime": "(UTC+01:00) Praha, Bratislava, Budapešť, Bělehrad, Lublaň",
        # "RomanceStandardTime":       "(UTC+01:00) Brussels, Copenhagen, Madrid, Paris",
        # "WEuropeStandardTime":       "(UTC+01:00) Amsterdam, Berlijn, Bern, Rome, Stockholm, Wenen",
        # "FLEStandardTime":           "(UTC+02:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius",
        # "AUSEasternStandardTime":    "(UTC+10:00) Canberra, Melbourne, Sydney",

        ret: _EvoDictT = self._config[S2_TIME_ZONE]
        return convert_keys_to_snake_case(ret)

    @property
    def use_daylight_save_switching(self) -> bool:
        ret: bool = self._config[S2_USE_DAYLIGHT_SAVE_SWITCHING]
        return ret

    async def update(self) -> None:
        """Get the latest state of the location and update its status.

        Will also update the status of its gateways, their TCSs, and their DHW/zones.

        Returns the raw JSON of the latest state.
        """

        status: _EvoDictT = await self._broker.get(
            f"{self.TYPE}/{self.id}/status?includeTemperatureControlSystems=True",
            schema=self.STATUS_SCHEMA,
        )  # type: ignore[assignment]

        self._update_status(status)

    def _update_status(self, status: _EvoDictT) -> None:
        # No ActiveFaults in location node of status

        self._status = status

        for gwy_status in self._status[S2_GATEWAYS]:
            if gwy := self.gateway_by_id.get(gwy_status[S2_GATEWAY_ID]):
                gwy._update_status(gwy_status)

            else:
                self._logger.warning(
                    f"{self}: gateway_id='{gwy_status[S2_GATEWAY_ID]} not known"
                    ", (has the location configuration changed?)"
                )
