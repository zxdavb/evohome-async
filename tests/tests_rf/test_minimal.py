"""evohome-async - a minimal test of instantiation/update of each client."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from evohome import exceptions as exc
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from tests.conftest import EvohomeClientv0, EvohomeClientv2


#######################################################################################


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_update_v0(evohome_v0: EvohomeClientv0) -> None:
    """Make a minimal test of instantiation/update of the v0 client."""

    with pytest.raises(exc.InvalidConfigError):
        assert evohome_v0.user_account

    await evohome_v0.update()

    assert evohome_v0.user_account


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_update_v2(evohome_v2: EvohomeClientv2) -> None:
    """Make a minimal test of instantiation/update of the v2 client."""

    with pytest.raises(exc.InvalidConfigError):
        assert evohome_v2.user_account

    await evohome_v2.update(_dont_update_status=True)

    assert evohome_v2.user_account
