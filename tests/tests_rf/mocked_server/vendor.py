#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked vendor server for provision via a hacked aiohttp."""
from __future__ import annotations

import re
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

from evohomeasync2.const import AUTH_URL, URL_BASE
from evohomeasync2.schema import (
    convert_to_get_schedule,
    vol,  # voluptuous
)
from evohomeasync2.schema.const import (
    SZ_DHW,
    SZ_DHW_ID,
    SZ_DOMESTIC_HOT_WATER,
    SZ_GATEWAYS,
    SZ_LOCATION,
    SZ_LOCATION_ID,
    SZ_SYSTEM_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEM,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TEMPERATURE_ZONE,
    SZ_ZONE_ID,
    SZ_ZONES,
)
from evohomeasync2.schema.schedule import (
    SCH_PUT_SCHEDULE_DHW,
    SCH_PUT_SCHEDULE_ZONE,
)

from .const import (
    GHOST_ZONE_ID,
    MOCK_AUTH_RESPONSE,
    MOCK_FULL_CONFIG,
    MOCK_LOCN_STATUS,
    MOCK_SCHEDULE_DHW,
    MOCK_SCHEDULE_ZONE,
    user_config_from_full_config as _user_config_from_full_config,
)

if TYPE_CHECKING:
    from evohomeasync2.schema import (
        _DhwIdT,
        _LocationIdT,
        _SystemIdT,
        _UserIdT,
        _ZoneIdT,
    )

    from .const import _bodyT, _methodT, _statusT, _urlT


def _dhw_id(url: _urlT) -> _DhwIdT:
    """Extract a DHW ID from a URL."""
    return url.split(f"{SZ_DOMESTIC_HOT_WATER}/")[1].split("/")[0]


def _loc_id(url: _urlT) -> _LocationIdT:
    """Extract a Location ID from a URL."""
    return url.split(f"{SZ_LOCATION}/")[1].split("/")[0]


def _tcs_id(url: _urlT) -> _SystemIdT:
    """Extract a TCS ID from a URL."""
    return url.split(f"{SZ_TEMPERATURE_CONTROL_SYSTEM}/")[1].split("/")[0]


def _usr_id(url: _urlT) -> _UserIdT:
    """Extract a TCS ID from a URL."""
    return url.split("?userId=")[1].split("&")[0]


def _zon_id(url: _urlT) -> _ZoneIdT:
    """Extract a Zone ID from a URL."""
    return url.split(f"{SZ_TEMPERATURE_ZONE}/")[1].split("/")[0]


def validate_id_of_url(id_fnc):
    """Validate the ID in the URL and set the status accordingly."""

    def decorator(func):
        def wrapper(self: MockedServer) -> _bodyT:
            if self._method != HTTPMethod.GET:
                self.status = HTTPStatus.METHOD_NOT_ALLOWED
                return {"message": "Method not allowed"}

            try:
                id: str = id_fnc(self._url)
            except IndexError:
                self.status = HTTPStatus.NOT_FOUND
                return {"message": "Not Found"}

            if not id.isdigit():
                self.status = HTTPStatus.BAD_REQUEST
                return [{"message": "Bad request"}]

            if result := func(self):
                return result

            self.status = HTTPStatus.UNAUTHORIZED
            return [{"message": "Unauthorized"}]

        return wrapper

    return decorator


class MockedServer:
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

        self._schedules = {}
        self._user_config = self._user_config_from_full_config(self._full_config)

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
        for pattern, method in REQUEST_MAP.items():
            if re.search(pattern, url):
                self.body = method(self)
                break
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

    def oauth_token(self) -> _bodyT | None:
        if self._method != HTTPMethod.POST:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif self._url == AUTH_URL:
            return MOCK_AUTH_RESPONSE
        return None

    def usr_account(self) -> _bodyT | None:
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

        if self._user_config["userId"] == usr_id:
            return self._full_config
        return None

    def loc_config(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_loc_id)
    def loc_status(self) -> _bodyT | None:
        loc_id = _loc_id(self._url)  # type: ignore[arg-type]

        if self._locn_status[SZ_LOCATION_ID] == loc_id:
            return self._locn_status
        return None

    def tcs_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @validate_id_of_url(_tcs_id)
    def tcs_status(self) -> _bodyT | None:
        tcs_id = _tcs_id(self._url)  # type: ignore[arg-type]

        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                if tcs[SZ_SYSTEM_ID] == tcs_id:
                    return tcs
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

        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                for zone in tcs[SZ_ZONES]:
                    if zone[SZ_ZONE_ID] == zon_id:
                        return zone
        return None

    def dhw_schedule(self) -> _bodyT | None:
        dhw_id = _dhw_id(self._url)  # type: ignore[arg-type]

        if self._method == HTTPMethod.GET:
            return self._schedules.get(dhw_id, self._dhw_schedule)

        if self._method != HTTPMethod.PUT:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
            return {"message": "Method not allowes"}

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

        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                if dhw := tcs.get(SZ_DHW):
                    if dhw[SZ_DHW_ID] == dhw_id:
                        return dhw
        return None

    def dhw_mode(self) -> _bodyT | None:
        raise NotImplementedError

    @staticmethod
    def _user_config_from_full_config(full_config: list) -> dict:
        """Create a valid MOCK_USER_CONFIG from a MOCK_FULL_CONFIG."""
        return _user_config_from_full_config(full_config)


REQUEST_MAP = {
    #
    r"/Auth/OAuth/Token": MockedServer.oauth_token,
    #
    r"/userAccount$": MockedServer.usr_account,
    r"/location/installationInfo": MockedServer.all_config,
    #
    r"/location/.*/installationInfo": MockedServer.loc_config,
    r"/location/.*/status": MockedServer.loc_status,
    #
    r"/temperatureControlSystem/.*/mode": MockedServer.tcs_mode,
    r"/temperatureControlSystem/.*/status": MockedServer.tcs_status,
    #
    r"/temperatureZone/.*/status": MockedServer.zon_status,
    r"/temperatureZone/.*/heatSetpoint": MockedServer.zon_mode,
    r"/temperatureZone/.*/schedule": MockedServer.zon_schedule,
    #
    r"/domesticHotWater/.*/status": MockedServer.dhw_status,
    r"/domesticHotWater/.*/state": MockedServer.dhw_mode,
    r"/domesticHotWater/.*/schedule": MockedServer.dhw_schedule,
}
