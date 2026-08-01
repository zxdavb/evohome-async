"""Tests for evohome-async - exception identity and empty-installation handling.

Exceptions raised directly by evohomeasync/evohomeasync2's own code (as opposed to the
shared _evohome.auth/_evohome.credentials base classes) should be reported as belonging
to that package, not to the internal _evohome package. Separately, an installation with
zero locations is valid data (not a config error) once update() has been called.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import evohomeasync as evo0
import evohomeasync2 as evo2
from _evohome import exceptions as base_exc

from .conftest import FIXTURES_V2 as FIXTURES, auth_get

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from tests.conftest import EvohomeClientV2


async def test_v2_locations_before_update_is_local_exception(
    credentials_manager: TokenCacheManager,
) -> None:
    """Accessing .locations before update() must raise evohomeasync2's own exception."""

    evo = evo2.EvohomeClient(credentials_manager)

    with pytest.raises(evo2.InvalidConfigError) as exc_info:
        _ = evo.locations

    assert type(exc_info.value).__module__ == "evohomeasync2.exceptions"
    assert isinstance(exc_info.value, base_exc.InvalidConfigError)  # still catchable


async def test_v0_locations_before_update_is_local_exception(
    credentials_manager: TokenCacheManager,
) -> None:
    """Accessing .locations before update() must raise evohomeasync's own exception."""

    evo = evo0.EvohomeClient(credentials_manager)

    with pytest.raises(evo0.InvalidConfigError) as exc_info:
        _ = evo.locations

    assert type(exc_info.value).__module__ == "evohomeasync.exceptions"
    assert isinstance(exc_info.value, base_exc.InvalidConfigError)  # still catchable


async def test_v2_empty_installation_has_no_locations(
    credentials_manager: TokenCacheManager,
) -> None:
    """An installation with 0 locations is valid data, not a config error."""

    fixture_folder = Path(FIXTURES) / "system_008"

    with patch("evohomeasync2.auth.Auth.get", auth_get(fixture_folder)):
        evo: EvohomeClientV2 = evo2.EvohomeClient(credentials_manager)
        await evo.update()

    assert evo.locations == []
    assert evo.location_by_id == {}

    # there being no locations at all is a NoSingleTcsError, not an InvalidConfigError
    with pytest.raises(evo2.NoSingleTcsError):
        _ = evo.tcs
