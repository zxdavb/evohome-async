"""Tests for evohome-async - ControlSystem mode edge cases.

Older systems do not support all system modes, and some modes have been renamed in
newer systems. These tests check that the client handles these cases correctly, falling
back to appropriate alternatives where possible and raising errors where not.
"""

from __future__ import annotations

from http import HTTPMethod
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

import evohomeasync2 as evo2
from evohomeasync2.schemas.const import SystemMode

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient


# Fixtures with old/new system modes to test fallback and error handling logic
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [Path(FIXTURES) / name for name in ("default", "hass_118169")]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_ctl_reset_emulates_auto_with_reset(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.reset() should emulate `AutoWithReset` if it is unavailable."""

    tcs = evohome_v2.tcs

    zone_mocks: list[AsyncMock] = []
    for zone in tcs.zones:
        zone.reset = AsyncMock()  # type: ignore[method-assign]
        zone_mocks.append(zone.reset)

    dhw_mock: AsyncMock | None = None
    if tcs.hotwater is not None:
        tcs.hotwater.reset = AsyncMock()  # type: ignore[method-assign]
        dhw_mock = tcs.hotwater.reset

    with (
        patch.object(tcs, "set_auto", new_callable=AsyncMock) as mock_set_auto,
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
    ):
        await tcs.reset()

    if SystemMode.AUTO_WITH_RESET in tcs.allowed_modes:
        url = f"temperatureControlSystem/{tcs.id}/mode"
        mode = {
            "systemMode": str(SystemMode.AUTO_WITH_RESET),
            "permanent": True,
        }

        mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)
        mock_set_auto.assert_not_awaited()

        for mock_zone_reset in zone_mocks:
            mock_zone_reset.assert_not_awaited()

        if dhw_mock is not None:
            dhw_mock.assert_not_awaited()

    else:
        mock_set_auto.assert_awaited_once()
        mock_put.assert_not_awaited()

        for mock_zone_reset in zone_mocks:
            mock_zone_reset.assert_awaited_once()

        if dhw_mock is not None:
            dhw_mock.assert_awaited_once()


async def test_ctl_set_auto_falls_back_to_heat(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_auto() should use `Heat` if `Auto` is unavailable."""

    tcs = evohome_v2.tcs

    expected_mode = (
        SystemMode.AUTO if SystemMode.AUTO in tcs.allowed_modes else SystemMode.HEAT
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": str(expected_mode),
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await tcs.set_auto()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_heatingoff_falls_back_to_off(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_heatingoff() should use `Off` if `HeatingOff` is unavailable."""

    tcs = evohome_v2.tcs

    expected_mode = (
        SystemMode.OFF
        if SystemMode.OFF in tcs.allowed_modes
        else SystemMode.HEATING_OFF
    )

    url = f"temperatureControlSystem/{tcs.id}/mode"
    mode = {
        "systemMode": str(expected_mode),
        "permanent": True,
    }

    with patch(
        "_evohome.auth.AbstractAuth.request", new_callable=AsyncMock
    ) as mock_put:
        await tcs.set_heatingoff()

    mock_put.assert_awaited_once_with(HTTPMethod.PUT, url, json=mode)


async def test_ctl_set_mode_rejects_unsupported_mode(
    evohome_v2: EvohomeClient,
) -> None:
    """ControlSystem.set_mode() should reject modes not supported by the current TCS."""

    tcs = evohome_v2.tcs

    for system_mode in SystemMode:
        if system_mode not in tcs.allowed_modes:
            break
    else:
        pytest.skip("TCS supports all system modes!")

    with (
        patch("_evohome.auth.AbstractAuth.request", new_callable=AsyncMock) as mock_put,
        pytest.raises(evo2.InvalidSystemModeError),
    ):
        await tcs.set_mode(system_mode)

    mock_put.assert_not_awaited()
