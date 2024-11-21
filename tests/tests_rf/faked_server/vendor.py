#!/usr/bin/env python3
"""Mocked vendor server for provision via a hacked aiohttp."""

from __future__ import annotations

import functools
import re
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from evohomeasync2.schemas import (
    SCH_PUT_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_ZONE,
    const as sch,
    convert_to_get_schedule,
)

from .const import (
    GHOST_ZONE_ID,
    MOCK_AUTH_RESPONSE,
    MOCK_FULL_CONFIG,
    MOCK_LOCN_STATUS,
    MOCK_SCHEDULE_DHW,
    MOCK_SCHEDULE_ZONE,
    URL_AUTH_V2 as URL_AUTH,
    URL_BASE_V2 as URL_BASE,
    user_config_from_full_config as _user_config_from_full_config,
)

if TYPE_CHECKING:
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


def validate_id_of_url(
    id_fnc: Callable[[_urlT], str],
) -> Callable[..., Callable[[FakedServer], _bodyT]]:
    """Validate the id in the URL and set the status accordingly."""

    def decorator(
        fnc: Callable[[FakedServer], _bodyT | None],
    ) -> Callable[[FakedServer], _bodyT]:
        @functools.wraps(fnc)
        def wrapper(svr: FakedServer) -> _bodyT:
            if svr._method != HTTPMethod.GET:
                svr.status = HTTPStatus.METHOD_NOT_ALLOWED
                return {"message": "Method not allowed"}

            assert svr._url  # mypy
            try:
                id: str = id_fnc(svr._url)
            except IndexError:
                svr.status = HTTPStatus.NOT_FOUND
                return {"message": "Not Found"}

            if not id.isdigit():
                svr.status = HTTPStatus.BAD_REQUEST
                return [{"message": "Bad request"}]

            if result := fnc(svr):
                return result

            svr.status = HTTPStatus.UNAUTHORIZED
            return [{"message": "Unauthorized"}]

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
        return self.body


class FakedServerV0(FakedServerBase):
    """Mocked vendor server for provision of v0 URL responses."""

    def v0_session(self) -> _bodyT | None:
        raise NotImplementedError

    def v0_account_info(self) -> _bodyT | None:
        raise NotImplementedError

    def v0_locations(self) -> _bodyT | None:
        raise NotImplementedError

    def v0_evo_touch_systems(self) -> _bodyT | None:
        raise NotImplementedError

    def v0_heat_setpoint(self) -> _bodyT | None:
        raise NotImplementedError

    def v0_changeable_values(self) -> _bodyT | None:
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
        self._user_config = self._user_config_from_full_config(self._full_config)

    def oauth_token(self) -> _bodyT | None:
        if self._method != HTTPMethod.POST:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif self._url == URL_AUTH:
            return MOCK_AUTH_RESPONSE
        return None

    def usr_account(self) -> _bodyT:
        if self._method != HTTPMethod.GET:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        elif self._url == f"{URL_BASE}/userAccount":
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
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:
                if tcs[sch.S2_SYSTEM_ID] == tcs_id:
                    return tcs  # type: ignore[no-any-return]
        return None

    def zon_schedule(self) -> _bodyT | None:
        zon_id = _zon_id(self._url)  # type: ignore[arg-type]

        if self._method == HTTPMethod.GET:
            if zon_id == GHOST_ZONE_ID:
                self.status = HTTPStatus.BAD_REQUEST
                return [{"code": "ScheduleNotFound", "message": "Schedule not found."}]
            return self._schedules.get(zon_id, self._zon_schedule)

        if self._method != HTTPMethod.PUT:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        if not isinstance(self._data, dict):
            self.status = HTTPStatus.BAD_REQUEST
            return [{"message": "Bad Request (invalid schedule: not a dict)"}]

        try:
            SCH_PUT_SCHEDULE_ZONE(self._data)
        except vol.Invalid:
            self.status = HTTPStatus.BAD_REQUEST
            return {"message": "Bad Request (invalid schedule: invalid schema)"}

        self._schedules[zon_id] = convert_to_get_schedule(self._data)
        return {"id": "1234567890"}

    def zon_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_zon_id)
    def zon_status(self) -> _bodyT | None:
        zon_id = _zon_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[sch.S2_GATEWAYS]:
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:
                for zone in tcs[sch.S2_ZONES]:
                    if zone[sch.S2_ZONE_ID] == zon_id:
                        return zone  # type: ignore[no-any-return]
        return None

    def dhw_schedule(self) -> _bodyT | None:
        dhw_id = _dhw_id(self._url)  # type: ignore[arg-type]

        if self._method == HTTPMethod.GET:
            return self._schedules.get(dhw_id, self._dhw_schedule)

        if self._method != HTTPMethod.PUT:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowed"}

        if not isinstance(self._data, dict):
            self.status = HTTPStatus.BAD_REQUEST
            return [{"message": "Bad Request (invalid schedule: not a dict)"}]

        try:
            SCH_PUT_SCHEDULE_DHW(self._data)
        except vol.Invalid:
            self.status = HTTPStatus.BAD_REQUEST
            return {"message": "Bad Request (invalid schedule: invalid schema)"}

        self._schedules[dhw_id] = convert_to_get_schedule(self._data)
        return {"id": "1234567890"}

    @validate_id_of_url(_dhw_id)
    def dhw_status(self) -> _bodyT | None:
        dhw_id = _dhw_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[sch.S2_GATEWAYS]:
            for tcs in gwy[sch.S2_TEMPERATURE_CONTROL_SYSTEMS]:
                if dhw := tcs.get(sch.S2_DHW):
                    if dhw[sch.S2_DHW_ID] == dhw_id:
                        return dhw  # type: ignore[no-any-return]
        return None

    def dhw_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @staticmethod
    def _user_config_from_full_config(full_config: list) -> dict:
        """Create a valid MOCK_USER_CONFIG from a MOCK_FULL_CONFIG."""
        return _user_config_from_full_config(full_config)


class FakedServer(FakedServerV2, FakedServerV0):
    """Mocked vendor server for provision via a hacked aiohttp."""


REQUEST_MAP_V0: dict[str, Callable] = {
    #
    r"/session": FakedServer.v0_session,  # authentication
    #
    r"/accountInfo$": FakedServer.v0_account_info,
    #
    r"/locations?userId=": FakedServer.v0_locations,
    #
    r"/evoTouchSystems?locationId=": FakedServer.v0_evo_touch_systems,
    #
    r"/devices/.*/thermostat/changeableValues/heatSetpoint": FakedServer.v0_heat_setpoint,
    r"/devices/.*/thermostat/changeableValues": FakedServer.v0_changeable_values,
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
REQUEST_MAP = REQUEST_MAP_V0 | REQUEST_MAP_V2
