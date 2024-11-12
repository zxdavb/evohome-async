#!/usr/bin/env python3
"""evohome-async - validate the handling of vendor APIs (URLs)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .common import skipif_auth_failed
from .const import _DBG_USE_REAL_AIOHTTP

if TYPE_CHECKING:
    from ..conftest import EvohomeClientv0


async def _test_client_apis(evo: EvohomeClientv0) -> None:
    """Instantiate a client, and logon to the vendor API."""

    user_data = await evo._get_user_data()
    assert user_data == evo.user_info

    full_data = await evo._populate_locn_data()
    assert full_data == evo.location_data

    temps = await evo.get_temperatures()

    assert temps

    # for _ in range(3):
    #     await asyncio.sleep(5)
    #     _ = await evo.get_temperatures()
    #     _LOGGER.warning("get_temperatures() OK")


@skipif_auth_failed
async def test_client_apis(evohome_v0: EvohomeClientv0) -> None:
    """Test _populate_user_data() & _populate_full_data()"""

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this API")

    await _test_client_apis(evohome_v0)
