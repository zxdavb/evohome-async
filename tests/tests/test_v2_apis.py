"""evohome-async - validate the v2 API for DHW."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from .conftest import FIXTURES_V2

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

    from evohomeasync2 import EvohomeClient


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [
        p for p in Path(FIXTURES_V2).glob("*") if p.is_dir() and p.name == "default"
    ]
    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


# Test the ControlSystem APIs (incomplete)...
# NOTE: not all systems support all modes, below we only test evohome modes


async def test_ctl_mode_reset(  # TODO: test systems without AutoWithReset
    evohome_v2: EvohomeClient,
) -> None:
    """Test ControlSystem.reset() method."""

    tcs = evohome_v2.tcs

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": "AutoWithReset",  # SystemMode.AUTO_WITH_RESET,
        "permanent": True,
    }

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await tcs.reset()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


CTL_APIS_SANS_UNTIL = {  # system mode APIs that can take an until kwarg
    "set_auto": "Auto",  # SystemMode.AUTO,
}


@pytest.mark.parametrize("api_name", CTL_APIS_SANS_UNTIL)
async def test_ctl_modes_sans_until(
    evohome_v2: EvohomeClient,
    api_name: str,
) -> None:
    """Test ControlSystem.set_auto() method."""

    tcs = evohome_v2.tcs

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": CTL_APIS_SANS_UNTIL[api_name],
        "permanent": True,
    }

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await getattr(tcs, api_name)()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


CTL_APIS_WITH_UNTIL = {  # system mode APIs that can take an until kwarg
    "set_away": "Away",  # SystemMode.AWAY,
    "set_custom": "Custom",  # SystemMode.CUSTOM,
    "set_dayoff": "DayOff",  # SystemMode.DAY_OFF,
    "set_eco": "AutoWithEco",  # SystemMode.AUTO_WITH_ECO,
    "set_heatingoff": "HeatingOff",  # SystemMode.HEATING_OFF,
}


@pytest.mark.parametrize("api_name", CTL_APIS_WITH_UNTIL)
async def test_ctl_modes_with_until(
    evohome_v2: EvohomeClient,
    api_name: str,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test ControlSystem.set_*() methods (that can take an until kwarg)."""

    tcs = evohome_v2.tcs

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": CTL_APIS_WITH_UNTIL[api_name],
        "permanent": True,
    }

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await getattr(tcs, api_name)()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)

    freezer.move_to("2025-07-10T12:00:00Z")

    mode = {
        "systemMode": CTL_APIS_WITH_UNTIL[api_name],
        "permanent": False,
        "timeUntil": "2025-07-13T12:00:00Z",
    }

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await getattr(tcs, api_name)(until=dt.now(tz=UTC) + td(days=3))

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


# Test the HotWater APIs...


async def test_dhw_mode_off(
    evohome_v2: EvohomeClient,
) -> None:
    """Test HotWater.off() method."""

    dhw = evohome_v2.tcs.hotwater
    assert dhw is not None

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await dhw.off()

    MODE = {
        "mode": "PermanentOverride",  # ZoneMode.PERMANENT_OVERRIDE,
        "state": "Off",  # #            DhwState.OFF,
        "untilTime": None,
    }

    mock_put.assert_awaited_once()

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": MODE}


async def test_dhw_mode_on(
    evohome_v2: EvohomeClient,
) -> None:
    """Test HotWater.on() method."""

    dhw = evohome_v2.tcs.hotwater
    assert dhw is not None

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await dhw.on()

    mock_put.assert_awaited_once()

    MODE = {
        "mode": "PermanentOverride",  # ZoneMode.PERMANENT_OVERRIDE,
        "state": "On",  # #             DhwState.ON,
        "untilTime": None,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": MODE}


async def test_dhw_mode_reset(
    evohome_v2: EvohomeClient,
) -> None:
    """Test HotWater.reset() method."""

    dhw = evohome_v2.tcs.hotwater
    assert dhw is not None

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await dhw.reset()

    mock_put.assert_awaited_once()

    MODE = {
        "mode": "FollowSchedule",  # ZoneMode.FOLLOW_SCHEDULE,
        "state": None,
        "untilTime": None,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"domesticHotWater/{dhw.id}/state"
    assert mock_put.call_args[1] == {"json": MODE}


# Test the Zone APIs...


async def test_zon_mode_reset(
    evohome_v2: EvohomeClient,
) -> None:
    """Test Zone.reset() method."""

    zone = evohome_v2.tcs.zones[0]

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await zone.reset()

    mock_put.assert_awaited_once()

    MODE = {
        "setpointMode": "FollowSchedule",  # ZoneMode.FOLLOW_SCHEDULE,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": MODE}


async def test_zon_mode_set_temperature(
    evohome_v2: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test Zone.set_temperature() method."""

    zone = evohome_v2.tcs.zones[0]

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await zone.set_temperature(19.5)

    mock_put.assert_awaited_once()

    MODE = {
        "setpointMode": "PermanentOverride",  # ZoneMode.PERMANENT_OVERRIDE,
        "heatSetpointValue": 19.5,
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": MODE}

    freezer.move_to("2025-07-10T12:00:00Z")

    with patch("evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put:
        await zone.set_temperature(20.5, until=dt.now(tz=UTC) + td(hours=1))

    mock_put.assert_awaited_once()

    MODE = {
        "setpointMode": "TemporaryOverride",  # ZoneMode.TEMPORARY_OVERRIDE,
        "heatSetpointValue": 20.5,
        "timeUntil": "2025-07-10T13:00:00Z",
    }

    assert mock_put.call_args[0][0] == HTTPMethod.PUT
    assert mock_put.call_args[0][1] == f"temperatureZone/{zone.id}/heatSetpoint"
    assert mock_put.call_args[1] == {"json": MODE}
