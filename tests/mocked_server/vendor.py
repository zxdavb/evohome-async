#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked vendor server for provision via a hacked aiohttp."""
from __future__ import annotations

from http import HTTPStatus
import re
from typing import TYPE_CHECKING

from evohomeasync2.const import AUTH_URL, URL_BASE
from evohomeasync2.schema.const import (
    SZ_DHW,
    SZ_DHW_ID,
    SZ_DOMESTIC_HOT_WATER,
    SZ_GATEWAYS,
    SZ_LOCATION,
    SZ_LOCATION_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_TEMPERATURE_ZONE,
    SZ_ZONE_ID,
    SZ_ZONES,
)

from .const import (
    MOCK_AUTH_RESPONSE,
    MOCK_FULL_CONFIG,
    MOCK_LOCN_STATUS,
    MOCK_SCHEDULE_DHW,
    MOCK_SCHEDULE_ZONE,
)
from .const import hdrs, user_config_from_full_config as _user_config_from_full_config


if TYPE_CHECKING:
    from evohomeasync2.typing import _DhwIdT, _LocationIdT, _SystemIdT, _ZoneIdT
    from .const import _bodyT, _methodT, _statusT, _urlT


class MockedServer:
    """Mocked vendor server for provision via a hacked aiohttp."""

    def __init__(
        self,
        full_config: dict,
        locn_status: dict,
        /,
        *,
        zone_schedule: None | dict = None,
        dhw_schedule: None | dict = None,
    ) -> None:
        self._full_config = full_config or MOCK_FULL_CONFIG
        self._locn_status = locn_status or MOCK_LOCN_STATUS
        self._zone_schedule = zone_schedule or MOCK_SCHEDULE_ZONE
        self._dhw_schedule = dhw_schedule or MOCK_SCHEDULE_DHW

        self._user_config = self._user_config_from_full_config(self._full_config)

        self.body: None | _bodyT = None
        self._method: None | _methodT = None
        self.status: None | _statusT = None
        self._url: None | _urlT = None

    def request(
        self, method: _methodT, url: _urlT, data: None | dict | str = None
    ) -> _bodyT:
        self._method = method
        self._url = url
        self._data = data

        # 400: Bad Request  - assume invalid data / JSON
        # 401: Unauthorized - assume no access (to UserId, LocationId, ZoneId, etc.)
        # 404: Not Found    - assume bad url

        self.body, self.status = None, None
        for pattern, method in REQUEST_MAP.items():
            if re.search(pattern, url):
                self.body: None | _bodyT = method(self)
                break
        else:
            self.status = HTTPStatus.NOT_FOUND

        if not self.status:
            self.status = HTTPStatus.OK if self.body else HTTPStatus.NOT_FOUND
        return self.body

    def oauth_token(self) -> None | _bodyT:
        if self._method != hdrs.METH_POST:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif self._url == AUTH_URL:
            return MOCK_AUTH_RESPONSE

    def usr_account(self) -> None | _bodyT:
        if self._method != hdrs.METH_GET:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif self._url == f"{URL_BASE}/userAccount":
            return self._user_config
        else:
            self.status = HTTPStatus.NOT_FOUND

    def all_config(self) -> None | _bodyT:  # full_locn
        def user_id(url) -> str:
            return url.split("?userId=")[1].split("&")[0]

        if self._method != hdrs.METH_GET:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif "?userId=" not in self._url:
            self.status = HTTPStatus.NOT_FOUND
        elif not user_id(self._url).isdigit():
            self.status = HTTPStatus.BAD_REQUEST
        elif user_id(self._url) != self._user_config["userId"]:
            self.status = HTTPStatus.UNAUTHORIZED
        else:
            return self._full_config

    def loc_config(self) -> None | _bodyT:
        raise NotImplementedError

    def loc_status(self) -> None | _bodyT:
        if self._method != hdrs.METH_GET:
            self.status = HTTPStatus.METHOD_NOT_ALLOWED
        elif not self._loc_id(self._url).isdigit():
            self.status = HTTPStatus.BAD_REQUEST
        elif self._loc_id(self._url) != self._locn_status[SZ_LOCATION_ID]:
            self.status = HTTPStatus.UNAUTHORIZED
        else:
            return self._locn_status

    def tcs_mode(self) -> None | _bodyT:
        raise NotImplementedError

    def zon_schedule(self) -> None | _bodyT:
        return self._zone_schedule

    def zon_mode(self) -> None | _bodyT:
        raise NotImplementedError

    def zon_status(self) -> None | _bodyT:
        zone_id = self._zon_id(self._url)

        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                for zone in tcs[SZ_ZONES]:
                    if zone[SZ_ZONE_ID] == zone_id:
                        return zone

        self.status = 404

    def dhw_schedule(self) -> None | _bodyT:
        return self._dhw_schedule

    def dhw_status(self) -> None | _bodyT:
        raise NotImplementedError

    def dhw_mode(self) -> None | _bodyT:
        raise NotImplementedError

    #

    def _response_for_request(self) -> None | _bodyT:
        """Set the response body (and status) according to the request."""

        if "/Auth" in self._url and self._method == hdrs.METH_POST:
            # POST /Auth/OAuth/Token
            return self.auth_response()

        if "/userAccount" in self._url and self._method == hdrs.METH_GET:
            # GET /userAccount
            return self.user_config()

        if "/location" in self._url and self._method == hdrs.METH_GET:
            return self._response_for_location_request()

        if "/temperatureControlSystem" in self._url and self._method == hdrs.METH_PUT:
            if self._method != hdrs.METH_PUT:
                pass

            elif re.search(r"temperatureControlSystem/.*/mode", self._url):
                # PUT /temperatureControlSystem/{systemId}/mode"
                return self.full_config()

        if "/temperatureZone" in self._url and self._method in (
            hdrs.METH_GET,
            hdrs.METH_PUT,
        ):
            return self._response_for_zone_request()

        if "/domesticHotWater" in self._url and self._method in (
            hdrs.METH_GET,
            hdrs.METH_PUT,
        ):
            return self._response_for_dhw_request()

    def _handle_user_account_request(self) -> None | _bodyT:
        if self._method == hdrs.METH_POST:
            return self.auth_response()

    def _response_for_location_request(self) -> None | _bodyT:
        """"""

        if self._method != hdrs.METH_GET:
            pass

        elif re.search(r"location/installationInfo", self._url):
            # GET /location/installationInfo?userId={userId}
            return self.full_config()

        elif re.search(r"location/.*/installationInfo", self._url):
            # GET /location/{locationId}/installationInfo
            return self.locn_config(location_id=None)

        elif re.search(r"location/.*/status", self._url):
            # GET /location/{locationId}/status
            return self.locn_status(location_id=None)

    def _response_for_zone_request(self) -> None | _bodyT:
        """"""

        def zone_id() -> _ZoneIdT:
            return self._url.split("temperatureZone/")[1].split("/")[0]

        if self._method == hdrs.METH_GET:
            if re.search(r"temperatureZone/.*/schedule", self._url):
                # GET /temperatureZone/{zoneId}/schedule  # /{zone_type}/{zoneId}/schedule
                return self.zone_schedule(zone_id=zone_id())

            if re.search(r"temperatureZone/.*/status", self._url):
                # GET /temperatureZone/{zoneId}/status  # /{zone_type}/{zoneId}/schedule
                return self.zone_status(zone_id=zone_id())

        elif self._method == hdrs.METH_PUT:
            if re.search(r"temperatureZone/.*/schedule", self._url):
                # PUT /temperatureZone/{zoneId}/schedule
                return {"id": "123456789"}

            if re.search(r"temperatureZone/.*/heatSetpoint", self._url):  # aka mode
                # PUT /temperatureZone/{zoneId}/heatSetpoint
                raise NotImplementedError

    def _response_for_dhw_request(self) -> None | _bodyT:
        """"""

        def dhw_id() -> _DhwIdT:
            return self._url.split("domesticHotWater/")[1].split("/")[0]

        if self._method == hdrs.METH_GET:
            if re.search(r"domesticHotWater/.*/schedule", self._url):
                # GET /domesticHotWater/{dhwId}/schedule  # /{zone_type}/{zoneId}/schedule
                return self.dhw_schedule(dhw_id=dhw_id())

            if re.search(r"domesticHotWater/.*/status", self._url):
                # GET /domesticHotWater/{dhwId}/status
                return self.dhw_status(dhw_id=dhw_id())

        elif self._method == hdrs.METH_PUT:
            if re.search(r"domesticHotWater/.*/schedule", self._url):
                # PUT /domesticHotWater/{dhwId}/schedule
                return {"id": "123456789"}

            if re.search(r"domesticHotWater/.*/state", self._url):  # aka mode
                # PUT /domesticHotWater/{dhwId}/state
                raise NotImplementedError

    def user_config(self) -> dict:
        return self._user_config

    def full_config(self) -> dict:
        return self._full_config

    def locn_config(self, location_id: None | str) -> dict:
        raise NotImplementedError

    def locn_status(self, location_id: None | str) -> dict:
        return self._locn_status

    def dhw_schedule_old(self, dhw_id: _DhwIdT) -> dict:
        return self._dhw_schedule

    def dhw_status_old(self, dhw_id: _DhwIdT) -> None | dict:
        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                if (dhw := tcs.get(SZ_DHW)) and dhw[SZ_DHW_ID] == dhw_id:
                    return dhw

        self.status = 404

    def zone_status(self, zone_id: _ZoneIdT) -> None | dict:
        for gwy in self._locn_status[SZ_GATEWAYS]:
            for tcs in gwy[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
                for zone in tcs[SZ_ZONES]:
                    if zone[SZ_ZONE_ID] == zone_id:
                        return zone

        self.status = 404

    def zone_schedule(self, zone_id: _ZoneIdT) -> dict:
        return self._zone_schedule

    @staticmethod
    def _user_config_from_full_config(full_config: dict) -> dict:
        """Create a valid MOCK_USER_CONFIG from a MOCK_FULL_CONFIG."""
        return _user_config_from_full_config(full_config)

    @staticmethod
    def _dhw_id(url) -> _DhwIdT:
        """Extract a DHW ID from a URL."""
        return url.split(f"{SZ_DOMESTIC_HOT_WATER}/")[1].split("/")[0]

    @staticmethod
    def _loc_id(url) -> _LocationIdT:
        """Extract a Location ID from a URL."""
        return url.split(f"{SZ_LOCATION}/")[1].split("/")[0]

    @staticmethod
    def _tcs_id(url) -> _SystemIdT:
        """Extract a TCS ID from a URL."""
        return url.split(f"{SZ_TEMPERATURE_CONTROL_SYSTEMS}/")[1].split("/")[0]

    @staticmethod
    def _zon_id(url) -> _ZoneIdT:
        """Extract a Zone ID from a URL."""
        return url.split(f"{SZ_TEMPERATURE_ZONE}/")[1].split("/")[0]


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
    #
    r"/temperatureZone/.*/status": MockedServer.zon_status,
    r"/temperatureZone/.*/heatSetpoint": MockedServer.zon_mode,
    r"/temperatureZone/.*/schedule": MockedServer.zon_schedule,
    #
    r"/domesticHotWater/.*/status": MockedServer.dhw_status,
    r"/domesticHotWater/.*/state": MockedServer.dhw_mode,
    r"/domesticHotWater/.*/schedule": MockedServer.dhw_schedule,
}
