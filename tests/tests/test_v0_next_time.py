"""Tests for evohome-async - the v0 client sends a NextTime as the location's local time.

The v0 API treats a NextTime (and a QuickActionNextTime) as the location's local time,
and ignores any Z (see: tests_rf/test_vx_until.py). So, the client must send it as such,
in the location's TZ (which is DST-aware, as its IANA TZ is used).

The default/ fixture's location is in "GMT Standard Time" (i.e. Europe/London), which is
UTC+0 in winter, but UTC+1 in summer (BST).
"""

from __future__ import annotations

import copy
import logging
from datetime import UTC, datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from _evohome.exceptions import BadApiRequestError
from evohomeasync.entities import create_location
from evohomeasync.schemas import TccSystemMode
from tests.common import get_loc

from .conftest import FIXTURES_V0 as FIXTURES

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import AsyncMock as AsyncMockT

    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync import EvohomeClient as EvohomeClientV0


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [p for p in Path(FIXTURES).glob("*") if p.name == "default"]

    if not folders:
        raise pytest.fail("Missing fixture folder(s)")

    metafunc.parametrize("fixture_folder", folders, ids=(p.name for p in folders))


def _put_json(mock: AsyncMockT) -> dict[str, Any]:
    """Return the JSON of the (only) PUT, as sent to the vendor."""

    mock.assert_awaited_once()
    assert mock.await_args is not None  # mypy
    json: dict[str, Any] = mock.await_args.kwargs["json"]
    return json


@pytest.fixture
def mock_put() -> Iterator[AsyncMockT]:
    """Mock the request to the vendor (after its JSON is converted to their format)."""

    with patch(
        "_evohome.auth.AbstractAuth._make_request",
        new_callable=AsyncMock,
        return_value={"id": 1234567890},
    ) as mock:
        yield mock


@pytest.mark.parametrize(
    ("until", "next_time"),
    [
        # in winter, UTC is the local time (GMT)...
        (dt(2026, 1, 15, 12, 0, tzinfo=UTC), "2026-01-15T12:00:00"),
        # ...but, in summer, the local time is an hour ahead of UTC (BST)
        (dt(2026, 7, 1, 12, 0, tzinfo=UTC), "2026-07-01T13:00:00"),
        # an aware datetime in another TZ is converted to the location's TZ
        (
            dt(2026, 7, 1, 14, 0, tzinfo=ZoneInfo("Europe/Berlin")),
            "2026-07-01T13:00:00",
        ),
    ],
    ids=("winter", "summer", "other_tz"),
)
async def test_zone_next_time(
    evohome_v0: EvohomeClientV0,
    mock_put: AsyncMockT,
    until: dt,
    next_time: str,
) -> None:
    """Test Zone.set_temperature() sends its NextTime as the location's local time."""

    zone = get_loc(evohome_v0).zones[0]

    await zone.set_temperature(19.5, until=until)

    assert _put_json(mock_put) == {
        "status": "Temporary",
        "value": 19.5,
        "nextTime": next_time,  # without a Z
    }


async def test_next_time_after_dst_ends(
    evohome_v0: EvohomeClientV0,
    freezer: FrozenDateTimeFactory,
    mock_put: AsyncMockT,
) -> None:
    """Test a NextTime after a DST transition uses the UTC offset of then, not now.

    In 2026, BST ends at 01:00 UTC on 25 October. So, if it is set in BST, an override
    until after then must use the offset of GMT (not of BST, which is the offset now).
    """

    freezer.move_to("2026-10-24T12:00:00+00:00")  # BST (UTC+1)

    zone = get_loc(evohome_v0).zones[0]

    await zone.set_temperature(19.5, until=dt(2026, 10, 26, 12, 0, tzinfo=UTC))

    assert _put_json(mock_put)["nextTime"] == "2026-10-26T12:00:00"  # GMT (UTC+0)


async def test_dhw_next_time(
    evohome_v0: EvohomeClientV0,
    mock_put: AsyncMockT,
) -> None:
    """Test HotWater.set_dhw_on() sends its NextTime as the location's local time."""

    dhw = get_loc(evohome_v0).hotwater
    assert dhw is not None  # the default/ fixture has a DHW

    await dhw.set_dhw_on(until=dt(2026, 7, 1, 12, 0, tzinfo=UTC))

    assert _put_json(mock_put)["nextTime"] == "2026-07-01T13:00:00"  # BST


async def test_tcs_quick_action_next_time(
    evohome_v0: EvohomeClientV0,
    mock_put: AsyncMockT,
) -> None:
    """Test Location.set_mode() sends its QuickActionNextTime as the local time.

    NOTE: the vendor has removed this URL (it is now a 404, see test_v0_urls.py), so
    this tests only the payload, as it can't be confirmed against the vendor's server.
    """

    loc = get_loc(evohome_v0)

    await loc.set_mode(TccSystemMode.AWAY, until=dt(2026, 7, 1, 12, 0, tzinfo=UTC))

    assert _put_json(mock_put) == {
        "quickAction": "Away",
        "quickActionNextTime": "2026-07-01T13:00:00",  # BST, without a Z
    }


async def test_naive_next_time(
    evohome_v0: EvohomeClientV0,
    mock_put: AsyncMockT,
) -> None:
    """Test a naive NextTime is rejected (as its instant would be ambiguous)."""

    zone = get_loc(evohome_v0).zones[0]

    naive = dt(2026, 7, 1, 12, 0, tzinfo=UTC).replace(tzinfo=None)

    with pytest.raises(BadApiRequestError):
        await zone.set_temperature(19.5, until=naive)

    mock_put.assert_not_awaited()


async def test_unknown_time_zone(
    evohome_v0: EvohomeClientV0,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a location with an unknown TZ falls back to its current UTC offset."""

    config = copy.deepcopy(get_loc(evohome_v0).config)
    config["time_zone"]["id"] = "No Such Standard Time"
    config["time_zone"]["current_offset_minutes"] = 60

    with caplog.at_level(logging.WARNING):
        loc = await create_location(evohome_v0, config)

    assert "Unable to find IANA TZ identifier" in caplog.text
    assert loc.tzinfo.utcoffset(None) == td(hours=1)
