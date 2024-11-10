#!/usr/bin/env python3
"""Tests for evohome-async - validate the schema of HA's debug JSON (newer ver)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable, Generator
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import voluptuous as vol
from aioresponses import aioresponses

import evohomeasync2 as evo2
from evohomeasync2.schema import SCH_FULL_CONFIG, SCH_LOCN_STATUS, SCH_USER_ACCOUNT

if TYPE_CHECKING:
    from ..conftest import TokenManager


type JsonValueType = (
    dict[str, JsonValueType] | list[JsonValueType] | str | int | float | bool | None
)
type JsonArrayType = list[JsonValueType]
type JsonObjectType = dict[str, JsonValueType]

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class ClientStub:
    auth = None
    broker = None
    _logger = logging.getLogger(__name__)


@pytest.fixture()  # autouse=True)
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
        if "userAccount" in url:
            return SCH_USER_ACCOUNT(user_account_fixture(install))  # type: ignore[no-any-return]

        elif "installationInfo" in url:
            return SCH_FULL_CONFIG(user_locations_config_fixture(install))  # type: ignore[no-any-return]

        elif "status" in url:
            return SCH_LOCN_STATUS(location_status_fixture(install, url.split("/")[1]))  # type: ignore[no-any-return]

        pytest.fail(f"Unexpected/unknown URL: {url}")

    return get


# #####################################################################################


@pytest.fixture(scope="session")
def use_fake_aiohttp() -> bool:
    """Return True is using the real aiohttp library."""
    return False


# @pytest.fixture  # NOTE: is a WIP
# async def evohome_v1(
#     install: str,
#     session_manager: SessionManager,
# ) -> AsyncGenerator[evo1.EvohomeClient, None]:
#     """Yield an instance of a v1 EvohomeClient."""

#     with patch("evohomeasync1.auth.Auth.get", broker_get(install)):
#         evo = evo1.EvohomeClient(session_manager)

#         await evo.update()

#         try:
#             yield evo
#         finally:
#             pass


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
