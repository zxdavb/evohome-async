"""Validate the instantiation/update of each client.

Performs the bare minimum of tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from _evohome import exceptions as exc
from tests.const import _DBG_USE_REAL_AIOHTTP

from .common import skipif_auth_failed

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient as EvohomeClientV1
    from evohomeasync2 import EvohomeClient as EvohomeClientV2


#######################################################################################


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_update_v1(
    ec1: EvohomeClientV1,
) -> None:
    """Make a minimal test of instantiation/update of the v1 client."""

    with pytest.raises(exc.NotFetchedError):
        assert ec1.user_account

    await ec1.get_status()

    assert ec1.user_account


@skipif_auth_failed
@pytest.mark.skipif(not _DBG_USE_REAL_AIOHTTP, reason="requires vendor's webserver")
async def test_update_v2(
    ec2: EvohomeClientV2,
) -> None:
    """Make a minimal test of instantiation/update of the v2 client."""

    with pytest.raises(exc.NotFetchedError):
        assert ec2.user_account

    await ec2.setup()

    assert ec2.user_account
