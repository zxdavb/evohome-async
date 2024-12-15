"""evohome-async - test config."""

from __future__ import annotations

import pytest

from tests.const import _DBG_USE_REAL_AIOHTTP


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
def use_real_aiohttp() -> bool:
    """Return True if using the real aiohttp library.

    This indicates testing is against the vendor's servers rather than a faked server.
    """
    return _DBG_USE_REAL_AIOHTTP
