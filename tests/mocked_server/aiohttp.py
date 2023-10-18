#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked webserver server via a hacked aiohttp.ClientSession."""
from __future__ import annotations

import asyncio
from enum import EnumCheck, StrEnum, verify
import re
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, Literal, Self, Type

from evohomeasync2.schema.const import (
    SZ_DHW,
    SZ_DHW_ID,
    SZ_GATEWAYS,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_ZONE_ID,
    SZ_ZONES,
)
import json

from .const import (
    MOCK_AUTH_RESPONSE,
    MOCK_FULL_CONFIG,
    MOCK_LOCN_STATUS,
    MOCK_SCHEDULE_DHW,
    MOCK_SCHEDULE_ZONE,
)
from .const import user_config_from_full_config as _user_config_from_full_config

if TYPE_CHECKING:
    from evohomeasync2.typing import _DhwIdT, _ZoneIdT


@verify(EnumCheck.UNIQUE)
class hdrs(StrEnum):
    METH_GET: Final[str] = "get"
    METH_POST: Final[str] = "post"
    METH_PUT: Final[str] = "put"


_bodyT = dict | str
_methodT = Literal[hdrs.METH_GET, hdrs.METH_POST, hdrs.METH_PUT]
_statusT = int
_urlT = str


_DEFAULT_LIMIT = 2**16  # 64 KiB


class StreamReader(asyncio.StreamReader):
    _buffer: bytearray = b""

    def __init__(self, limit=_DEFAULT_LIMIT, loop=None):
        pass

    async def read(self, n: int = -1) -> bytes:
        """Read up to `n` bytes from the stream."""
        raise NotImplementedError

    async def readline(self) -> bytes:
        """Read chunk of data from the stream until newline (b'\n') is found."""
        return await self.readuntil(b"\n")

    async def readexactly(self, n: int) -> bytes:
        """Read exactly `n` bytes."""
        raise NotImplementedError

    async def readuntil(self, separator: bytes = b"\n") -> bytes:
        """Read data from the stream until ``separator`` is found."""
        raise NotImplementedError

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: None | Type[BaseException],
        exc_val: None | BaseException,
        exc_tb: None | TracebackType,
    ) -> None:
        pass


class MockedServer:
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

    @staticmethod
    def _user_config_from_full_config(full_config: dict) -> dict:
        """Create a valid MOCK_USER_CONFIG from a MOCK_FULL_CONFIG."""
        return _user_config_from_full_config(full_config)

    def request(
        self, method: _methodT, url: _urlT, data: None | dict | str = None
    ) -> _bodyT:
        self._method = method
        self._url = url

        self.status = None
        self.body = self._response_for_request()  # TODO: handle data
        if self.status is None:
            self.status = 200 if self.body else 404

        return self.body

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

        if "/gateway" in self._url and self._method == hdrs.METH_GET:
            # GET /gateway
            raise NotImplementedError

        if "/temperatureControlSystem" in self._url and self._method == hdrs.METH_PUT:
            # PUT /temperatureControlSystem/{systemId}/mode"
            raise NotImplementedError

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
                raise NotImplementedError

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
                raise NotImplementedError

            if re.search(r"domesticHotWater/.*/state", self._url):  # aka mode
                # PUT /domesticHotWater/{dhwId}/state
                raise NotImplementedError

    def auth_response(self) -> dict:
        return MOCK_AUTH_RESPONSE  # TODO: consider status = 401

    def user_config(self) -> dict:
        return self._user_config

    def full_config(self) -> dict:
        return self._full_config

    def locn_config(self, location_id: None | str) -> dict:
        raise NotImplementedError

    def locn_status(self, location_id: None | str) -> dict:
        return self._locn_status

    def dhw_schedule(self, dhw_id: _DhwIdT) -> dict:
        return self._dhw_schedule

    def dhw_status(self, dhw_id: _DhwIdT) -> None | dict:
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


class ClientError(Exception):
    """Base class for client connection errors."""


class ClientResponseError(ClientError):
    """Base class for exceptions that occur after getting a response."""

    def __init__(self, msg, /, *, status: None | int = None, **kwargs) -> None:
        super().__init__(msg)
        self.status: int = status or 404


class ClientTimeout:
    """"""

    def __init__(self, /, *, total: None | float = None, **kwargs) -> None:
        self.total: float = total or 30


class ClientSession:
    """First-class interface for making HTTP requests."""

    def __init__(self, /, *, timeout: None | ClientTimeout = None, **kwargs) -> None:
        self._timeout = timeout or ClientTimeout()

        # this is required, so no .get()
        self._mocked_server: MockedServer = kwargs["mocked_server"]

    def get(self, url, /, headers: None | str = None):
        return ClientResponse(hdrs.METH_GET, url, session=self)

    def put(
        self, url, /, *, data: Any = None, json: Any = None, headers: None | str = None
    ):
        return ClientResponse(hdrs.METH_PUT, url, data=data or json, session=self)

    def post(self, url, /, *, data: Any = None, headers: None | str = None):
        return ClientResponse(hdrs.METH_POST, url, data=data, session=self)

    async def close(self) -> None:
        pass


class ClientResponse:
    """"""

    charset: str = "utf-8"

    def __init__(
        self,
        method: _methodT,
        url: _urlT,
        /,
        *,
        data: None | str = None,
        json: None | str = None,
        session: None | ClientSession = None,
        **kwargs,
    ) -> None:
        self.method = method
        self.url = url
        self.session = session

        self._mocked_server = self.session._mocked_server

        self.status: _statusT = None
        self._body: None | _bodyT = None

        # self.content = StreamReader(
        #     self._mocked_server.request(method, url, data=data or json)
        # )
        self._body = self._mocked_server.request(method, url, data=data or json)
        self.status = self._mocked_server.status

    def raise_for_status(self) -> None:
        if self.status >= 300:
            raise ClientResponseError(
                f"{self.method} {self.url}: {self.status}", status=self.status
            )

    async def text(self, /, **kwargs) -> str:  # TODO: if no body...
        """Return the response body as text."""
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)

    async def json(self, /, **kwargs) -> dict | list:  # TODO: if no body...
        """Return the response body as json (a dict)."""
        if isinstance(self._body, (dict, list)):
            return self._body
        return json.loads(self._body)

    async def __aenter__(self, *args, **kwargs) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: None | Type[BaseException],
        exc_val: None | BaseException,
        exc_tb: None | TracebackType,
    ) -> None:
        pass
