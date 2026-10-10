"""Tests for evohome-async - the setup() and get_status() methods of both clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

import evohomeasync as evo1
import evohomeasync2 as evo2
from _evohome import exceptions as exc
from tests.common import get_loc, get_zon

from .conftest import FIXTURES_V0, FIXTURES_V2, auth_get

if TYPE_CHECKING:
    from _evohome.helpers import Validator
    from evohome_cli.auth import TokenCacheManager


async def test_v2_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config only, and Location.get_status() the status."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        evo = evo2.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = evo.locations

        await evo.setup()

        loc = get_loc(evo)  # the config is available...
        zone = get_zon(evo)
        assert zone is not None  # the default/ fixture has zones

        with pytest.raises(exc.EvohomeError):  # ... but not the status
            _ = zone.status

        status = await loc.get_status()

        assert status["location_id"] == loc.id
        assert zone.status["zone_id"] == zone.id  # no longer raises


async def test_v2_update_is_unchanged(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update() is still setup() plus the status of every location."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        evo = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use setup\(\), then Location.get_status\(\)"
        ):
            await evo.update()

        zone = get_zon(evo)
        assert zone is not None  # the default/ fixture has zones
        assert zone.status["zone_id"] == zone.id  # update() got the status too

        loc = get_loc(evo)
        with pytest.warns(DeprecationWarning, match=r"use get_status\(\)"):
            status = await loc.update()
        assert status == await loc.get_status()


async def test_v2_update_without_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test update(dont_update_status=True) still gets the config only (as setup())."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(FIXTURES_V2 / "default")):
        evo = evo2.EvohomeClient(credentials_manager)
        with pytest.warns(
            DeprecationWarning, match=r"use setup\(\), then Location.get_status\(\)"
        ):
            await evo.update(dont_update_status=True)

    zone = get_zon(evo)
    assert zone is not None  # the default/ fixture has zones

    with pytest.raises(exc.EvohomeError):
        _ = zone.status


async def test_v1_setup(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test setup() gets the config and, as v1 has them in one GET, the status."""

    with patch("evohomeasync.auth.Auth.get", auth_get(FIXTURES_V0 / "default")):
        evo = evo1.EvohomeClient(credentials_manager)

        with pytest.raises(exc.EvohomeError):
            _ = evo.locations

        await evo.setup()

        assert get_loc(evo).zones[0].temperature is not None


async def test_v1_get_status(
    credentials_manager: TokenCacheManager,
) -> None:
    """Test get_status() gets the latest status every time it is called."""

    mock_get = auth_get(FIXTURES_V0 / "default")
    calls: list[str] = []

    async def get(self: object, url: str, /, schema: Validator[Any]) -> object:
        calls.append(url)
        return await mock_get(self, url, schema)

    with patch("evohomeasync.auth.Auth.get", get):
        evo = evo1.EvohomeClient(credentials_manager)

        result = await evo.get_status()  # also gets the config, as it is first
        with pytest.warns(
            DeprecationWarning, match=r"use setup\(\), then get_status\(\)"
        ):
            assert result == await evo.update()

        calls.clear()
        await evo.get_status()

    assert len(calls) == 1
    assert calls[0].startswith("locations?userId=")
