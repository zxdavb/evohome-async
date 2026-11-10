"""The faked vendor server (v1 and v2 APIs)."""

from __future__ import annotations

import functools
import re
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, TypeVar

import probatio as vol

from evohomeasync2.schemas import const as sch
from evohomeasync2.schemas.schedule import TCC_GET_DHW_SCHEDULE, TCC_GET_ZON_SCHEDULE

from .const import (
    GHOST_ZONE_ID,
    MOCK_CRED_RESPONSE,
    MOCK_FULL_CONFIG,
    MOCK_LOCN_STATUS,
    MOCK_SCHEDULE_DHW,
    MOCK_SCHEDULE_ZONE,
    URL_BASE_V2 as URL_BASE,
    URL_CRED_V2 as URL_CRED,
    user_config_from_full_config as _user_config_from_full_config,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .const import _bodyT, _methodT, _statusT, _urlT


def _dhw_id(url: _urlT) -> str:
    """Extract a DHW id from a URL."""
    return url.split(f"{sch.S2_DOMESTIC_HOT_WATER}/")[1].split("/")[0]


def _loc_id(url: _urlT) -> str:
    """Extract a Location id from a URL."""
    return url.split(f"{sch.S2_LOCATION}/")[1].split("/")[0]


def _tcs_id(url: _urlT) -> str:
    """Extract a TCS id from a URL."""
    return url.split(f"{sch.S2_TEMPERATURE_CONTROL_SYSTEM}/")[1].split("/")[0]


def _usr_id(url: _urlT) -> str:
    """Extract a User id from a URL."""
    return url.split("?userId=")[1].split("&")[0]


def _zon_id(url: _urlT) -> str:
    """Extract a Zone id from a URL."""
    return url.split(f"{sch.S2_TEMPERATURE_ZONE}/")[1].split("/")[0]


S = TypeVar("S", bound="FakedServerBase")


def _failure(code: sch.TccFailureCode, message: str) -> list[dict[str, str]]:
    """Return the vendor's response to a failed GET/PUT (a list of code/message)."""
    return [{sch.S2_CODE: code, sch.S2_MESSAGE: message}]


# the vendor's response to any request for an id that is not the user's (whether or not
# it exists, e.g. a deleted zone): it is the same for every URL, GET or PUT
_UNAUTHORIZED: Final = _failure(
    sch.TccFailureCode.UNAUTHORIZED, "You are not allowed to perform this action."
)


def validate_id_of_url(
    id_fnc: Callable[[_urlT], str],
) -> Callable[[Callable[[S], _bodyT | None]], Callable[[S], _bodyT]]:
    """Validate the id in the URL and set the status accordingly."""

    def decorator(
        fnc: Callable[[S], _bodyT | None],
    ) -> Callable[[S], _bodyT]:
        @functools.wraps(fnc)
        def wrapper(svr: S) -> _bodyT:
            if svr._method != HTTPMethod.GET:
                svr.status = HTTPStatus.METHOD_NOT_ALLOWED
                return {"message": "Method not allowed"}

            assert svr._url  # mypy
            try:
                id_: str = id_fnc(svr._url)
            except IndexError:
                svr.status = HTTPStatus.NOT_FOUND
                return {"message": "Not Found"}

            if not id_.isdigit():
                svr.status = HTTPStatus.BAD_REQUEST
                return [{"message": "Bad request"}]

            if result := fnc(svr):
                return result

            svr.status = HTTPStatus.UNAUTHORIZED
            return _UNAUTHORIZED

        return wrapper

    return decorator


class FakedServerBase:
    """Mocked vendor server for provision via a hacked aiohttp."""

    def __init__(
        self,
        full_config: dict,
        locn_status: dict,
        /,
        *,
        zone_schedule: dict | None = None,
        dhw_schedule: dict | None = None,
    ) -> None:
        self._full_config = full_config or MOCK_FULL_CONFIG
        self._locn_status = locn_status or MOCK_LOCN_STATUS
        self._zon_schedule = zone_schedule or MOCK_SCHEDULE_ZONE
        self._dhw_schedule = dhw_schedule or MOCK_SCHEDULE_DHW

        self._schedules: dict[str, dict] = {}
        self._user_config: dict[str, Any] = {}

        self.body: _bodyT | None = None
        self._method: _methodT | None = None
        self.status: _statusT | None = None
        self._url: _urlT | None = None

    def request(
        self, method: _methodT, url: _urlT, data: dict | str | None = None
    ) -> _bodyT:
        self._method = method
        self._url = url
        self._data = data

        self.body, self.status = None, None
        for pattern, fnc in REQUEST_MAP.items():
            if re.search(pattern, url):
                self.body = fnc(self)
                break
            # self.status = HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            self.status = HTTPStatus.NOT_FOUND
            return """
                <html>
                    <head><title>Error</title></head>
                    <body><h1>Not Found</h1></body>
                </html>
            """

        if not self.status:
            self.status = HTTPStatus.OK if self.body else HTTPStatus.NOT_FOUND

        assert self.body is not None  # mypy
        return self.body


class FakedServerV1(FakedServerBase):
    """Mocked vendor server for provision of v1 URL responses."""

    def v1_session(self) -> _bodyT | None:
        raise NotImplementedError

    def v1_account_info(self) -> _bodyT | None:
        raise NotImplementedError

    def v1_locations(self) -> _bodyT | None:
        raise NotImplementedError

    def v1_evo_touch_systems(self) -> _bodyT | None:
        raise NotImplementedError

    def v1_heat_setpoint(self) -> _bodyT | None:
        raise NotImplementedError

    def v1_changeable_values(self) -> _bodyT | None:
        raise NotImplementedError


class FakedServerV2(FakedServerBase):
    """Mocked vendor server for provision of v2 URL responses."""

    def __init__(
        self,
        full_config: dict,
        locn_status: dict,
        /,
        *,
        zone_schedule: dict | None = None,
        dhw_schedule: dict | None = None,
    ) -> None:
        super().__init__(
            full_config,
            locn_status,
            zone_schedule=zone_schedule,
            dhw_schedule=dhw_schedule,
        )
        self._user_config = self._user_config_from_full_config(self._full_config)  # type: ignore[arg-type]

    def _ids(self) -> dict[str, set[str]]:
        """Return the ids of the user's entities, by their id key (from the status)."""

        keys = (
            sch.S2_LOCATION_ID,
            sch.S2_GATEWAY_ID,
            sch.S2_SYSTEM_ID,
            sch.S2_ZONE_ID,
            sch.S2_DHW_ID,
        )
        ids: dict[str, set[str]] = {key: set() for key in keys}

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ids and isinstance(value, str):
                        ids[key].add(value)
                    else:
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(self._locn_status)
        return ids

    def _is_users_id(self, id_: str) -> bool:
        """Return True if the id is of any of the user's entities."""
        return any(id_ in ids for ids in self._ids().values())

    def _schedule_error(
        self, id_: str, valid_ids: set[str], failure: list[dict[str, str]]
    ) -> _bodyT | None:
        """Return the vendor's error (if any) for the id of a schedule's URL.

        An id that is not the user's is a 401 (a GET or PUT); a GET with an id that is
        the user's, but not a valid one (e.g. of another type), is a 400 (the failure).
        """

        if not self._is_users_id(id_):
            self.status = HTTPStatus.UNAUTHORIZED
            return _UNAUTHORIZED

        if self._method == HTTPMethod.GET and id_ not in valid_ids:
            self.status = HTTPStatus.BAD_REQUEST
            return failure
        return None

    def oauth_token(self) -> _bodyT | None:
        if self._method != HTTPMethod.POST:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif self._url == URL_CRED:
            return MOCK_CRED_RESPONSE
        return None

    def usr_account(self) -> _bodyT:
        if self._method != HTTPMethod.GET:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        if self._url == f"{URL_BASE}/userAccount":
            return self._user_config

        self.status = HTTPStatus.NOT_FOUND
        return {"message": "Not found"}

    @validate_id_of_url(_usr_id)
    def all_config(self) -> _bodyT | None:  # full_locn
        usr_id = _usr_id(self._url)  # type: ignore[arg-type]

        if self._user_config[sch.S2_USER_ID] == usr_id:
            return self._full_config
        return None

    def loc_config(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_loc_id)
    def loc_status(self) -> _bodyT | None:
        loc_id = _loc_id(self._url)  # type: ignore[arg-type]

        if self._locn_status[sch.S2_LOCATION_ID] == loc_id:
            return self._locn_status
        return None

    def tcs_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_tcs_id)
    def tcs_status(self) -> _bodyT | None:
        tcs_id = _tcs_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[sch.S2_GATEWAYS]:
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:  # type: ignore[index]
                if tcs[sch.S2_SYSTEM_ID] == tcs_id:
                    return tcs  # type: ignore[no-any-return]
        return None

    def zon_schedule(self) -> _bodyT | None:
        zon_id = _zon_id(self._url)  # type: ignore[arg-type]

        not_found = _failure(
            sch.TccFailureCode.SCHEDULE_NOT_FOUND, "Schedule not found."
        )
        # a ghost zone is a zone, but has no schedule (so is as if not a zone's id)
        valid_ids = self._ids()[sch.S2_ZONE_ID] - {GHOST_ZONE_ID}
        if err := self._schedule_error(zon_id, valid_ids, not_found):
            return err  # e.g. a TCS's id (or an id that is not the user's)

        if self._method == HTTPMethod.GET:
            return self._schedules.get(zon_id, self._zon_schedule)

        if self._method != HTTPMethod.PUT:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        if not isinstance(self._data, dict):
            self.status = HTTPStatus.BAD_REQUEST
            return [{"message": "Bad Request (invalid schedule: not a dict)"}]

        try:
            TCC_GET_ZON_SCHEDULE(self._data)
        except vol.Invalid:
            self.status = HTTPStatus.BAD_REQUEST
            return {"message": "Bad Request (invalid schedule: invalid schema)"}

        self._schedules[zon_id] = self._data
        return {"id": "1234567890"}

    def zon_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_zon_id)
    def zon_status(self) -> _bodyT | None:
        zon_id = _zon_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[sch.S2_GATEWAYS]:
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:  # type: ignore[index]
                for zone in tcs[sch.S2_ZONES]:
                    if zone[sch.S2_ZONE_ID] == zon_id:
                        return zone  # type: ignore[no-any-return]

        if self._is_users_id(zon_id):  # e.g. a TCS's id
            self.status = HTTPStatus.BAD_REQUEST
            return _failure(
                sch.TccFailureCode.TEMPERATURE_ZONE_NOT_FOUND,
                f"Temperature Zone {zon_id} not found.",
            )
        return None

    def dhw_schedule(self) -> _bodyT | None:
        dhw_id = _dhw_id(self._url)  # type: ignore[arg-type]

        not_found = _failure(
            sch.TccFailureCode.DHW_NOT_FOUND, f"Domestic Hot Water {dhw_id} not found."
        )
        if err := self._schedule_error(dhw_id, self._ids()[sch.S2_DHW_ID], not_found):
            return err  # e.g. a zone's id (or an id that is not the user's)

        if self._method == HTTPMethod.GET:
            return self._schedules.get(dhw_id, self._dhw_schedule)

        if self._method != HTTPMethod.PUT:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        if not isinstance(self._data, dict):
            self.status = HTTPStatus.BAD_REQUEST
            return [{"message": "Bad Request (invalid schedule: not a dict)"}]

        try:
            TCC_GET_DHW_SCHEDULE(self._data)
        except vol.Invalid:
            self.status = HTTPStatus.BAD_REQUEST
            return {"message": "Bad Request (invalid schedule: invalid schema)"}

        self._schedules[dhw_id] = self._data
        return {"id": "1234567890"}

    @validate_id_of_url(_dhw_id)
    def dhw_status(self) -> _bodyT | None:
        dhw_id = _dhw_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[sch.S2_GATEWAYS]:
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:  # type: ignore[index]
                if (dhw := tcs.get(sch.S2_DHW)) and dhw[sch.S2_DHW_ID] == dhw_id:
                    return dhw  # type: ignore[no-any-return]

        if self._is_users_id(dhw_id):  # e.g. a zone's id
            self.status = HTTPStatus.BAD_REQUEST
            return _failure(
                sch.TccFailureCode.DHW_NOT_FOUND,
                f"Domestic Hot Water {dhw_id} not found.",
            )
        return None

    def dhw_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @staticmethod
    def _user_config_from_full_config(full_config: list) -> dict:
        """Create a valid MOCK_USER_CONFIG from a MOCK_FULL_CONFIG."""
        return _user_config_from_full_config(full_config)


class FakedServer(FakedServerV2, FakedServerV1):
    """Mocked vendor server for provision via a hacked aiohttp."""


REQUEST_MAP_V1: dict[str, Callable] = {
    #
    r"/session": FakedServer.v1_session,  # authentication
    #
    r"/accountInfo$": FakedServer.v1_account_info,
    #
    r"/locations?userId=": FakedServer.v1_locations,
    #
    r"/evoTouchSystems?locationId=": FakedServer.v1_evo_touch_systems,
    #
    r"/devices/.*/thermostat/changeableValues/heatSetpoint": FakedServer.v1_heat_setpoint,
    r"/devices/.*/thermostat/changeableValues": FakedServer.v1_changeable_values,
}
REQUEST_MAP_V2: dict[str, Callable] = {
    #
    r"/Auth/OAuth/Token": FakedServer.oauth_token,  # authentication
    #
    r"/userAccount$": FakedServer.usr_account,
    #
    r"/location/installationInfo": FakedServer.all_config,
    r"/location/.*/installationInfo": FakedServer.loc_config,
    r"/location/.*/status": FakedServer.loc_status,
    #
    r"/temperatureControlSystem/.*/mode": FakedServer.tcs_mode,
    r"/temperatureControlSystem/.*/status": FakedServer.tcs_status,
    #
    r"/temperatureZone/.*/status": FakedServer.zon_status,
    r"/temperatureZone/.*/heatSetpoint": FakedServer.zon_mode,
    r"/temperatureZone/.*/schedule": FakedServer.zon_schedule,
    #
    r"/domesticHotWater/.*/status": FakedServer.dhw_status,
    r"/domesticHotWater/.*/state": FakedServer.dhw_mode,
    r"/domesticHotWater/.*/schedule": FakedServer.dhw_schedule,
}
REQUEST_MAP = REQUEST_MAP_V1 | REQUEST_MAP_V2
