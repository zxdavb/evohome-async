"""Test the v2 GETs of each entity's config and status (most unused by the client).

  GET /location/{loc_id}/installationInfo[?includeTemperatureControlSystems=True]
  GET /location/{loc_id}/status  (without includeTemperatureControlSystems=True)
  GET /gateway/{gwy_id}/installationInfo[?includeTemperatureControlSystems=True]
  GET /gateway/{gwy_id}/status[?includeTemperatureControlSystems=True]
  GET /temperatureControlSystem/{tcs_id}/installationInfo
  GET /temperatureControlSystem/{tcs_id}/status
  GET /temperatureZone/{zon_id}/installationInfo
  GET /temperatureZone/{zon_id}/status
  GET /domesticHotWater/{dhw_id}/installationInfo
  GET /domesticHotWater/{dhw_id}/status

The client gets the config and status of every entity from those of its location (see
test_get.py), so it calls only three of these URLs, and those only via methods it
keeps for testing: Location._get_config() (to update its time zone), and
Zone/HotWater._get_status(). The rest are called here via Auth.get() (or, if the
client has no schema for the response, Auth.request()), to document them.

Each entity's installationInfo (or status) is the same object as is nested within that
of its parent (so shares its schema). Those of a TCS always include its zones and DHW;
those of a location or gateway include its TCSs only if
includeTemperatureControlSystems=True (so the client's schemas, which require the TCSs,
would reject them otherwise).

An id that is the user's, but of another type of entity, is a 400 whose code names
the type that was expected (e.g. a TCS's id as a zone's: TemperatureZoneNotFound). One
that is not the user's is a 401 (see test_get.py).
"""

from __future__ import annotations

import logging
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from _evohome.helpers import Case
from evohomeasync2 import ApiCallRejectedError, ControlSystem, Gateway, HotWater, Zone
from evohomeasync2.location import Location
from evohomeasync2.schemas.config import (
    factory_dhw_config,
    factory_gwy_config,
    factory_tcs_config,
    factory_zon_config,
)
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import URL_BASE_V2

from .vendor import (
    DHW_CONFIG,
    DHW_ID,
    DHW_STATUS,
    GWY_CONFIG,
    GWY_CONFIG_SANS_TCSS,
    GWY_ID,
    GWY_STATUS,
    GWY_STATUS_SANS_TCSS,
    LOC_CONFIG,
    LOC_CONFIG_SANS_TCSS,
    LOC_ID,
    LOC_STATUS_SANS_TCSS,
    TCS_CONFIG,
    TCS_ID,
    TCS_STATUS,
    ZON_CONFIG,
    ZON_ID,
    ZON_STATUS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from _evohome.helpers import Validator
    from evohomeasync2 import EvohomeClient as EvohomeClientV2
    from evohomeasync2.schemas.account import TccFailureResponseT
    from tests.tests.aioresponses import AioResponses


@pytest.mark.parametrize(
    ("url", "payload", "schema", "id_key", "id_"),
    [
        pytest.param(
            f"location/{LOC_ID}/installationInfo?includeTemperatureControlSystems=True",
            LOC_CONFIG,
            Location.SCH_CONFIG,
            "location_info",
            None,
            id="loc_config",
        ),
        pytest.param(
            f"gateway/{GWY_ID}/installationInfo?includeTemperatureControlSystems=True",
            GWY_CONFIG,
            factory_gwy_config(Case.PYTHONIC),
            "gateway_info",
            None,
            id="gwy_config",
        ),
        pytest.param(
            f"gateway/{GWY_ID}/status?includeTemperatureControlSystems=True",
            GWY_STATUS,
            Gateway.SCH_STATUS,
            "gateway_id",
            GWY_ID,
            id="gwy_status",
        ),
        pytest.param(
            f"temperatureControlSystem/{TCS_ID}/installationInfo",
            TCS_CONFIG,
            factory_tcs_config(Case.PYTHONIC),
            "system_id",
            TCS_ID,
            id="tcs_config",
        ),
        pytest.param(
            f"temperatureControlSystem/{TCS_ID}/status",
            TCS_STATUS,
            ControlSystem.SCH_STATUS,
            "system_id",
            TCS_ID,
            id="tcs_status",
        ),
        pytest.param(
            f"temperatureZone/{ZON_ID}/installationInfo",
            ZON_CONFIG,
            factory_zon_config(Case.PYTHONIC),
            "zone_id",
            ZON_ID,
            id="zon_config",
        ),
        pytest.param(
            f"temperatureZone/{ZON_ID}/status",
            ZON_STATUS,
            Zone.SCH_STATUS,
            "zone_id",
            ZON_ID,
            id="zon_status",
        ),
        pytest.param(
            f"domesticHotWater/{DHW_ID}/installationInfo",
            DHW_CONFIG,
            factory_dhw_config(Case.PYTHONIC),
            "dhw_id",
            DHW_ID,
            id="dhw_config",
        ),
        pytest.param(
            f"domesticHotWater/{DHW_ID}/status",
            DHW_STATUS,
            HotWater.SCH_STATUS,
            "dhw_id",
            DHW_ID,
            id="dhw_status",
        ),
    ],
)
async def test_get(
    *,  # keyword-only, as pytest passes them by name
    ec2: EvohomeClientV2,
    mock: AioResponses,
    url: str,
    payload: Mapping[str, object],
    schema: Validator[Mapping[str, object]],
    id_key: str,
    id_: str | None,
) -> None:
    """The config (installationInfo) or status of an entity is a 200.

    Its keys are snake_cased by Auth.get(), and it passes the client's schema.
    """

    mock.get(f"{URL_BASE_V2}/{url}", payload=payload)

    result = await ec2.auth.get(url, schema=schema)

    mock.assert_called_once_with(f"{URL_BASE_V2}/{url}", HTTPMethod.GET, json=None)
    assert id_key in result
    if id_ is not None:
        assert result[id_key] == id_


@pytest.mark.parametrize(
    ("url", "payload"),
    [
        pytest.param(
            f"location/{LOC_ID}/installationInfo",
            LOC_CONFIG_SANS_TCSS,
            id="loc_config",
        ),
        pytest.param(
            f"location/{LOC_ID}/status", LOC_STATUS_SANS_TCSS, id="loc_status"
        ),
        pytest.param(
            f"gateway/{GWY_ID}/installationInfo", GWY_CONFIG_SANS_TCSS, id="gwy_config"
        ),
        pytest.param(f"gateway/{GWY_ID}/status", GWY_STATUS_SANS_TCSS, id="gwy_status"),
    ],
)
async def test_get_sans_tcss(
    ec2: EvohomeClientV2,
    mock: AioResponses,
    url: str,
    payload: dict[str, object],
) -> None:
    """Without includeTemperatureControlSystems=True, there are no TCSs.

    The client has no schema for such a response, so it is got via Auth.request().
    """

    mock.get(f"{URL_BASE_V2}/{url}", payload=payload)

    result = await ec2.auth.request(HTTPMethod.GET, url)

    mock.assert_called_once_with(f"{URL_BASE_V2}/{url}", HTTPMethod.GET, json=None)
    assert isinstance(result, dict)
    assert "temperature_control_systems" not in str(result)


async def test_location_get_config(
    loc: Location,
    mock: AioResponses,
) -> None:
    """Location._get_config() GETs its installationInfo (with its TCSs).

    Only its time zone (and its use of DST) is updated from it.
    """

    url = f"{URL_BASE_V2}/location/{LOC_ID}/installationInfo"
    url += "?includeTemperatureControlSystems=True"

    mock.get(url, payload=LOC_CONFIG)

    result = await loc._get_config()

    mock.assert_called_once_with(url, HTTPMethod.GET, json=None)
    assert result["location_info"]["location_id"] == LOC_ID
    assert loc.config["time_zone"]["time_zone_id"] == "GMTStandardTime"


async def test_zone_get_status(
    zone: Zone,
    mock: AioResponses,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Zone._get_status() GETs its status (and warns that it is less efficient)."""

    url = f"{URL_BASE_V2}/temperatureZone/{ZON_ID}/status"

    mock.get(url, payload=ZON_STATUS)

    with caplog.at_level(logging.WARNING):
        result = await zone._get_status()

    mock.assert_called_once_with(url, HTTPMethod.GET, json=None)
    assert result["zone_id"] == ZON_ID
    assert zone.temperature == ZON_STATUS["temperatureStatus"]["temperature"]
    assert "prefer Location.get_status()" in caplog.text


async def test_dhw_get_status(
    dhw: HotWater,
    mock: AioResponses,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """HotWater._get_status() GETs its status (and warns that it is less efficient)."""

    url = f"{URL_BASE_V2}/domesticHotWater/{DHW_ID}/status"

    mock.get(url, payload=DHW_STATUS)

    with caplog.at_level(logging.WARNING):
        result = await dhw._get_status()

    mock.assert_called_once_with(url, HTTPMethod.GET, json=None)
    assert result["dhw_id"] == DHW_ID
    assert "prefer Location.get_status()" in caplog.text


@pytest.mark.parametrize(
    ("url", "code", "message"),
    [
        pytest.param(  # a TCS's id, as a zone's
            f"temperatureZone/{TCS_ID}/status",
            TccFailureCode.TEMPERATURE_ZONE_NOT_FOUND,
            f"Temperature Zone {TCS_ID} not found.",
            id="zon_status",
        ),
        pytest.param(  # a zone's id, as a DHW's
            f"domesticHotWater/{ZON_ID}/status",
            TccFailureCode.DHW_NOT_FOUND,
            f"Domestic Hot Water {ZON_ID} not found.",
            id="dhw_status",
        ),
    ],
)
async def test_get_id_of_another_type(
    ec2: EvohomeClientV2,
    mock: AioResponses,
    url: str,
    code: TccFailureCode,
    message: str,
) -> None:
    """An id that is the user's, but of another type of entity, is a 400."""

    body: list[TccFailureResponseT] = [{"code": code, "message": message}]
    mock.get(f"{URL_BASE_V2}/{url}", status=HTTPStatus.BAD_REQUEST, payload=body)

    with pytest.raises(ApiCallRejectedError) as err:
        await ec2.auth.request(HTTPMethod.GET, url)

    assert err.value.status == HTTPStatus.BAD_REQUEST
    assert err.value.details == {"code": code}
    assert message in err.value.message
