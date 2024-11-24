#!/usr/bin/env python3
"""Provides handling of TCC v2 locations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from evohome.helpers import camel_to_snake

from .const import (
    SZ_COUNTRY,
    SZ_GATEWAY_ID,
    SZ_GATEWAYS,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_LOCATION_OWNER,
    SZ_NAME,
    SZ_TIME_ZONE,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
)
from .gateway import Gateway
from .schemas import factory_loc_status
from .schemas.const import EntityType
from .zone import EntityBase

if TYPE_CHECKING:
    from . import _EvohomeClientNew as EvohomeClient
    from .schemas import _EvoDictT
    from .schemas.typedefs import (
        EvoGwyEntryT,
        EvoLocationOwnerInfoT,
        EvoLocConfigT,
        EvoLocEntryT,
        EvoTimeZoneInfoT,
    )


class Location(EntityBase):
    """Instance of an account's location."""

    STATUS_SCHEMA: Final = factory_loc_status(camel_to_snake)
    _TYPE: Final = EntityType.LOC  # type: ignore[misc]

    def __init__(self, client: EvohomeClient, config: EvoLocEntryT) -> None:
        super().__init__(
            config[SZ_LOCATION_INFO][SZ_LOCATION_ID],
            client.auth,
            client._logger,
        )

        self.client = client  # proxy for parent
        #

        self._config: Final[EvoLocConfigT] = config[SZ_LOCATION_INFO]  # type: ignore[assignment,misc]
        self._status: _EvoDictT = {}

        # children
        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}  # gwy by id

        gwy_entry: EvoGwyEntryT
        for gwy_entry in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_entry)

            self.gateways.append(gwy)
            self.gateway_by_id[gwy.id] = gwy

    @property
    def country(self) -> str:
        # "Belgium"
        # "CzechRepublic"
        # "Netherlands"
        # "UnitedKingdom"

        return self._config[SZ_COUNTRY]

    @property
    def name(self) -> str:
        return self._config[SZ_NAME]

    @property
    def owner(self) -> EvoLocationOwnerInfoT:
        """
        "locationOwner": {
            "userId": "1234567",
            "username": "username@email.com",
            "firstname": "John",
            "lastname": "Smith"
        }
        """

        return self._config[SZ_LOCATION_OWNER]

    @property
    def time_zone(self) -> EvoTimeZoneInfoT:
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

        return self._config[SZ_TIME_ZONE]

    @property
    def use_daylight_save_switching(self) -> bool:
        return self._config[SZ_USE_DAYLIGHT_SAVE_SWITCHING]

    async def update(self) -> _EvoDictT:
        """Get the latest state of the location and update its status.

        Will also update the status of its gateways, their TCSs, and their DHW/zones.

        Returns the raw JSON of the latest state.
        """

        status: _EvoDictT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status?includeTemperatureControlSystems=True",
            schema=self.STATUS_SCHEMA,
        )  # type: ignore[assignment]

        self._update_status(status)

        return status

    def _update_status(self, status: _EvoDictT) -> None:
        # No ActiveFaults in location node of status

        self._status = status

        for gwy_status in self._status[SZ_GATEWAYS]:
            if gwy := self.gateway_by_id.get(gwy_status[SZ_GATEWAY_ID]):
                gwy._update_status(gwy_status)

            else:
                self._logger.warning(
                    f"{self}: gateway_id='{gwy_status[SZ_GATEWAY_ID]} not known"
                    ", (has the location configuration changed?)"
                )
