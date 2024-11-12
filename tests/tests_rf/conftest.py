#!/usr/bin/env python3
"""evohome-async - test config."""

from __future__ import annotations

import pytest

from .const import _DBG_USE_REAL_AIOHTTP


@pytest.fixture(autouse=False)
def zpatches_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the evohomeasync and evohomeasync2 modules."""

    if _DBG_USE_REAL_AIOHTTP:
        import aiohttp
    else:
        from .faked_server import aiohttp  # type: ignore[no-redef]

    monkeypatch.setattr("evohomeasync.auth.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.auth.aiohttp", aiohttp)
    monkeypatch.setattr("evohomeasync2.client.aiohttp", aiohttp)


# #####################################################################################


@pytest.fixture(scope="session")
def use_fake_aiohttp() -> bool:
    """Return True is using the real aiohttp library."""
    return not _DBG_USE_REAL_AIOHTTP
