#!/usr/bin/env python3
"""Tests for evohome-async - validate the schema of HA's debug JSON (newer ver)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable, Generator
from datetime import datetime as dt
from functools import lru_cache
from pathlib import Path
from typing import Final
from unittest.mock import patch

import aiohttp
import pytest
import voluptuous as vol
from aioresponses import aioresponses

import evohomeasync2 as evo2
from evohomeasync2.auth import AbstractTokenManager
from evohomeasync2.schema import SCH_FULL_CONFIG, SCH_LOCN_STATUS, SCH_USER_ACCOUNT

type JsonValueType = (
    dict[str, JsonValueType] | list[JsonValueType] | str | int | float | bool | None
)
type JsonArrayType = list[JsonValueType]
type JsonObjectType = dict[str, JsonValueType]

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# used to construct the default token cache
DEFAULT_USERNAME: Final[str] = "username@email.com"
DEFAULT_PASSWORD: Final[str] = "P@ssw0rd!!"  # noqa: S105


class ClientStub:
    auth = None
    broker = None
    _logger = logging.getLogger(__name__)


class TokenManager(AbstractTokenManager):
    async def restore_access_token(self) -> None:
        """Restore the access token from the cache."""

        self._access_token = "access_token"  # noqa: S105
        self._access_token_expires = dt.max
        self._refresh_token = "refresh_token"  # noqa: S105

    async def save_access_token(self) -> None:
        """Save the access token to the cache."""
        pass


@pytest.fixture(autouse=True)
def block_aiohttp() -> Generator[Callable]:
    """Prevent any actual I/O: will raise ClientConnectionError(Connection refused)."""
    with aioresponses() as m:
        yield m


@lru_cache
def load_fixture(file: Path) -> JsonArrayType | JsonObjectType:
    """Load a file fixture."""

    text = Path(file).read_text()

    return json.loads(text)  # type: ignore[no-any-return]


def _load_fixture(install: str, file_name: str) -> JsonArrayType | JsonObjectType:
    """Load a file fixture."""

    try:
        try:
            result = load_fixture(FIXTURES_DIR / install / file_name)
        except FileNotFoundError:
            result = load_fixture(FIXTURES_DIR / "default" / file_name)

    except FileNotFoundError:
        pytest.xfail(f"Fixture file not found: {file_name}")

    return result


def user_account_fixture(install: str) -> JsonObjectType:
    """Load the JSON of the user installation."""
    return _load_fixture(install, "user_account.json")  # type: ignore[return-value]


def user_locations_config_fixture(install: str) -> JsonArrayType:
    """Load the JSON of the config of a user's installation (a list of locations)."""
    return _load_fixture(install, "user_locations.json")  # type: ignore[return-value]


def location_status_fixture(install: str, loc_id: str) -> JsonObjectType:
    """Load the JSON of the status of a location."""
    return _load_fixture(install, f"status_{loc_id}.json")  # type: ignore[return-value]


def broker_get(install: str) -> Callable:
    """Return a mock of Broker.get()."""

    async def get(  # type: ignore[no-untyped-def]
        self, url: str, schema: vol.Schema | None = None
    ) -> JsonArrayType | JsonObjectType:
        if "userAccount" in url:  # EvohomeClient.user_account
            return SCH_USER_ACCOUNT(user_account_fixture(install))  # type: ignore[no-any-return]

        elif "installationInfo" in url:  # EvohomeClient._installation
            return SCH_FULL_CONFIG(user_locations_config_fixture(install))  # type: ignore[no-any-return]

        elif "status" in url:  # Location.refresh_status
            return SCH_LOCN_STATUS(location_status_fixture(install, url.split("/")[1]))  # type: ignore[no-any-return]

        pytest.fail(f"Unexpected/unknown URL: {url}")

    return get


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Yield a vanilla aiohttp.ClientSession."""

    client_session = aiohttp.ClientSession()

    try:
        yield client_session
    finally:
        await client_session.close()


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Return a username and a password."""

    return DEFAULT_USERNAME, DEFAULT_PASSWORD


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def token_manager(
    client_session: aiohttp.ClientSession,
    credentials: tuple[str, str],
) -> AsyncGenerator[TokenManager, None]:
    """Yield a token manager with vanilla credentials."""

    token_manager = TokenManager(credentials[0], credentials[1], client_session)
    await token_manager.restore_access_token()

    try:
        yield token_manager
    finally:
        await token_manager.save_access_token()


@pytest.fixture
async def evohome_v2(
    install: str,
    token_manager: TokenManager,
) -> AsyncGenerator[evo2.EvohomeClientNew, None]:
    """Yield an instance of a v2 EvohomeClient."""

    with patch("evohomeasync2.auth.Auth.get", broker_get(install)):
        evo = evo2.EvohomeClientNew(token_manager)

        await evo.update()

        try:
            yield evo
        finally:
            pass
