"""Tests for evohome-async - validate the schema of HA's debug JSON (newer ver)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses

from evohome.helpers import convert_keys_to_snake_case
from evohomeasync2 import _EvohomeClientNew as EvohomeClientv2
from evohomeasync2.schemas import (
    TCC_GET_LOC_STATUS,
    TCC_GET_USR_ACCOUNT,
    TCC_GET_USR_LOCATIONS,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    import voluptuous as vol

    from tests.conftest import TokenManager


type JsonValueType = (
    dict[str, "JsonValueType"] | list["JsonValueType"] | str | int | float | bool | None
)
type JsonArrayType = list["JsonValueType"]
type JsonObjectType = dict[str, "JsonValueType"]


class ClientStub:
    auth = None
    logger = logging.getLogger(__name__)


@pytest.fixture  # (autouse=True)
def block_aiohttp() -> Generator[Callable]:  # type: ignore[type-arg]
    """Prevent any actual I/O: will raise ClientConnectionError(Connection refused)."""
    with aioresponses() as m:
        yield m


@pytest.fixture  # @pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client_session() -> AsyncGenerator[aiohttp.ClientSession]:
    """Yield an aiohttp.ClientSession (never faked)."""

    client_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    try:
        yield client_session
    finally:
        await client_session.close()


@lru_cache
def load_fixture(file: Path) -> JsonArrayType | JsonObjectType:
    """Load a file fixture."""

    text = Path(file).read_text()

    return json.loads(text)  # type: ignore[no-any-return]


# NOTE: JSON from HA is not compliant with vendor schema, but is useful to test against
CONFIG_FILE_NAME = "config.json"
STATUS_FILE_NAME = "status.json"


@pytest.fixture  # used by test_schemas_0.py, test_schemas_1.py
def config(folder: Path) -> dict[str, Any]:
    """Fixture to load the configuration file."""
    # is camelCase, as per vendor's schema

    config_path = folder / CONFIG_FILE_NAME
    if not config_path.is_file():
        pytest.skip(f"No {CONFIG_FILE_NAME} in: {folder.name}")

    return load_fixture(config_path)  # type: ignore[return-value]


@pytest.fixture  # used by test_schemas_0.py, test_schemas_1.py
def status(folder: Path) -> dict[str, Any]:
    """Fixture to load the status file."""
    # is camelCase, as per vendor's schema

    status_path = folder / STATUS_FILE_NAME
    if not status_path.is_file():
        pytest.skip(f"No {STATUS_FILE_NAME} in: {folder.name}")

    return load_fixture(status_path)  # type: ignore[return-value]


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# wrapper for FIXTURES_DIR to enable default fixtures
def _load_fixture(install: str, file_name: str) -> JsonArrayType | JsonObjectType:
    """Load a file fixture and use a default fixture if not found."""

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


def broker_get(install: str) -> Callable[[Any, str, vol.Schema | None], Any]:
    """Return a mock of Broker.get()."""

    async def get(  # type: ignore[no-untyped-def]
        self,  # noqa: ANN001
        url: str,
        schema: vol.Schema | None = None,
    ) -> JsonArrayType | JsonObjectType:
        if "userAccount" in url:
            return convert_keys_to_snake_case(  # type: ignore[no-any-return]
                TCC_GET_USR_ACCOUNT(user_account_fixture(install))
            )

        if "installationInfo" in url:
            return convert_keys_to_snake_case(  # type: ignore[no-any-return]
                TCC_GET_USR_LOCATIONS(user_locations_config_fixture(install))
            )

        if "status" in url:
            return convert_keys_to_snake_case(  # type: ignore[no-any-return]
                TCC_GET_LOC_STATUS(location_status_fixture(install, url.split("/")[1]))
            )

        pytest.fail(f"Unexpected/unknown URL: {url}")

    return get


# #####################################################################################


@pytest.fixture(scope="session")
def use_real_aiohttp() -> bool:
    """Return True if using the real aiohttp library.

    This indicates testing is against the vendor's servers rather than a faked server.
    """
    return False


@pytest.fixture
async def evohome_v2(
    install: str,
    cache_manager: TokenManager,
) -> AsyncGenerator[EvohomeClientv2]:
    """Yield an instance of a v2 EvohomeClient."""

    with patch("evohomeasync2.auth.Auth.get", broker_get(install)):
        evo = EvohomeClientv2(cache_manager)

        await evo.update()

        try:
            yield evo
        finally:
            pass
