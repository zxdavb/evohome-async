#!/usr/bin/env python3
"""evohome-async - validate the v1 API session manager."""

from __future__ import annotations

import uuid
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory

from evohomeasync import exceptions as exc
from evohomeasync.auth import _APPLICATION_ID

from ..const import HEADERS_AUTH_V0 as HEADERS_AUTH, URL_AUTH_V0 as URL_AUTH

if TYPE_CHECKING:
    from ..common import SessionManager


async def test_get_session_id(
    credentials: tuple[str, str],
    session_manager: SessionManager,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_session_id() and .is_session_valid() methods."""

    def server_response() -> dict[str, dict | str]:
        """Return the server response to a valid authorization request."""
        return {"sessionId": str(uuid.uuid4()), "userInfo": {}}

    # TODO: ensure cache is empty...
    # maybe: session_manager = SessionManager(...) here?

    #
    # have not yet called get_session_id (so not loaded cache either)
    assert session_manager.is_session_valid() is False

    #
    # test HTTPStatus.UNAUTHORIZED -> exc.AuthenticationFailedError
    data_password = {  # later, we'll assert POST was called with this data
        "applicationId": _APPLICATION_ID,
        "username": credentials[0],
        "password": credentials[1],
    }

    with aioresponses() as rsp:
        response = [
            {
                "code": "EmailOrPasswordIncorrect",
                "message": "The email or password provided is incorrect.",
            }
        ]
        rsp.post(URL_AUTH, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.AuthenticationFailedError):
            await session_manager.get_session_id()

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert session_manager.is_session_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_AUTH, payload=payload)

        assert await session_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert session_manager.is_session_valid() is True

    #
    # check doesn't invoke the URL again, as session id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await session_manager.get_session_id() == payload["sessionId"]

        mok.assert_not_called()

    assert session_manager.is_session_valid() is True

    #
    # check session id now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert session_manager.is_session_valid() is False

    #
    # check does invoke the URL, as session id now expired
    #
    #
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_AUTH, payload=payload)

        assert await session_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(
            URL_AUTH, HTTPMethod.POST, headers=HEADERS_AUTH, data=data_password
        )

    assert session_manager.is_session_valid() is True

    #
    # test _clear_session_id()
    session_manager._clear_session_id()

    assert session_manager.is_session_valid() is False
