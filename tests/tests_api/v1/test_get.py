"""Test the v1 GETs that the client uses: the user, and their locations (with status).

  GET /accountInfo
  GET /locations?userId={usr_id}&allData=True

setup() GETs both (the user's account, for its userID; then all the user's locations,
with their devices: in v1, a location's config and status are the one response), and
get_status() GETs the second again. With allData=True, each location has its devices,
and each device its thermostat (with its changeableValues); without it, the vendor
omits them (see test_get_device.py).

The ids are ints (the client keeps them as strs), and are cased inconsistently (e.g.
userID, locationID, deviceID, but a device's gatewayId). A device's indoorTemperature
is 128.0 if it has none (its indoorTemperatureStatus is then not Measured): e.g. a lost
zone (its isAlive is false). A device's thermostatModelType is a str (e.g. EMEA_ZONE,
DOMESTIC_HOT_WATER), but some (e.g. a Honeywell TH9320WF3003) send an int. Its datetimes (e.g. a nextTime) are the location's local
time, without a Z.

As for any URL (see vendor.py), an id that is not the user's is a 401; an unknown path
is a 404 (HTML), as is a GET of a PUT-only URL; a known path without its required
query key is a 404 (JSON, but without a code).
"""

from __future__ import annotations

from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING

import pytest

from evohomeasync import (
    ApiCallErrorReason,
    ApiCallFailedError,
    ApiCallRejectedError,
    EvohomeClient as EvohomeClientV1,
)
from evohomeasync.main import SCH_GET_ACCOUNT_INFO, SCH_GET_ACCOUNT_LOCS
from evohomeasync.schemas import TccFailureCode
from tests.const import HEADERS_BASE, URL_BASE_V1

from .vendor import (
    DHW_ID,
    HTML_NOT_FOUND,
    LOC_ID,
    NOT_THE_USERS_ID,
    USR_ID,
    USR_INFO,
    USR_LOCS,
    ZON_ID,
    ZON_ID_2,
)

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync import ControlSystem
    from evohomeasync.schemas import TccFailureResponseT
    from tests.tests.aioresponses import AioResponses


URL_ACCOUNT_INFO = f"{URL_BASE_V1}/accountInfo"
URL_LOCATIONS = f"{URL_BASE_V1}/locations?userId={USR_ID}&allData=True"


async def test_setup(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """setup() GETs the user's account, then (with its userID) their locations."""

    mock.get(URL_ACCOUNT_INFO, payload=USR_INFO)
    mock.get(URL_LOCATIONS, payload=USR_LOCS)

    ec1 = EvohomeClientV1(credentials_manager)
    await ec1.setup()

    headers = HEADERS_BASE | {"sessionId": credentials_manager.session_id}

    assert list(mock.requests) == [  # in this order
        (HTTPMethod.GET, URL_ACCOUNT_INFO),
        (HTTPMethod.GET, URL_LOCATIONS),
    ]
    mock.assert_any_call(URL_ACCOUNT_INFO, HTTPMethod.GET, headers=headers, json=None)
    mock.assert_any_call(URL_LOCATIONS, HTTPMethod.GET, headers=headers, json=None)

    # the config, as parsed (its int ids are kept as strs)...
    assert ec1.user_id == str(USR_ID)
    assert [loc.id for loc in ec1.locations] == [str(LOC_ID)]

    tcs = ec1.locations[0].tcs
    assert tcs is not None
    assert [z.id for z in tcs.zones] == [str(ZON_ID), str(ZON_ID_2)]
    assert tcs.hotwater is not None
    assert tcs.hotwater.id == str(DHW_ID)


async def test_get_status(
    ec1: EvohomeClientV1,
    tcs: ControlSystem,
    mock: AioResponses,
) -> None:
    """get_status() GETs the user's locations (again), but not their account.

    A device's indoorTemperature is 128.0 if it has none (e.g. a lost zone).
    """

    mock.get(URL_LOCATIONS, payload=USR_LOCS)

    temps = await tcs.get_temperatures()  # calls get_status()

    mock.assert_called_once_with(URL_LOCATIONS, HTTPMethod.GET, json=None)

    zon_dev = USR_LOCS[0]["devices"][1]  # its 128.0 is not available
    assert temps == {
        str(ZON_ID): zon_dev["thermostat"]["indoorTemperature"],
        str(ZON_ID_2): None,
    }
    assert ec1.location_by_id[str(LOC_ID)].weather is not None


async def test_get_not_the_users(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401 (Unauthorized).

    Its message differs from that of a bad session id ("Unauthorized"). The client
    probes accountInfo, to tell it from a 401 of the session id.
    """

    url = f"locations?userId={NOT_THE_USERS_ID}&allData=True"
    # provenance: probed 2026-11-13
    body: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.get(f"{URL_BASE_V1}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=body)
    mock.get(URL_ACCOUNT_INFO, payload=USR_INFO)  # the client's probe

    with pytest.raises(ApiCallFailedError) as err:
        await ec1.auth.get(url, schema=SCH_GET_ACCOUNT_LOCS)

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED


async def test_get_unknown_path(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """An unknown path is a 404 (Not Found), whose body is HTML, not JSON."""

    mock.get(
        f"{URL_BASE_V1}/xxxxxxx",
        status=HTTPStatus.NOT_FOUND,
        body=HTML_NOT_FOUND,
        content_type="text/html",
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec1.auth.get("xxxxxxx", schema=SCH_GET_ACCOUNT_INFO)

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.details == {}  # there is no code, as there is no JSON
    assert "404 - File or directory not found." in err.value.message


async def test_get_without_query_key(
    ec1: EvohomeClientV1,
    mock: AioResponses,
) -> None:
    """A known path without its required query key is a 404 (Not Found), as JSON."""

    url = f"locations?noSuchKey={USR_ID}"  # i.e. without a userId
    mock.get(
        f"{URL_BASE_V1}/{url}",
        status=HTTPStatus.NOT_FOUND,
        payload={
            "message": "No HTTP resource was found that matches the request URI "
            f"'{URL_BASE_V1}/{url}'."
        },
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec1.auth.get(url, schema=SCH_GET_ACCOUNT_LOCS)

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.details == {}
