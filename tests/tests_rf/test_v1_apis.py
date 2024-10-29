#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs)."""

from __future__ import annotations

import logging

import pytest

import evohomeasync as evohome

from .conftest import _DBG_USE_REAL_AIOHTTP
from .helpers import aiohttp, instantiate_client_v1

_LOGGER = logging.getLogger(__name__)


async def _test_client_apis(evo: evohome.EvohomeClient) -> None:
    """Instantiate a client, and logon to the vendor API."""

    user_data = await evo._populate_user_data()
    assert user_data == evo.user_info

    full_data = await evo._populate_locn_data()
    assert full_data == evo.location_data

    temps = await evo.get_temperatures()

    assert temps

    # for _ in range(3):
    #     await asyncio.sleep(5)
    #     _ = await evo.get_temperatures()
    #     _LOGGER.warning("get_temperatures() OK")


async def test_client_apis(
    user_credentials: tuple[str, str], client_session: aiohttp.ClientSession
) -> None:
    """Test _populate_user_data() & _populate_full_data()"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this API")

    try:
        await _test_client_apis(
            await instantiate_client_v1(*user_credentials, session=client_session)
        )
    except evohome.AuthenticationFailed:
        pytest.skip("Unable to authenticate")
