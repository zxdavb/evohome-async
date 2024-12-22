"""Provides handling of TCC v2 locations."""

from __future__ import annotations

import logging
from datetime import datetime as dt, timedelta as td, tzinfo
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from evohome.helpers import camel_to_snake
from evohome.windows_zones import (
    WINDOWS_TO_IANA_APAC,
    WINDOWS_TO_IANA_ASIA,
    WINDOWS_TO_IANA_EMEA,
)

from .const import (
    SZ_COUNTRY,
    SZ_CURRENT_OFFSET_MINUTES,
    SZ_GATEWAY_ID,
    SZ_GATEWAYS,
    SZ_LOCATION_ID,
    SZ_LOCATION_INFO,
    SZ_NAME,
    SZ_OFFSET_MINUTES,
    SZ_TIME_ZONE,
    SZ_USE_DAYLIGHT_SAVE_SWITCHING,
)
from .gateway import Gateway
from .schemas import factory_loc_status
from .schemas.const import EntityType
from .zone import EntityBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import _EvohomeClientNew as EvohomeClient
    from .schemas.typedefs import (
        EvoLocConfigEntryT,
        EvoLocConfigResponseT,
        EvoLocStatusResponseT,
        EvoTimeZoneInfoT,
    )


_LOGGER = logging.getLogger(__name__.rpartition(".")[0])


# TCC seen in EMEA and APAC (not Americas)
WINDOWS_TO_IANA = {
    k.replace(" ", "").replace(".", ""): v
    for k, v in (
        WINDOWS_TO_IANA_EMEA | WINDOWS_TO_IANA_ASIA | WINDOWS_TO_IANA_APAC
    ).items()
}


class Location(EntityBase):
    """Instance of an account's location."""

    SCH_STATUS: vol.Schema = factory_loc_status(camel_to_snake)
    _TYPE = EntityType.LOC

    def __init__(self, client: EvohomeClient, config: EvoLocConfigResponseT) -> None:
        super().__init__(
            config[SZ_LOCATION_INFO][SZ_LOCATION_ID],
            client.auth,
            client.logger,
        )

        self.client = client  # proxy for parent
        #

        self._config: EvoLocConfigEntryT = config[SZ_LOCATION_INFO]
        self._status: EvoLocStatusResponseT | None = None

        self._tzinfo = _create_tzinfo(self.time_zone_info, dst_enabled=self.dst_enabled)

        # children
        self.gateways: list[Gateway] = []
        self.gateway_by_id: dict[str, Gateway] = {}  # gwy by id

        for gwy_entry in config[SZ_GATEWAYS]:
            gwy = Gateway(self, gwy_entry)

            self.gateways.append(gwy)
            self.gateway_by_id[gwy.id] = gwy

    @property  # TODO: deprecate in favour of .id attr
    def locationId(self) -> str:  # noqa: N802
        return self._id

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
    def dst_enabled(self) -> bool:
        """Return True if the location uses daylight saving time.

        Not the same as the location's TZ supporting DST, nor the current DST status.
        """
        return self._config[SZ_USE_DAYLIGHT_SAVE_SWITCHING]

    @property
    def tzinfo(self) -> tzinfo:
        """Return a tzinfo-compliant object for this Location."""
        return self._tzinfo

    def now(self) -> dt:  # always returns a TZ-aware dtm
        """Return the current local time as a aware datetime in this location's TZ."""
        return dt.now(self.client.tzinfo).astimezone(self.tzinfo)

    async def update(
        self, *, _update_time_zone_info: bool = False
    ) -> EvoLocStatusResponseT:
        """Get the latest state of the location and update its status.

        Will also update the status of its gateways, their TCSs, and their DHW/zones.

        Returns the raw JSON of the latest state.
        """

        if _update_time_zone_info:
            await self._update_config()

        status: EvoLocStatusResponseT = await self._auth.get(
            f"{self._TYPE}/{self.id}/status?includeTemperatureControlSystems=True",
            schema=self.SCH_STATUS,
        )  # type: ignore[assignment]

        self._update_status(status)
        return status

    async def _update_config(self) -> None:
        """Usually called when DST starts/stops or the location's DST config changes."""

        # it is assumed that only the location's TZ/DST info can change
        # so no ?includeTemperatureControlSystems=True

        config: EvoLocConfigResponseT = await self._auth.get(
            f"location/{self._id}/installationInfo"  # TODO: add schema
        )  # type: ignore[assignment]

        self._config = config[SZ_LOCATION_INFO]

        # new TzInfo object, or update the existing one?
        self._tzinfo = _create_tzinfo(self.time_zone_info, dst_enabled=self.dst_enabled)
        # lf._tzinfo._update(time_zone_info=time_zone_info, use_dst_switching=use_dst_switching)

    def _update_status(self, status: EvoLocStatusResponseT) -> None:
        """Update the location's latest status (and its gateways and their TCSs)."""
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


def _create_tzinfo(time_zone_info: EvoTimeZoneInfoT, /, *, dst_enabled: bool) -> tzinfo:
    """Create a tzinfo object based on the time zone information."""

    time_zone_id = time_zone_info["time_zone_id"]

    try:
        return ZoneInfo(WINDOWS_TO_IANA[time_zone_id])
    except (KeyError, ModuleNotFoundError):
        pass

    if dst_enabled:
        _LOGGER.warning(
            "Unable to find IANA TZ for '%s'; DST transitions will not be automatic",
            time_zone_id,
        )
    return EvoZoneInfo(time_zone_info=time_zone_info, use_dst_switching=dst_enabled)


# it is ostensibly optional to provide this data to our TzInfo object
_DEFAULT_TIME_ZONE_INFO: EvoTimeZoneInfoT = {
    "time_zone_id": "GMTStandardTime",
    "display_name": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
    "offset_minutes": 0,
    "current_offset_minutes": 0,
    "supports_daylight_saving": True,
}
_DEFAULT_USE_DST_SWITCHING = False


class EvoZoneInfo(tzinfo):
    """Return a tzinfo object based on a TCC location's time zone information.

    The location does not know its IANA time zone, only its offsets, so:
    - this tzinfo object must be informed when the DST has started/stopped
    - the `tzname` name is based upon the Windows scheme
    """

    # example time_zone_id: display_name key-value pairs:
    # "GMTStandardTime":           "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
    # "CentralEuropeStandardTime": "(UTC+01:00) Praha, Bratislava, Budapešť, Bělehrad, Lublaň",
    # "RomanceStandardTime":       "(UTC+01:00) Brussels, Copenhagen, Madrid, Paris",
    # "WEuropeStandardTime":       "(UTC+01:00) Amsterdam, Berlijn, Bern, Rome, Stockholm, Wenen",
    # "FLEStandardTime":           "(UTC+02:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius",
    # "AUSEasternStandardTime":    "(UTC+10:00) Canberra, Melbourne, Sydney",

    _time_zone_info: EvoTimeZoneInfoT
    _use_dst_switching: bool

    _utcoffset: td
    _dst: td

    # NOTE: from https://docs.python.org/3/library/datetime.html#datetime.tzinfo:
    # Special requirement for pickling: A tzinfo subclass must have an __init__()
    # method that can be called with no arguments, otherwise it can be pickled but
    # possibly not unpickled again. This is a technical requirement that may be
    # relaxed in the future.

    def __init__(  #
        self,
        *,
        time_zone_info: EvoTimeZoneInfoT | None,
        use_dst_switching: bool | None,
    ) -> None:
        """Initialise the class."""
        super().__init__()

        self._update(time_zone_info=time_zone_info, use_dst_switching=use_dst_switching)

    # loc.tzinfo.utcoffset(dt | None)
    # loc.tzinfo.dst(dt | None)
    # loc.tzinfo.tzname(dt | None)
    # loc.tzinfo.fromutc(loc.now())
    # loc.now().astimezone(loc.tzinfo | None)

    def __repr__(self) -> str:
        return "{}({!r}, '{}', is_dst={})".format(
            self.__class__.__name__,
            self._utcoffset,
            self._time_zone_info["time_zone_id"],
            bool(self._dst),
        )

    def _update(
        self,
        *,
        time_zone_info: EvoTimeZoneInfoT | None = _DEFAULT_TIME_ZONE_INFO,
        use_dst_switching: bool | None = _DEFAULT_USE_DST_SWITCHING,
    ) -> None:
        """Update the TZ information and DST configuration.

        This is not a standard method for tzinfo objects, but a custom one for this
        class.

        So that so that the this object can correctly maintain its `utcoffset` and
        `dst` attrs, this method should be called (on instantiation and):
        - when the time zone enters or leaves DST
        - when the location starts or stops using DST
        """

        if time_zone_info is None:
            time_zone_info = _DEFAULT_TIME_ZONE_INFO

        if use_dst_switching is None:
            use_dst_switching = _DEFAULT_USE_DST_SWITCHING

        self._time_zone_info = time_zone_info
        self._use_dst_switching = use_dst_switching

        self._utcoffset = td(minutes=time_zone_info[SZ_CURRENT_OFFSET_MINUTES])
        self._dst = self._utcoffset - td(minutes=time_zone_info[SZ_OFFSET_MINUTES])

        self._tzname = time_zone_info["time_zone_id"] + (
            " (DST)" if self._dst else " (STD)"
        )

    def dst(self, dtm: dt | None) -> td:
        """Return the daylight saving time adjustment, as a timedelta object.

        Return 0 if DST not in effect. utcoffset() must include the DST offset.
        """

        return self._dst

    def tzname(self, dtm: dt | None) -> str:
        "datetime -> string name of time zone."
        return self._tzname

    def utcoffset(self, dtm: dt | None) -> td:
        """Return offset of local time from UTC, as a timedelta object.

        The timedelta is positive east of UTC. If local time is west of UTC, this
        should be negative.
        """

        return self._utcoffset
