#!/usr/bin/env python3
"""evohome-async - validate the evohome-async APIs (methods)."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import datetime as dt
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

import evohomeasync2 as evo2
from evohomeasync2 import exceptions as exc
from evohomeasync2.client import TokenManager

from .conftest import DEFAULT_PASSWORD, DEFAULT_USERNAME

if TYPE_CHECKING:
    from datetime import datetime as dt

    import aiohttp


#######################################################################################


@pytest.fixture
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Yield a client session, which may be faked."""

    def post_side_effect(*args: Any, **kwargs: Any) -> Any:
        """Raise an exception."""

        if args != ("https://tccna.honeywell.com/Auth/OAuth/Token",):
            raise aiohttp.ClientResponseError(None, (), status=HTTPStatus.NOT_FOUND)

        data = kwargs["data"]

        if data["grant_type"] == "refresh_token":  # mock it is not valid
            raise aiohttp.ClientResponseError(None, (), status=HTTPStatus.UNAUTHORIZED)

        # else: data["grant_type"] == "password"...

        if (
            data.get("Username") != DEFAULT_USERNAME
            or data.get("Password") != DEFAULT_PASSWORD
        ):
            raise aiohttp.ClientResponseError(None, (), status=HTTPStatus.BAD_REQUEST)

        raise aiohttp.ClientResponseError(None, (), status=HTTPStatus.TOO_MANY_REQUESTS)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.post = post_side_effect

    try:
        yield mock_session
    finally:
        await mock_session.close()


async def test_token_manager_loading(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
    tmp_path: Path,
    token_data: dict[str, Any],
) -> None:
    """Test the token manager by loading different token data from the cache."""

    def tokens_are_null() -> bool:
        return (
            token_manager.access_token == ""
            and token_manager.access_token_expires <= dt.min
            and token_manager.refresh_token == ""
        )

    # we don't use the token_manager fixture in this test
    token_cache = tmp_path / ".evo-cache.tst"

    token_manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    assert tokens_are_null()
    assert not token_manager.is_token_data_valid()

    #
    # Test 0: null token cache (zero-length content in file)
    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_token_data_valid()

    #
    # Test 1: valid token cache
    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    await token_manager.load_access_token()

    assert not tokens_are_null()
    assert token_manager.is_token_data_valid()

    #
    # Test 2: empty token cache (empty dict in file)
    with token_cache.open("w") as f:
        f.write(json.dumps({}))

    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_token_data_valid()

    #
    # Test 1: valid token cache (again)
    with token_cache.open("w") as f:
        f.write(json.dumps(token_data))

    await token_manager.load_access_token()

    assert not tokens_are_null()
    assert token_manager.is_token_data_valid()

    #
    # Test 3: invalid token cache (different username)
    with token_cache.open("w") as f:
        f.write(json.dumps({f"_{credentials[0]}": token_data[credentials[0]]}))

    await token_manager.load_access_token()

    assert tokens_are_null()
    assert not token_manager.is_token_data_valid()


async def _test_token_manager_00(
    credentials: tuple[str, str],
    token_cache: Path,
    client_session: aiohttp.ClientSession,
) -> None:
    """Test token manager."""

    token_manager = TokenManager(*credentials, client_session, token_cache=token_cache)

    assert not token_manager.is_token_data_valid()

    await token_manager.get_access_token()

    assert token_manager.is_token_data_valid()


async def _test_evo_update_00(
    evohome_v2: evo2.EvohomeClientNew,
) -> None:
    """Test EvohomeClient2.update()."""

    evo = evohome_v2

    assert evo._user_info is None
    assert evo._install_config is None

    await evo.update(reset_config=False, dont_update_status=False)

    assert evo._user_info is not None
    assert evo._install_config is not None  # type: ignore[unreachable]

    assert evo.locations[0]._status == {}

    await evo.update(reset_config=True)

    assert evo._user_info is not None
    assert evo._install_config is not None

    assert evo.locations[0]._status != {}


async def _test_evo_update_01(
    evohome_v2: evo2.EvohomeClientNew,
) -> None:
    """Test EvohomeClient2.update()."""

    evo = evohome_v2

    with patch(
        "evohomeasync2.auth.AbstractTokenManager._post_access_token_request"
    ) as mock_fcn:
        mock_fcn.side_effect = exc.AuthenticationFailedError(
            "", status=HTTPStatus.TOO_MANY_REQUESTS
        )
        await evo.update()
