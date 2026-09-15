"""Tests for evohome-async - the status JSON must be consistent with the config JSON.

Every entity known from the config (gateway, TCS, DHW, zone) must be in the status. The
converse is tolerated: entities in the status, but not in the config, are only logged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import probatio as vol
import pytest

import evohomeasync2 as evo2
from evohomeasync2.const import (
    SZ_DHW,
    SZ_GATEWAYS,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_ZONE_ID,
    SZ_ZONES,
)
from evohomeasync2.schemas.status import factory_loc_status

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from collections.abc import Callable

    from evohomeasync2 import EvohomeClient
    from evohomeasync2.typedefs import EvoLocStatusResponseT


# A fixture with a single location, gateway & TCS that has both zones and a DHW
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    folders = [Path(FIXTURES) / "default"]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


def test_tcs_status_requires_zones(fixture_folder: Path) -> None:
    """A TCS status with no zones should fail validation, as does its config."""

    (status_file,) = fixture_folder.glob("status_*.json")
    status = json.loads(status_file.read_text())

    SCH_STATUS = factory_loc_status()
    _ = SCH_STATUS(status)  # the unaltered fixture is valid

    status["gateways"][0]["temperatureControlSystems"][0]["zones"] = []

    with pytest.raises(vol.Invalid):
        SCH_STATUS(status)


def _drop_gateway(status: EvoLocStatusResponseT) -> None:
    status[SZ_GATEWAYS].clear()


def _drop_tcs(status: EvoLocStatusResponseT) -> None:
    status[SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS].clear()


def _drop_dhw(status: EvoLocStatusResponseT) -> None:
    del status[SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0][SZ_DHW]


def _drop_zone(status: EvoLocStatusResponseT) -> None:
    status[SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0][SZ_ZONES].pop()


@pytest.mark.parametrize(
    ("mutate", "entity"),
    [
        (_drop_gateway, "gateway_id"),
        (_drop_tcs, "system_id"),
        (_drop_dhw, "dhw_id"),
        (_drop_zone, "zone_id"),
    ],
    ids=["gateway", "tcs", "dhw", "zone"],
)
async def test_status_missing_known_entity_raises(
    evohome_v2: EvohomeClient,
    mutate: Callable[[EvoLocStatusResponseT], None],
    entity: str,
) -> None:
    """A status that omits a configured entity should raise, and update nothing."""

    loc = evohome_v2.locations[0]
    tcs = loc.gateways[0].systems[0]
    zone_status_before = tcs.zones[0].status

    status = await loc._get_status(_update=False)
    mutate(status)

    with pytest.raises(evo2.BadConfigError, match=entity):
        loc._update_status(status)

    assert tcs.zones[0].status is zone_status_before


async def test_status_unknown_entity_is_tolerated(
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A status that has an entity absent from the config should only log a warning."""

    loc = evohome_v2.locations[0]
    tcs = loc.gateways[0].systems[0]

    status = await loc._get_status(_update=False)
    zones = status[SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0][SZ_ZONES]
    zones.append(zones[0] | {SZ_ZONE_ID: "9999999"})

    loc._update_status(status)

    assert "zone_id='9999999' not known" in caplog.text
    assert len(tcs.zones) == len(zones) - 1
