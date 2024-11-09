#!/usr/bin/env python3
"""evohome-async - validate the evohomeclient v1 session manager."""

from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory

from evohomeasync import exceptions as exc

from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:

    from .common import SessionManager


@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="is not using the real aiohttp")
async def test_get_session_id(
    session_manager: SessionManager,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_session_id() and .is_session_valid() methods."""

    # TODO: ensure cache is empty...
    # maybe: session_manager = SessionManager(...) here?

    #
    # have not yet called get_session_id (so not loaded cache either)
    assert session_manager.is_session_valid() is False

    #
    # test HTTPStatus.UNAUTHORIZED -> exc.AuthenticationFailedError
    with aioresponses() as rsp:
        rsp.post(
            "https://tccna.honeywell.com/WebAPI/api/session",
            status=HTTPStatus.UNAUTHORIZED,
            payload=[{"code": "EmailOrPasswordIncorrect", "message": "xxx"}],
        )

        with pytest.raises(exc.AuthenticationFailedError):
            await session_manager.get_session_id()

    assert session_manager.is_session_valid() is False

    #
    # test HTTPStatus.OK
    session_id = str(uuid.uuid4()).upper()

    with aioresponses() as rsp:
        rsp.post(
            "https://tccna.honeywell.com/WebAPI/api/session",
            payload={"sessionId": session_id, "userInfo": {}},
        )

        assert await session_manager.get_session_id() == session_id

    assert session_manager.is_session_valid() is True

    #
    # check doesn't invoke the URL again, as session_id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await session_manager.get_session_id() == session_id

        mok.assert_not_called()

    assert session_manager.is_session_valid() is True

    #
    # check session_id now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert session_manager.is_session_valid() is False

    #
    # check does invoke the URL, as session_id now expired
    session_id = str(uuid.uuid4()).upper()

    with aioresponses() as rsp:
        rsp.post(
            "https://tccna.honeywell.com/WebAPI/api/session",
            payload={"sessionId": session_id, "userInfo": {}},
        )

        assert await session_manager.get_session_id() == session_id

    assert session_manager.is_session_valid() is True

    #
    # test _clear_session_id()
    session_manager._clear_session_id()

    assert session_manager.is_session_valid() is False
