#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the updated Evohome API.

It is (largely) a faithful port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""
from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from datetime import datetime as dt
from datetime import timedelta as td
from typing import TYPE_CHECKING

import aiohttp

try:  # voluptuous is an optional module...
    import voluptuous as vol  # type: ignore[import-untyped]

except ModuleNotFoundError:  # No module named 'voluptuous'

    class vol:  # type: ignore[no-redef]
        class Invalid(Exception):
            pass

        Schema = dict | list


if TYPE_CHECKING:
    import logging

    from .typing import _EvoDictT, _EvoSchemaT


from . import exceptions
from .const import (
    AUTH_HEADER_ACCEPT,
    AUTH_HEADER,
    AUTH_URL,
    URL_BASE,
    AUTH_PAYLOAD,
    CREDS_REFRESH_TOKEN,
    CREDS_USER_PASSWORD,
)
from .schema.account import SCH_OAUTH_TOKEN


_ERR_MSG_LOOKUP_BOTH: dict[int, str] = {  # common to both OAUTH_URL & URL_BASE
    HTTPStatus.INTERNAL_SERVER_ERROR: "Can't reach server (check vendor's status page)",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method not allowed (dev/test?)",
    HTTPStatus.SERVICE_UNAVAILABLE: "Can't reach server (check vendor's status page)",
    HTTPStatus.TOO_MANY_REQUESTS: "Vendor's API rate limit exceeded (wait a while)",
}

_ERR_MSG_LOOKUP_AUTH: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # POST OAUTH_URL
    HTTPStatus.BAD_REQUEST: "Invalid user credentials (check the username/password)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid URL?)",
    HTTPStatus.UNAUTHORIZED: "Invalid access token (dev/test only)",
}

_ERR_MSG_LOOKUP_BASE: dict[int, str] = _ERR_MSG_LOOKUP_BOTH | {  # GET/PUT URL_BASE
    HTTPStatus.BAD_REQUEST: "Bad request (invalid data/json?)",
    HTTPStatus.NOT_FOUND: "Not Found (invalid entity type?)",
    HTTPStatus.UNAUTHORIZED: "Unauthorized (unknown entity id?)",
}


class Broker:
    """A class for interacting with the Evohome API."""

    def __init__(
        self,
        username: str,
        password: str,
        /,
        *,
        refresh_token: str | None = None,
        access_token: str | None = None,
        access_token_expires: dt | None = None,
        session: aiohttp.ClientSession | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """A class for interacting with the Evohome API."""

        self._credentials = {"Username": username, "Password": password}
        self._logger = logger or logging.getLogger(__name__)

        self.refresh_token = refresh_token
        self.access_token = access_token
        self.access_token_expires = access_token_expires

        self._session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def _client(
        self, method, url, data=None, json=None, headers=None
    ) -> tuple[aiohttp.ClientResponse, None | dict | list | str]:
        """Wrapper for aiohttp.ClientSession()."""

        if headers is None:
            headers = await self._headers()

        if method == HTTPMethod.GET:
            _session_method = self._session.get
            kwargs = {"headers": headers}

        elif method == HTTPMethod.POST:
            _session_method = self._session.post
            kwargs = {"data": data, "headers": headers}

        elif method == HTTPMethod.PUT:
            _session_method = self._session.put
            # headers["Content-Type"] = "application/json"
            kwargs = {"json": json, "headers": headers}

        async with _session_method(url, **kwargs) as response:

            if not response.content_length:
                content = None
                self._logger.info(f"{method} {url} ({response.status}) = {content}")

            elif response.content_type == "application/json":
                content = await response.json()
                self._logger.info(f"{method} {url} ({response.status}) = {content}")

            else:  # assume "text/plain" or "text/html"
                content = await response.text()
                self._logger.debug(f"{method} {url} ({response.status}) = {content}")

            return response, content  # FIXME: is messy to return response

    async def _headers(self) -> dict[str, str]:
        """Ensure the Authorization Header has a valid Access Token."""

        if not self.access_token or not self.access_token_expires:
            await self._basic_login()

        elif dt.now() > self.access_token_expires - td(seconds=30):
            await self._basic_login()

        assert isinstance(self.access_token, str)  # mypy

        return {
            "Accept": AUTH_HEADER_ACCEPT,
            "Authorization": "bearer " + self.access_token,
            "Content-Type": "application/json",
        }

    async def _basic_login(self) -> None:
        """Obtain a new access token from the vendor (as it is invalid, or expired).

        First, try using the refresh token, if one is available, otherwise authenticate
        using the user credentials.
        """

        # assert (
        #     not self.access_token
        #     or not self.access_token_expires
        #     or dt.now() > self.access_token_expires - td(seconds=30)
        # )

        self._logger.debug("No/Expired/Invalid access_token, re-authenticating.")
        self.access_token = self.access_token_expires = None

        if self.refresh_token:
            self._logger.debug("Authenticating with the refresh_token...")
            credentials = {"refresh_token": self.refresh_token}

            try:
                await self._obtain_access_token(CREDS_REFRESH_TOKEN | credentials)  # type: ignore[arg-type]

            except exceptions.AuthenticationError as exc:
                if exc.status != 400:  # Bad Request
                    raise

                self._logger.warning(
                    "Invalid refresh_token (will try username/password)"
                )
                self.refresh_token = None

        if not self.refresh_token:
            self._logger.debug("Authenticating with username/password...")
            await self._obtain_access_token(CREDS_USER_PASSWORD | self._credentials)  # type: ignore[arg-type]

        self._logger.debug(f"refresh_token = {self.refresh_token}")
        self._logger.debug(f"access_token = {self.access_token}")
        self._logger.debug(f"access_token_expires = {self.access_token_expires}")

    async def _obtain_access_token(self, credentials: dict[str, str]) -> None:
        """Obtain an access token using either the refresh token or user credentials."""

        response, content = await self._client(
            HTTPMethod.POST,
            AUTH_URL,
            data=AUTH_PAYLOAD | credentials,
            headers=AUTH_HEADER,
        )
        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as exc:
            if hint := _ERR_MSG_LOOKUP_AUTH.get(exc.status):
                raise exceptions.AuthenticationError(hint, status=exc.status)
            raise exceptions.AuthenticationError(str(exc), status=exc.status)

        except aiohttp.ClientError as exc:  # ClientConnectionError/ClientResponseError
            raise exceptions.AuthenticationError(str(exc))

        try:  # the access token _should_ be valid...
            _ = SCH_OAUTH_TOKEN(content)  # can't use result, due to obsfucated values
        except vol.Invalid as exc:
            self._logger.warning(
                f"Response may be invalid (bad schema): POST {AUTH_URL}: {exc}"
            )

        assert isinstance(content, dict)  # mypy

        try:  # the access token _should_ be valid...
            self.access_token = content["access_token"]
            self.access_token_expires = dt.now() + td(seconds=content["expires_in"])
            self.refresh_token = content["refresh_token"]

        except (KeyError, TypeError) as exc:
            raise exceptions.AuthenticationError(f"Invalid response from server: {exc}")

    async def get(
        self, url: str, schema: vol.Schema | None = None
    ) -> _EvoSchemaT:
        """"""

        response, content = await self._client(HTTPMethod.GET, f"{URL_BASE}/{url}")
        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as exc:
            if hint := _ERR_MSG_LOOKUP_BASE.get(exc.status):
                raise exceptions.FailedRequest(hint, status=exc.status)
            raise exceptions.FailedRequest(str(exc), status=exc.status)

        except aiohttp.ClientError as exc:  # incl. ClientConnectionError
            raise exceptions.FailedRequest(str(exc))

        if schema:
            try:
                return schema(content)
            except vol.Invalid as exc:
                self._logger.warning(
                    f"Response may be invalid (bad schema): GET {url}: {exc}"
                )

        assert isinstance(content, (dict, list))  # mypy
        return content

    async def put(
        self, url: str, json: _EvoDictT | str, schema: vol.Schema | None = None
    ) -> _EvoSchemaT:
        """"""

        if schema:
            try:
                _ = schema(json)
            except vol.Invalid as exc:
                self._logger.warning(
                    f"JSON may be invalid (bad schema): PUT {url}: {exc}"
                )

        response, content = await self._client(
            HTTPMethod.PUT, f"{URL_BASE}/{url}", json=json
        )

        try:
            response.raise_for_status()

        except aiohttp.ClientResponseError as exc:
            if hint := _ERR_MSG_LOOKUP_BASE.get(exc.status):
                raise exceptions.FailedRequest(hint, status=exc.status)
            raise exceptions.FailedRequest(str(exc), status=exc.status)

        except aiohttp.ClientError as exc:  # incl. ClientConnectionError
            raise exceptions.FailedRequest(str(exc))

        assert isinstance(content, (dict, list))  # mypy
        return content