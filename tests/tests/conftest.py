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

from _evohome.helpers import convert_keys_to_snake_case
from evohomeasync import EvohomeClient as EvohomeClientV0
from evohomeasync.schemas import TCC_GET_USR_INFO, TCC_GET_USR_LOCS
from evohomeasync2 import EvohomeClient as EvohomeClientV2

from .aioresponses import AioResponses, aioresponses

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    import voluptuous as vol

    from evohome_cli.auth import TokenCacheManager


type JsonValueType = (
    dict[str, "JsonValueType"] | list["JsonValueType"] | str | int | float | bool | None
)
type JsonArrayType = list["JsonValueType"]
type JsonObjectType = dict[str, "JsonValueType"]


class ClientStub:
    auth = None
    _logger = logging.getLogger(__name__)

    @property
    def logger(self) -> logging.Logger:
        return self._logger


@pytest.fixture  # (autouse=True)
def block_aiohttp() -> Generator[AioResponses]:
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


FIXTURES_V0 = Path(__file__).parent / "fixtures_v0"
FIXTURES_V2 = Path(__file__).parent / "fixtures_v2"


def _load_fixture(folder: Path, file_name: str) -> JsonArrayType | JsonObjectType:
    """Load a fixture file; xfail immediately if not present (no default/ fallback)."""

    try:
        return load_fixture(folder / file_name)
    except FileNotFoundError:
        pytest.xfail(f"Fixture file not found: {file_name}")


def _load_schedule_fixture(
    folder: Path, file_name: str
) -> JsonArrayType | JsonObjectType:
    """Load a schedule fixture; fall back to default/ if not present.

    Schedule files are generic enough to share across systems.
    """

    try:
        try:
            return load_fixture(folder / file_name)
        except FileNotFoundError:
            return load_fixture(folder.parent / "default" / file_name)
    except FileNotFoundError:
        pytest.xfail(f"Fixture file not found: {file_name}")


def user_info_fixture(folder: Path) -> JsonObjectType:
    """Load the JSON of the v0 user information."""
    return _load_fixture(folder, "user_info.json")  # type: ignore[return-value]


def user_locs_fixture(folder: Path) -> JsonObjectType:
    """Load the JSON of the v0 user installation (locations)."""
    return _load_fixture(folder, "user_locs.json")  # type: ignore[return-value]


def user_account_fixture(folder: Path) -> JsonObjectType:
    """Load the JSON of the user installation."""
    return _load_fixture(folder, "user_account.json")  # type: ignore[return-value]


def user_locations_config_fixture(folder: Path) -> JsonArrayType:
    """Load the JSON of the config of a user's installation (a list of locations)."""
    return _load_fixture(folder, "user_locations.json")  # type: ignore[return-value]


def location_status_fixture(folder: Path, loc_id: str) -> JsonObjectType:
    """Load the JSON of the status of a location."""
    return _load_fixture(folder, f"status_{loc_id}.json")  # type: ignore[return-value]


def zone_schedule_fixture(folder: Path, zon_type: str) -> JsonObjectType:
    """Load the JSON of the schedule of a dhw/zone."""
    return _load_schedule_fixture(
        folder, f"schedule_{'dhw' if zon_type == 'domesticHotWater' else 'zone'}.json"
    )  # type: ignore[return-value]


def auth_get(fixture: Path) -> Callable[[Any, str, vol.Schema | None], Any]:
    """Return a mock of Auth.get() for both v0 and v2 API."""

    async def get(  # type: ignore[no-untyped-def]
        self,  # noqa: ANN001
        url: str,
        schema: vol.Schema | None = None,
    ) -> JsonArrayType | JsonObjectType:
        # "accountInfo"
        if "accountInfo" in url:
            return convert_keys_to_snake_case(  # type: ignore[no-any-return]
                TCC_GET_USR_INFO(user_info_fixture(fixture)["userInfo"])
            )

        # f"locations?userId={usr_id}&allData=True"
        if "locations" in url:
            return convert_keys_to_snake_case(  # type: ignore[no-any-return]
                TCC_GET_USR_LOCS(user_locs_fixture(fixture))
            )

        # mirror what auth.request() + auth.get() do: snake-case keys, then apply
        # whatever schema the model passes so enum values are coerced to members

        # "userAccount"
        if "userAccount" in url:
            data: JsonArrayType | JsonObjectType = convert_keys_to_snake_case(
                user_account_fixture(fixture)
            )
            return schema(data) if schema else data  # pyright: ignore[reportReturnType]

        # f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True"
        if "installationInfo" in url:
            data = convert_keys_to_snake_case(user_locations_config_fixture(fixture))
            return schema(data) if schema else data  # pyright: ignore[reportReturnType]

        # f"{_TCC_TYPE}/{id}/status?includeTemperatureControlSystems=True"
        if "status" in url:
            data = convert_keys_to_snake_case(
                location_status_fixture(fixture, url.split("/")[1])
            )
            return schema(data) if schema else data  # pyright: ignore[reportReturnType]

        # f"{_TCC_TYPE}/{id}/schedule"
        if "schedule" in url:
            data = convert_keys_to_snake_case(
                zone_schedule_fixture(fixture, url.split("/", maxsplit=1)[0])
            )
            return schema(data) if schema else data  # pyright: ignore[reportReturnType]

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
async def evohome_v0(
    credentials_manager: TokenCacheManager,
    fixture_folder: Path,
) -> AsyncGenerator[EvohomeClientV0]:
    """Yield an instance of a v2 EvohomeClient."""

    with patch("evohomeasync.auth.Auth.get", auth_get(fixture_folder)):
        evo = EvohomeClientV0(credentials_manager)

        await evo.update()

        try:
            yield evo
        finally:
            pass


@pytest.fixture
async def evohome_v2(
    credentials_manager: TokenCacheManager,
    fixture_folder: Path,
) -> AsyncGenerator[EvohomeClientV2]:
    """Yield an instance of a v2 EvohomeClient."""

    with patch("evohomeasync2.auth.Auth.get", auth_get(fixture_folder)):
        evo = EvohomeClientV2(credentials_manager)

        await evo.update()

        try:
            yield evo
        finally:
            pass
