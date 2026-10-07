"""Tests for evohome-async - validate the schema of HA's debug JSON (newer ver)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import aiohttp
import probatio as vol
import pytest

from _evohome import exceptions as exc
from _evohome.helpers import convert_keys_to_snake_case
from evohomeasync import EvohomeClient as EvohomeClientV0
from evohomeasync2 import EvohomeClient as EvohomeClientV2
from tests.common import get_dhw, get_tcs, get_zon

from .aioresponses import AioResponses, aioresponses

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    from _evohome.helpers import Validator
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync2 import ControlSystem, HotWater, Zone
    from evohomeasync2.auth import Auth


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


def zone_schedule_fixture(folder: Path, zon_type: str, zon_id: str) -> JsonObjectType:
    """Load the JSON of the schedule of a dhw/zone.

    Use the dhw/zone's own schedule (schedule_{id}.json), if the fixture has one.
    """

    try:
        schedule = load_fixture(folder / f"schedule_{zon_id}.json")
    except FileNotFoundError:
        schedule = _load_schedule_fixture(
            folder,
            f"schedule_{'dhw' if zon_type == 'domesticHotWater' else 'zone'}.json",
        )

    assert isinstance(schedule, dict), schedule  # a schedule is a JSON object
    return schedule


def auth_get(fixture: Path) -> Callable[[Any, str, Validator[Any]], Any]:
    """Return a mock of Auth.get() for both v0 and v2 API."""

    def _get[T](url: str, schema: Validator[T]) -> T:
        # mirror what auth.request() + auth.get() do: snake-case keys, then apply
        # the schema the model passes (it is required) so enum values are coerced to members
        # (a failure of that schema is wrapped by get(), below)
        data: object

        # "accountInfo"
        if "accountInfo" in url:
            data = convert_keys_to_snake_case(user_info_fixture(fixture)["userInfo"])
            return schema(data)

        # f"locations?userId={usr_id}&allData=True"
        if "locations" in url:
            data = convert_keys_to_snake_case(user_locs_fixture(fixture))
            return schema(data)

        # "userAccount"
        if "userAccount" in url:
            data = convert_keys_to_snake_case(user_account_fixture(fixture))
            return schema(data)

        # f"location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True"
        if "installationInfo" in url:
            data = convert_keys_to_snake_case(user_locations_config_fixture(fixture))
            return schema(data)

        # f"{_TCC_TYPE}/{id}/status?includeTemperatureControlSystems=True"
        if "status" in url:
            data = convert_keys_to_snake_case(
                location_status_fixture(fixture, url.split("/")[1])
            )
            return schema(data)

        # f"{_TCC_TYPE}/{id}/schedule"
        if "schedule" in url:
            data = convert_keys_to_snake_case(
                zone_schedule_fixture(fixture, *url.split("/")[:2])
            )
            return schema(data)

        pytest.fail(f"Unexpected/unknown URL: {url}")

    async def get[T](  # type: ignore[no-untyped-def]
        self,  # noqa: ANN001
        url: str,
        /,
        schema: Validator[T],
    ) -> T:
        try:
            return _get(url, schema)
        except vol.Invalid as err:  # as does Auth.get()
            raise exc.BadApiResponseError(
                f"GET {url}: response failed validation: {err}"
            ) from err

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


@pytest.fixture
def auth(evohome_v2: EvohomeClientV2) -> Auth:
    """Return the Auth object of the client (e.g. to create a CommTask)."""
    return evohome_v2.auth


@pytest.fixture
def tcs(evohome_v2: EvohomeClientV2) -> ControlSystem:
    """Return the first TCS of the location under test (see get_tcs()).

    Fail the test if there is none, as then the test is using the wrong fixture.
    """
    try:
        return get_tcs(evohome_v2)
    except IndexError:
        pytest.fail("The location under test has no TCS")


@pytest.fixture
def zone(evohome_v2: EvohomeClientV2) -> Zone:
    """Return the first zone of the location under test (see get_zon()).

    Fail the test if there is none, as then the test is using the wrong fixture.
    """
    if (zon := get_zon(evohome_v2)) is None:
        pytest.fail("The location under test has no zone")
    return zon


@pytest.fixture
def dhw(evohome_v2: EvohomeClientV2) -> HotWater:
    """Return the DHW of the location under test (see get_dhw()).

    Fail the test if there is none, as then the test is using the wrong fixture.
    """
    if (dhw := get_dhw(evohome_v2)) is None:
        pytest.fail("The location under test has no DHW")
    return dhw
