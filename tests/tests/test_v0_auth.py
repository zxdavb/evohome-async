"""evohome-async - validate the v0 API session manager."""

from __future__ import annotations

import json
import uuid
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from cli.auth import CredentialsManager

from evohomeasync import exceptions as exc
from evohomeasync.auth import _APPLICATION_ID
from tests.const import HEADERS_CRED_V0 as HEADERS_CRED, URL_CRED_V0 as URL_CRED

if TYPE_CHECKING:
    from pathlib import Path

    import aiohttp
    from cli.auth import CacheDataT
    from freezegun.api import FrozenDateTimeFactory


async def test_get_session_id(
    credentials: tuple[str, str],
    credentials_manager: CredentialsManager,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test .get_session_id() and .is_session_valid() methods."""

    def server_response() -> dict[str, dict[str, Any] | str]:
        """Return the server response to a valid authorization request."""
        return {"sessionId": str(uuid.uuid4()), "userInfo": {}}

    # TODO: ensure cache is empty...
    # maybe: cache_manager = CacheManager(...) here?

    #
    # have not yet called get_session_id (so not loaded cache either)
    assert credentials_manager.is_session_id_valid() is False

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
        rsp.post(URL_CRED, status=HTTPStatus.UNAUTHORIZED, payload=response)

        with pytest.raises(exc.AuthenticationFailedError):
            await credentials_manager.get_session_id()

        rsp.assert_called_once_with(
            URL_CRED, HTTPMethod.POST, headers=HEADERS_CRED, data=data_password
        )

    assert credentials_manager.is_session_id_valid() is False

    #
    # test HTTPStatus.OK
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED, payload=payload)

        assert await credentials_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(
            URL_CRED, HTTPMethod.POST, headers=HEADERS_CRED, data=data_password
        )

    assert credentials_manager.is_session_id_valid() is True

    #
    # check doesn't invoke the URL again, as session id still valid
    freezer.tick(600)  # advance time by 5 minutes

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mok:
        assert await credentials_manager.get_session_id() == payload["sessionId"]

        mok.assert_not_called()

    assert credentials_manager.is_session_id_valid() is True

    #
    # check session id now expired
    freezer.tick(1200)  # advance time by another 10 minutes, 15 total

    assert credentials_manager.is_session_id_valid() is False

    #
    # check does invoke the URL, as session id now expired
    #
    #
    payload = server_response()

    with aioresponses() as rsp:
        rsp.post(URL_CRED, payload=payload)

        assert await credentials_manager.get_session_id() == payload["sessionId"]

        rsp.assert_called_once_with(
            URL_CRED, HTTPMethod.POST, headers=HEADERS_CRED, data=data_password
        )

    assert credentials_manager.is_session_id_valid() is True

    #
    # test _clear_session_id()
    credentials_manager._clear_session_id()

    assert credentials_manager.is_session_id_valid() is False


async def test_session_manager(
    cache_data_expired: CacheDataT,
    cache_data_valid: CacheDataT,
    cache_file: Path,
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    freezer: FrozenDateTimeFactory,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Test the .load_session_id() and .save_session_id() methods."""

    cache_file = tmp_path_factory.getbasetemp() / ".evo-cache.tst"

    #
    # TEST 1: load an invalid cache...
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_expired, indent=4))

    cache_manager = CredentialsManager(
        *credentials, client_session, cache_file=cache_file
    )

    # have not yet called get_access_token (so not loaded cache either)
    assert cache_manager.is_session_id_valid() is False

    await cache_manager.load_from_cache()
    assert cache_manager.is_session_id_valid() is False

    #
    # TEST 2: load a valid token cache
    with cache_file.open("w") as f:
        f.write(json.dumps(cache_data_valid, indent=4))

    cache_manager = CredentialsManager(
        *credentials, client_session, cache_file=cache_file
    )

    await cache_manager.load_from_cache()
    assert cache_manager.is_session_id_valid() is True

    session_id = await cache_manager.get_session_id()

    #
    # TEST 3: some time has passed, but token is not expired
    freezer.tick(600)  # advance time by 5 minutes
    assert cache_manager.is_session_id_valid() is True

    assert await cache_manager.get_session_id() == session_id

    #
    # TEST 4: test save_session_id() method
    freezer.tick(1800)  # advance time by 15 minutes, 20 mins total
    assert cache_manager.is_session_id_valid() is False

    with (
        patch(
            "evohomeasync.auth.AbstractSessionManager._post_session_id_request",
            new_callable=AsyncMock,
        ) as req,
        patch(
            "cli.auth.CredentialsManager.save_session_id", new_callable=AsyncMock
        ) as wrt,
    ):
        req.return_value = {
            "sessionId": "new_session_id...",
            "userInfo": None,
        }

        assert await cache_manager.get_session_id() == "new_session_id..."

        req.assert_called_once()
        wrt.assert_called_once()

    assert cache_manager.is_session_id_valid() is True
