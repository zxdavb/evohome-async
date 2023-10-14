#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked webserver server via a hacked aiohttp.ClientSession."""
from __future__ import annotations

from enum import EnumCheck, StrEnum, verify
import re
from types import TracebackType
from typing import Any, Final, Type

import aiohttp
import json

# from evohomeasync2.const import AUTH_URL, URL_BASE


@verify(EnumCheck.UNIQUE)
class hdrs(StrEnum):
    METH_GET: Final[str] = "get"
    METH_POST: Final[str] = "post"
    METH_PUT: Final[str] = "put"


class ClientError(Exception):
    """Base class for client connection errors."""


class ClientResponseError(ClientError):
    """Base class for exceptions that occur after getting a response."""

    def __init__(self, /, *, status: None | int = None) -> None:
        self.status: int = status or 404


class ClientTimeout:
    """"""

    def __init__(self, /, *, total: None | float = None, **kwargs) -> None:
        self._total: int = total or 30


class ClientSession:
    """First-class interface for making HTTP requests."""

    def __init__(
        self,
        base_url: str,
        /,
        *,
        timeout: None | ClientTimeout = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout or ClientTimeout()

    def get(self, url, /, headers: None | str = None):
        return ClientResponse(hdrs.METH_GET, url)

    def put(
        self, url, /, *, data: Any = None, json: Any = None, headers: None | str = None
    ):
        return ClientResponse(hdrs.METH_PUT, url, data=data or json)

    def post(self, url, /, *, data: Any = None, headers: None | str = None):
        return ClientResponse(hdrs.METH_POST, url, data=data)

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: None | Type[BaseException],
        exc_val: None | BaseException,
        exc_tb: None | TracebackType,
    ) -> None:
        pass


class ClientResponse:
    """"""

    def __init__(self, method: str, url: str) -> None:
        self.method = method
        self.url = url

        self.status = None
        self._body = self._response_for_request()  # may set self._status

    def raise_for_status(self) -> None:
        if self.status:
            raise self.status

    async def text(self, /, **kwargs) -> str:  # TODO: if no body...
        """Return the response body as text."""
        return self._body

    async def json(self, /, **kwargs) -> dict:  # TODO: if no body...
        """Return the response body as json (a dict)."""
        return json.loads(self._body)

    def _response_for_request(self):
        """Set the response body (and status) according to the request."""

        if "/Auth" in self.url and self.method == hdrs.METH_POST:
            # POST /Auth/OAuth/Token
            return

        if "/userAccount" in self.url and self.method == hdrs.METH_GET:
            # GET /userAccount
            return

        if "/location" in self.url and self.method == hdrs.METH_GET:
            return self._response_for_location_request()

        if "/gateway" in self.url and self.method == hdrs.METH_GET:
            # GET /gateway
            return

        if "/temperatureControlSystem" in self.url and self.method == hdrs.METH_PUT:
            # PUT /temperatureControlSystem/{systemId}/mode"
            return

        if "/temperatureZone" in self.url and self.method in (
            hdrs.METH_GET,
            hdrs.METH_PUT,
        ):
            return self._response_for_zone_request()

        if "/domesticHotWater" in self.url and self.method in (
            hdrs.METH_GET,
            hdrs.METH_PUT,
        ):
            return self._response_for_dhw_request()

        self.status = aiohttp.ClientResponseError  # unknown URL, set status to non-null

    def _response_for_location_request(self):
        """"""

        if self.method != hdrs.METH_GET:
            pass

        elif re.match(r"location/installationInfo", self.url):
            # GET /location/installationInfo?userId={userId}
            return

        elif re.match(r"location/.*/installationInfo", self.url):
            # GET /location/{locationId}/installationInfo
            return

        elif re.match(r"location/.*/status", self.url):
            # GET /location/{locationId}/status
            return

        self.status = aiohttp.ClientResponseError(status=404)

    def _response_for_zone_request(self):
        """"""

        if self.method == hdrs.METH_GET:
            if re.match(r"temperatureZone/.*/schedule", self.url):
                # GET /temperatureZone/{zoneId}/schedule  # /{zone_type}/{zoneId}/schedule
                return

        elif self.method == hdrs.METH_PUT:
            if re.match(r"temperatureZone/.*/schedule", self.url):
                # PUT /temperatureZone/{zoneId}/schedule
                return

            if re.match(r"temperatureZone/.*/heatSetpoint", self.url):  # aka mode
                # PUT /temperatureZone/{zoneId}/heatSetpoint
                return

        self.status = aiohttp.ClientResponseError

    def _response_for_dhw_request(self):
        """"""

        if self.method == hdrs.METH_GET:
            if re.match(r"domesticHotWater/.*/schedule", self.url):
                # GET /domesticHotWater/{dhwId}/schedule  # /{zone_type}/{zoneId}/schedule
                return

            if re.match(r"domesticHotWater/.*/status", self.url):
                # GET /domesticHotWater/{dhwId}/status
                return

        elif self.method == hdrs.METH_PUT:
            if re.match(r"domesticHotWater/.*/schedule", self.url):
                # PUT /domesticHotWater/{dhwId}/schedule
                return

            if re.match(r"domesticHotWater/.*/state", self.url):  # aka mode
                # PUT /domesticHotWater/{dhwId}/state
                return

        self.status = aiohttp.ClientResponseError


RESPONSES = {}
