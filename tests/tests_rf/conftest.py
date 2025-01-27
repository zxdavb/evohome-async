"""evohome-async - test config."""

from __future__ import annotations

import os

import pytest

from tests.const import _DBG_USE_REAL_AIOHTTP, TEST_PASSWORD, TEST_USERNAME


@pytest.fixture(scope="session")
def use_real_aiohttp() -> bool:
    """Return True if using the real aiohttp library.

    This indicates testing is against the vendor's servers rather than a faked server.
    """
    return _DBG_USE_REAL_AIOHTTP


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    username: str = os.getenv("TEST_USERNAME") or TEST_USERNAME
    password: str = os.getenv("TEST_PASSWORD") or TEST_PASSWORD

    return username, password
