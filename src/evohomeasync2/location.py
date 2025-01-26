"""Provides handling of TCC v2 locations.

The entity hierarchy is: Location -> Gateway -> TCS -> DHW | Zone.
"""

from __future__ import annotations

import logging
from datetime import datetime as dt, tzinfo
from typing import TYPE_CHECKING

from aiozoneinfo import async_get_time_zone

from evohome.helpers import camel_to_snake, convert_naive_dtm_strs_to_aware
from evohome.time_zone import EvoZoneInfo, iana_tz_from_windows_tz

from .const import (
    SZ_COUNTRY,
    SZ_GATEWAY_ID,
    SZ_GATEWAYS,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_NAME,
    SZ_TIME_ZONE,
    SZ_TIME_ZONE_ID,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
)
from .gateway import Gateway
from .schemas import factory_loc_status
from .schemas.const import EntityType
from .schemas.typedefs import EvoTimeZoneInfoT
from .zone import EntityBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import EvohomeClient
    from .schemas.typedefs import (
        EvoLocConfigEntryT,
        EvoLocConfigResponseT,
        EvoLocStatusResponseT,
        EvoTimeZoneInfoT,
    )


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


async def _create_tzinfo(
    time_zone_info: EvoTimeZoneInfoT, /, *, use_dst_switching: bool | None = False
) -> tzinfo:  # EvoZoneInfo | ZoneInfo:
    """Return a ZoneInfo object based on the time zone information.

    Note that `dst_enabled` (DST will be active at some times) is distinct from
    `dst_active` (DST is active now).
    """

    time_zone_id = time_zone_info[SZ_TIME_ZONE_ID]

    try:
        return await async_get_time_zone(iana_tz_from_windows_tz(time_zone_id))
    except (KeyError, ModuleNotFoundError):
        pass

    # DST support will be very limited, for example:
    # - unable to adjust current utcoffset when DST starts & stops
    # - unable to determine if a given datetime was/will be during DST

    msg = f"Unable to find IANA TZ identifier for '{time_zone_id}'"
    _LOGGER.warning(
        msg + "; DST support will be very limited" if use_dst_switching else ""
    )

    return EvoZoneInfo(
        time_zone_info=time_zone_info, use_dst_switching=use_dst_switching
    )


async def create_location(
    client: EvohomeClient,
    config: EvoLocConfigResponseT,
) -> Location:
    """Create a Location entity and return it.

    We use a constructor function to keep the async creation of a tzinfo object tightly
    coupled with the instantiation of its Location.
    """

    tzinfo = await _create_tzinfo(
        config[SZ_LOCATION_INFO][SZ_TIME_ZONE],
        use_dst_switching=config[SZ_LOCATION_INFO][SZ_USE_DAYLIGHT_SAVE_SWITCHING],
    )

    loc = Location(client, config, tzinfo=tzinfo)

    _LOGGER.debug(f"Instantiated {loc}")

    return loc


class Location(EntityBase):
    """Instance of an account's location."""

    SCH_STATUS: vol.Schema = factory_loc_status(camel_to_snake)
    _TYPE = EntityType.LOC

    def __init__(
        self,
        client: EvohomeClient,
        config: EvoLocConfigResponseT,
        /,
        *,
        tzinfo: tzinfo | None = None,
    ) -> None:
        super().__init__(
            config[SZ_LOCATION_INFO][SZ_LOCATION_ID],
            client.auth,
            client.logger,
        )

        self.client = client  # proxy for parent
        #

        self._config: EvoLocConfigEntryT = config[SZ_LOCATION_INFO]
        self._status: EvoLocStatusResponseT | None = None

        self._tzinfo = tzinfo or EvoZoneInfo(
            time_zone_info=self.time_zone_info,
            use_dst_switching=self.dst_enabled,
        )

        # children
        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}  # gwy by id

        for gwy_entry in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_entry)

            self.gateways.append(gwy)
            self.gateway_by_id[gwy.id] = gwy

    def __str__(self) -> str:
        """Return a string representation of the entity."""
        return f"{self.__class__.__name__}(id='{self._id}', tzinfo='{self.tzinfo}')"

    # Config attrs...

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

    async def _get_config(self) -> EvoLocConfigResponseT:
        """Get the latest state of the gateway and update its status attr.

        Usually called when DST starts/stops or the location's DST config changes (i.e.
        there is no _update_config() method). Returns the raw JSON of the latest config.
        """

        # it is assumed that only the location's TZ/DST info can change
        # so no ?includeTemperatureControlSystems=True

        config: EvoLocConfigResponseT = await self._auth.get(
            f"location/{self._id}/installationInfo"  # TODO: add schema
        )  # type: ignore[assignment]

        self._config = config[SZ_LOCATION_INFO]

        # new TzInfo object, or update the existing one?
        self._tzinfo = await _create_tzinfo(
            self.time_zone_info, use_dst_switching=self.dst_enabled
        )
        # lf._tzinfo._update(time_zone_info=time_zone_info, use_dst_switching=use_dst_switching)

        return config

    @property
    def dst_enabled(self) -> bool:
        """Return True if the location uses daylight saving time.

        Not the same as the location's TZ supporting DST, nor the current DST status.
        """
        return self._config[SZ_USE_DAYLIGHT_SAVE_SWITCHING]

    @property  # NOTE: renamed config key: was time_zone
    def time_zone_info(self) -> EvoTimeZoneInfoT:
        """Return the time zone information for the location.

        The time zone id is not IANA-compliant, but is based upon the Windows scheme.
        """

        """
            "timeZone": {
                "timeZoneId": "GMTStandardTime",
                "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
                "offsetMinutes": 0,
                "currentOffsetMinutes": 60,
                "supportsDaylightSaving": true
            }
        """

        return self._config[SZ_TIME_ZONE]

    @property
    def tzinfo(self) -> tzinfo:
        """Return a tzinfo-compliant object for this Location."""
        return self._tzinfo

    def now(self) -> dt:  # always returns a TZ-aware dtm
        """Return the current local time as an aware datetime in this location's TZ."""
        return dt.now(self.client._tzinfo).astimezone(self.tzinfo)

    # Status (state) attrs & methods...

    async def update(
        self, *, _update_time_zone_info: bool = False
    ) -> EvoLocStatusResponseT:
        """Get the latest state of the location and update its status attrs.

        Will also update the status of its gateways, their TCSs, and their DHW/zones.
        Returns the raw JSON of the latest state.
        """

        if _update_time_zone_info:
            await self._get_config()

        status = await self._get_status()

        self._update_status(status)
        return status

    async def _get_status(self) -> EvoLocStatusResponseT:
        """Get the latest state of the location and update its status attr.

        Returns the raw JSON of the latest state.
        """

        status: EvoLocStatusResponseT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status?includeTemperatureControlSystems=True",
            schema=self.SCH_STATUS,
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    def _update_status(self, status: EvoLocStatusResponseT) -> None:
        """Update the LOC's status and cascade to its descendants."""

        # convert all naive datetimes to TZ-aware datetimes (do when snake_casing?)
        status = convert_naive_dtm_strs_to_aware(status, self.tzinfo)

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
