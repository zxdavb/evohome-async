"""Tests for evohome-async - the status JSON must be consistent with the config JSON.

Every entity known from the config (gateway, TCS, DHW, zone) should be in the status. If
one is not, a warning is logged (the others are still updated). The converse is
tolerated: entities in the status, but not in the config, are only logged.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import probatio as vol
import pytest

from evohomeasync2 import exceptions as exc
from evohomeasync2.const import (
    SZ_DHW,
    SZ_GATEWAYS,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
    SZ_ZONE_ID,
    SZ_ZONES,
)
from evohomeasync2.schemas.const import (
    S2_GATEWAYS,
    S2_TEMPERATURE_CONTROL_SYSTEMS,
    S2_ZONES,
)
from evohomeasync2.schemas.status import factory_loc_status
from tests.common import get_loc

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


def test_tcs_status_requires_zones(
    fixture_folder: Path,
) -> None:
    """A TCS status with no zones should fail validation, as does its config."""

    (status_file,) = fixture_folder.glob("status_*.json")
    status = json.loads(status_file.read_text())

    SCH_STATUS = factory_loc_status()
    _ = SCH_STATUS(status)  # the unaltered fixture is valid

    status[S2_GATEWAYS][0][S2_TEMPERATURE_CONTROL_SYSTEMS][0][S2_ZONES] = []

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
    ("mutate", "entity", "is_updated"),
    [
        (_drop_gateway, "gateway_id", False),
        (_drop_tcs, "system_id", False),
        (_drop_dhw, "dhw_id", True),
        (_drop_zone, "zone_id", True),
    ],
    ids=["gateway", "tcs", "dhw", "zone"],
)
async def test_status_missing_known_entity(
    evohome_v2: EvohomeClient,
    *,
    mutate: Callable[[EvoLocStatusResponseT], None],
    entity: str,
    is_updated: bool,
) -> None:
    """A status that omits a configured entity should raise, after updating the rest."""

    loc = get_loc(evohome_v2)
    zone = loc.gateways[0].systems[0].zones[0]  # is never the one dropped

    status = await loc._get_status(_update=False)
    mutate(status)

    zone._status = None

    with pytest.raises(exc.StaleConfigError, match=entity):
        loc._update_status(status)

    assert (zone._status is not None) is is_updated


async def test_status_missing_known_entity_warns_once(
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A status that omits a configured entity should log a warning, but only once."""

    loc = get_loc(evohome_v2)

    status = await loc._get_status(_update=False)
    stale_status = await loc._get_status(_update=False)
    _drop_zone(stale_status)

    def warnings() -> list[str]:
        return [r.message for r in caplog.records if r.levelno == logging.WARNING]

    with caplog.at_level(logging.WARNING):
        with patch("evohomeasync2.auth.Auth.get", AsyncMock(return_value=stale_status)):
            await loc.update()
            await loc.update()

        (warning,) = warnings()  # i.e. is logged only once
        assert "has no entry for zone_id=" in warning

        with patch("evohomeasync2.auth.Auth.get", AsyncMock(return_value=status)):
            await loc.update()  # the entity is back, so no warning

        assert warnings() == [warning]

        with patch("evohomeasync2.auth.Auth.get", AsyncMock(return_value=stale_status)):
            await loc.update()  # the entity is absent again, so warn again

        assert warnings() == [warning, warning]


async def test_status_missing_known_entity_raises_if_asked(
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A status that omits a configured entity should raise, if asked to do so."""

    loc = get_loc(evohome_v2)
    zone = loc.gateways[0].systems[0].zones[0]  # is never the one dropped

    stale_status = await loc._get_status(_update=False)
    _drop_zone(stale_status)

    with (
        caplog.at_level(logging.WARNING),
        patch("evohomeasync2.auth.Auth.get", AsyncMock(return_value=stale_status)),
    ):
        zone._status = None

        with pytest.raises(exc.StaleConfigError, match="zone_id="):
            await loc.update(raise_on_stale_config=True)

        _ = zone.status  # the others were updated before the raise (else would raise)

        with pytest.raises(exc.StaleConfigError, match="zone_id="):
            await loc.get_status(raise_on_stale_config=True)

        with pytest.raises(exc.StaleConfigError, match="zone_id="):
            await evohome_v2.update(raise_on_stale_config=True)

    assert not caplog.records  # it is raised, and not logged


async def test_status_unknown_entity_is_tolerated(
    evohome_v2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A status that has an entity absent from the config should only log a warning."""

    loc = get_loc(evohome_v2)
    tcs = loc.gateways[0].systems[0]

    status = await loc._get_status(_update=False)
    zones = status[SZ_GATEWAYS][0][SZ_TEMPERATURE_CONTROL_SYSTEMS][0][SZ_ZONES]
    zones.append(zones[0] | {SZ_ZONE_ID: "9999999"})

    loc._update_status(status)

    assert "zone_id='9999999' not known" in caplog.text
    assert len(tcs.zones) == len(zones) - 1


_UNAUTHORIZED = exc.ApiCallFailedError(
    "GET url: 401 Unauthorized", status=HTTPStatus.UNAUTHORIZED
)
_NO_CONNECTION = exc.ApiCallFailedError("GET url: Connection refused")
_SERVER_ERROR = exc.ApiCallFailedError(
    "GET url: 500 Internal Server Error", status=HTTPStatus.INTERNAL_SERVER_ERROR
)
_BAD_RESPONSE = exc.BadApiResponseError("GET url: response failed validation: ...")


@pytest.mark.parametrize(
    ("account_error", "expected"),
    [
        (None, exc.StaleConfigError),  # the access token is OK, so: no such location
        (_UNAUTHORIZED, exc.ApiCallFailedError),  # the access token was rejected
        (_NO_CONNECTION, exc.ApiCallFailedError),  # can't tell
        (_SERVER_ERROR, exc.ApiCallFailedError),  # can't tell
        (_BAD_RESPONSE, exc.ApiCallFailedError),  # can't tell
    ],
    ids=[
        "location_absent",
        "token_rejected",
        "no_connection",
        "server_error",
        "bad_response",
    ],
)
async def test_location_absent(
    evohome_v2: EvohomeClient,
    account_error: exc.EvohomeError | None,
    expected: type[exc.EvohomeError],
) -> None:
    """A 401 from the location's status is StaleConfigError, if the token is OK.

    Otherwise (the token was rejected, or that can't be determined), it is the 401.
    """

    loc = get_loc(evohome_v2)

    def get(url: str, schema: object) -> object:
        if url != "userAccount":  # i.e. is the location's status
            raise _UNAUTHORIZED
        if account_error:
            raise account_error
        return {}

    with (
        patch("evohomeasync2.auth.Auth.get", AsyncMock(side_effect=get)),
        pytest.raises(expected) as err,
    ):
        await loc.update()

    assert type(err.value) is expected
    if expected is not exc.StaleConfigError:
        assert err.value is _UNAUTHORIZED  # the original 401, not the probe's error
