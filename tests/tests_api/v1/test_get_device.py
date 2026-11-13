"""Test the other v1 GETs (of a location, its gateways and devices): unused by the client.

  GET /locations?userId={usr_id}                     (i.e. without allData=True)
  GET /locations?locationId={loc_id}[&allData=True]
  GET /gateways?locationId={loc_id}[&allData=True]
  GET /devices?locationId={loc_id}[&allData=True]
  GET /devices/{dev_id}
  GET /devices/{dev_id}/thermostat
  GET /devices/{dev_id}/thermostat/changeableValues

The client gets everything from GET /locations?userId={usr_id}&allData=True (see
test_get.py), so it calls none of these, and has no schemas for them: they are called
here via Auth.request(), which returns the response with its keys snake_cased.

Each is as per the object nested within the user's locations, with or without its
children (allData=True adds them):
- a location: its devices and oneTouchButtons (and its weather, and its contractor, if
  it has them); locations?locationId= returns a dict, not a list of one
- a gateway: its devices (the gateway's id is gatewayID, but its location's locationId)
- a device: its thermostat and alertSettings; a device's own URL has no allData param
  (so is without them)
- a thermostat: as nested, but without its changeableValues
- changeableValues: as nested, but with the source of each change made via the API
  (e.g. modeChangeSource, and, a zone's, heatSetpointChangeSource), for a live device
  (it has been seen absent for a lost one)

A GET of .../changeableValues/heatSetpoint is a 404 (HTML), as it is PUT-only.
"""

from __future__ import annotations

from http import HTTPMethod
from typing import TYPE_CHECKING

import pytest

from tests.const import URL_BASE_V1

from .vendor import (
    DEVICES,
    DEVICES_SANS_ALL_DATA,
    GATEWAYS,
    GATEWAYS_ALL_DATA,
    LOC_ID,
    LOCATION,
    LOCATION_SANS_ALL_DATA,
    USR_ID,
    ZON_CHANGEABLE_VALUES,
    ZON_ID,
    ZON_THERMOSTAT,
)

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient as EvohomeClientV1
    from tests.tests.aioresponses import AioResponses


@pytest.mark.parametrize(
    ("url", "payload", "keys"),
    [
        pytest.param(
            f"locations?userId={USR_ID}",
            [LOCATION_SANS_ALL_DATA],
            {"location_id", "time_zone"},
            id="locations_by_user",
        ),
        pytest.param(
            f"locations?locationId={LOC_ID}&allData=True",
            LOCATION,
            {"location_id", "devices", "one_touch_buttons", "weather", "contractor"},
            id="location_all_data",
        ),
        pytest.param(
            f"locations?locationId={LOC_ID}",
            LOCATION_SANS_ALL_DATA,
            {"location_id", "time_zone"},
            id="location",
        ),
        pytest.param(
            f"gateways?locationId={LOC_ID}",
            GATEWAYS,
            {"gateway_id", "mac", "location_id", "is_redlink_gateway"},
            id="gateways",
        ),
        pytest.param(
            f"gateways?locationId={LOC_ID}&allData=True",
            GATEWAYS_ALL_DATA,
            {"gateway_id", "devices"},
            id="gateways_all_data",
        ),
        pytest.param(
            f"devices?locationId={LOC_ID}&allData=True",
            DEVICES,
            {"device_id", "gateway_id", "thermostat", "alert_settings"},
            id="devices_all_data",
        ),
        pytest.param(
            f"devices?locationId={LOC_ID}",
            DEVICES_SANS_ALL_DATA,
            {"device_id", "gateway_id", "is_alive"},
            id="devices",
        ),
        pytest.param(
            f"devices/{ZON_ID}",
            DEVICES_SANS_ALL_DATA[1],
            {"device_id", "thermostat_model_type", "is_alive"},
            id="device",
        ),
        pytest.param(
            f"devices/{ZON_ID}/thermostat",
            ZON_THERMOSTAT,
            {"indoor_temperature", "outdoot_humidity_available"},  # sic
            id="thermostat",
        ),
        pytest.param(
            f"devices/{ZON_ID}/thermostat/changeableValues",
            ZON_CHANGEABLE_VALUES,
            {"mode", "heat_setpoint", "heat_setpoint_change_source"},
            id="changeable_values",
        ),
    ],
)
async def test_get(
    ec1: EvohomeClientV1,
    mock: AioResponses,
    url: str,
    payload: object,
    keys: set[str],
) -> None:
    """Each GET is a 200 (its keys are snake_cased by Auth.request())."""

    mock.get(f"{URL_BASE_V1}/{url}", payload=payload)

    result = await ec1.auth.request(HTTPMethod.GET, url)

    mock.assert_called_once_with(f"{URL_BASE_V1}/{url}", HTTPMethod.GET, json=None)

    entity = result[0] if isinstance(result, list) else result
    assert isinstance(entity, dict)
    assert keys <= set(entity)


async def test_get_sans_all_data(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """Without allData=True, the children of each entity are omitted."""

    mock.get(
        f"{URL_BASE_V1}/devices?locationId={LOC_ID}", payload=DEVICES_SANS_ALL_DATA
    )

    result = await ec1.auth.request(HTTPMethod.GET, f"devices?locationId={LOC_ID}")

    assert isinstance(result, list)
    assert all("thermostat" not in d for d in result)
