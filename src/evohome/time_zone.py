"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

from datetime import datetime as dt, timedelta as td, tzinfo
from typing import TYPE_CHECKING, Final

from .windows_zones import WINDOWS_TO_IANA_LOOKUP

if TYPE_CHECKING:
    from evohomeasync2.schemas.typedefs import EvoTimeZoneInfoT

SZ_CURRENT_OFFSET_MINUTES: Final = "current_offset_minutes"
SZ_OFFSET_MINUTES: Final = "offset_minutes"
SZ_TIME_ZONE_ID: Final = "time_zone_id"


def iana_tz_from_windows_tz(time_zone: str) -> str:
    """Return the IANA TZ identifier from the Windows TZ id."""
    return WINDOWS_TO_IANA_LOOKUP[time_zone.replace(" ", "").replace(".", "")]


# it is ostensibly optional to provide this data to the EvoZoneInfo class
_DEFAULT_TIME_ZONE_INFO: EvoTimeZoneInfoT = {
    SZ_TIME_ZONE_ID: "GMTStandardTime",
    "display_name": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
    SZ_OFFSET_MINUTES: 0,
    SZ_CURRENT_OFFSET_MINUTES: 0,
    "supports_daylight_saving": False,
}


# Currently used only by the newer API (minor changes needed for older API)...
class EvoZoneInfo(tzinfo):
    """Return a tzinfo object based on a TCC location's time zone information.

    The location does not know its IANA time zone, only its offsets, so:
    - this tzinfo object must be informed when the DST has started/stopped
    - the `tzname` name is based upon the Windows scheme
    """

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
        time_zone_info: EvoTimeZoneInfoT | None = _DEFAULT_TIME_ZONE_INFO,
        use_dst_switching: bool | None = False,
    ) -> None:
        """Initialise the class."""
        super().__init__()

        if time_zone_info is None:
            time_zone_info = _DEFAULT_TIME_ZONE_INFO

        self._update(
            time_zone_info=time_zone_info, use_dst_switching=bool(use_dst_switching)
        )

    # tzinfo.utcoffset(dt | None)
    # tzinfo.dst(dt | None)
    # tzinfo.tzname(dt | None)
    # tzinfo.fromutc(now())
    # now().astimezone(tzinfo | None)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self._utcoffset!r}, "
            f"'{self._time_zone_info[SZ_TIME_ZONE_ID]}', is_dst={bool(self._dst)})"
        )

    def _update(
        self,
        *,
        time_zone_info: EvoTimeZoneInfoT | None = None,
        use_dst_switching: bool | None = None,
    ) -> None:
        """Update the TZ information and DST configuration.

        This is not a standard method for tzinfo objects, but a custom one for this
        class.

        So this object can correctly maintain its `utcoffset` and `dst` attrs, this
        method should be called (on instantiation and):
        - when the time zone enters or leaves DST
        - when the location starts or stops using DST switching (not expected)
        """

        if time_zone_info is not None:  # TZ shouldn't change, only the current offset
            self._time_zone_info = time_zone_info

            self._utcoffset = td(minutes=time_zone_info[SZ_CURRENT_OFFSET_MINUTES])
            self._dst = self._utcoffset - td(minutes=time_zone_info[SZ_OFFSET_MINUTES])

            self._tzname = time_zone_info[SZ_TIME_ZONE_ID] + (
                " (DST)" if self._dst else " (STD)"
            )

        if use_dst_switching is not None:
            self._use_dst_switching = use_dst_switching

        # if not self._use_dst_switching:
        #     assert self._dst == td(0), "DST is not enabled, but the offset is non-zero"

    def dst(self, dtm: dt | None) -> td:
        """Return the daylight saving time adjustment, as a timedelta object.

        Return 0 if DST not in effect. utcoffset() must include the DST offset.
        """

        if dtm and self._dst:  # we don't know when DST starts/stops
            raise NotImplementedError("DST transitions are not implemented")

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


### TZ data for v2 location (newer API)...

# _ = {
#     "locationInfo": {
#         "locationId": "2738909",
#         "useDaylightSaveSwitching": True,
#         "timeZone": {
#             "timeZoneId": "GMTStandardTime",
#             "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
#             "offsetMinutes": 0,
#             "currentOffsetMinutes": 60,
#             "supportsDaylightSaving": True
#         }
#     }
# }

# examples of known display_name: key-value pairs:
#   "GMTStandardTime":           "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
#   "CentralEuropeStandardTime": "(UTC+01:00) Praha, Bratislava, Budapešť, Bělehrad, Lublaň",
#   "RomanceStandardTime":       "(UTC+01:00) Brussels, Copenhagen, Madrid, Paris",
#   "WEuropeStandardTime":       "(UTC+01:00) Amsterdam, Berlijn, Bern, Rome, Stockholm, Wenen",
#   "FLEStandardTime":           "(UTC+02:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius",
#   "AUSEasternStandardTime":    "(UTC+10:00) Canberra, Melbourne, Sydney",


### TZ data for v1 location (older API)...

# _ = {
#     "locationID": 2738909,  # NOTE: is an integer
#     "daylightSavingTimeEnabled": True,  # NOTE: different key
#     "timeZone": {
#         "id": "GMT Standard Time",  # NOTE: different key, spaces in value
#         "displayName": "(UTC+00:00) Dublin, Edinburgh, Lisbon, London",
#         "offsetMinutes": 0,
#         "currentOffsetMinutes": 60,
#         "usingDaylightSavingTime": True  # NOTE: different key
#     }
# }
