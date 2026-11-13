"""Test the v2 GETs that the client uses: the user, their locations, and their status.

  GET /userAccount
  GET /location/installationInfo?userId={usr_id}&includeTemperatureControlSystems=True
  GET /location/{loc_id}/status?includeTemperatureControlSystems=True

setup() GETs the first two (the user's account, for its userId; then the config of all
the user's locations), and Location.get_status() the third (the status of a location,
including that of its gateways, TCSs, zones and DHW). Without
includeTemperatureControlSystems=True, the vendor omits the TCSs (so the client's
schemas would reject the response).

A location may have no gateways (e.g. one newly created), so no TCS: its parsing is
tested in tests/tests (test_client_setup.py, test_v2_location_tcs_none).

The status reports a TCS's until as timeUntil, but a zone's (or a DHW's) as until. Its
datetimes are UTC (with a Z), except a fault's since, which is TZ-naive (the client
takes it as the location's local time), and may be fractional.

As for any URL (see vendor.py):
- an id that is not the user's is a 401 (Unauthorized), as is a bad access token; the
  userAccount URL is open to any authenticated user, so a 401 from it can only be due to
  the token: the client uses that to tell one 401 from the other
- an unknown path is a 404 (HTML); a known path without its required query key is a
  404 (JSON, but without a code)
- too many requests are a 429; the vendor's own failure is a 500
"""

from __future__ import annotations

from datetime import UTC, datetime as dt
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2 import (
    ApiCallErrorReason,
    ApiCallFailedError,
    ApiCallRejectedError,
    ApiRateLimitExceededError,
    ClientStateErrorReason,
    DhwState,
    EvohomeClient as EvohomeClientV2,
    FaultType,
    StaleConfigError,
    SystemMode,
    ZoneMode,
)
from evohomeasync2.main import SCH_USR_ACCOUNT, SCH_USR_LOCATIONS
from evohomeasync2.schemas.const import TccFailureCode
from tests.const import HEADERS_BASE, URL_BASE_V2

from .vendor import (
    DHW_ID,
    GWY_ID,
    HTML_NOT_FOUND,
    LOC_ID,
    LOC_STATUS_OVERRIDDEN,
    NOT_THE_USERS_ID,
    TCS_ID,
    USR_ACCOUNT,
    USR_ID,
    USR_LOCATIONS,
    ZON_ID,
    ZON_ID_2,
)

if TYPE_CHECKING:
    from evohome_cli.auth import TokenCacheManager
    from evohomeasync2 import ControlSystem, HotWater, Location, Zone
    from evohomeasync2.schemas.account import TccFailureResponseT
    from tests.tests.aioresponses import AioResponses


_RETRY_AFTER: Final = 60  # seconds

URL_USR_ACCOUNT = f"{URL_BASE_V2}/userAccount"
URL_USR_LOCATIONS = (
    f"{URL_BASE_V2}/location/installationInfo"
    f"?userId={USR_ID}&includeTemperatureControlSystems=True"
)
URL_LOC_STATUS = (
    f"{URL_BASE_V2}/location/{LOC_ID}/status?includeTemperatureControlSystems=True"
)


async def test_setup(
    credentials_manager: TokenCacheManager,
    mock: AioResponses,
) -> None:
    """setup() GETs the user's account, then (with its userId) their locations."""

    mock.get(URL_USR_ACCOUNT, payload=USR_ACCOUNT)
    mock.get(URL_USR_LOCATIONS, payload=USR_LOCATIONS)

    ec2 = EvohomeClientV2(credentials_manager)
    await ec2.setup()

    headers = HEADERS_BASE | {
        "Authorization": f"bearer {credentials_manager.access_token}"
    }

    assert list(mock.requests) == [  # in this order
        (HTTPMethod.GET, URL_USR_ACCOUNT),
        (HTTPMethod.GET, URL_USR_LOCATIONS),
    ]
    mock.assert_any_call(URL_USR_ACCOUNT, HTTPMethod.GET, headers=headers, json=None)
    mock.assert_any_call(URL_USR_LOCATIONS, HTTPMethod.GET, headers=headers, json=None)

    # the config, as parsed (its keys snake_case, its enums the client's)...
    assert ec2.user_id == USR_ID
    assert [loc.id for loc in ec2.locations] == [LOC_ID]

    loc = ec2.locations[0]
    assert [gwy.id for gwy in loc.gateways] == [GWY_ID]

    tcs = loc.gateways[0].systems[0]
    zon_config = USR_LOCATIONS[0]["gateways"][0]["temperatureControlSystems"][0][
        "zones"
    ]

    assert tcs.id == TCS_ID
    assert SystemMode.AWAY in tcs.allowed_modes
    assert [z.id for z in tcs.zones] == [ZON_ID, ZON_ID_2]
    assert tcs.zones[0].name == "Main Room"
    assert (
        tcs.zones[0].min_heat_setpoint
        == (zon_config[0]["setpointCapabilities"]["minHeatSetpoint"])
    )
    assert tcs.zones[0].allowed_modes == (
        ZoneMode.PERMANENT_OVERRIDE,
        ZoneMode.FOLLOW_SCHEDULE,
        ZoneMode.TEMPORARY_OVERRIDE,
    )

    assert tcs.hotwater is not None
    assert tcs.hotwater.id == DHW_ID
    assert tcs.hotwater.allowed_states == (DhwState.ON, DhwState.OFF)


async def test_get_status(
    loc: Location,
    tcs: ControlSystem,
    zone: Zone,
    dhw: HotWater,
    mock: AioResponses,
) -> None:
    """Location.get_status() GETs its status, and updates that of its entities."""

    mock.get(URL_LOC_STATUS, payload=LOC_STATUS_OVERRIDDEN)

    await loc.get_status()

    mock.assert_called_once_with(URL_LOC_STATUS, HTTPMethod.GET, json=None)

    # the TCS's until is its timeUntil...
    assert tcs.mode == SystemMode.AWAY
    assert tcs.is_permanent is False
    assert tcs.until == dt(2026, 11, 15, tzinfo=UTC)

    zon_status = LOC_STATUS_OVERRIDDEN["gateways"][0]["temperatureControlSystems"][0][
        "zones"
    ][0]

    assert zone.mode == ZoneMode.PERMANENT_OVERRIDE
    assert (
        zone.target_heat_temperature
        == (zon_status["setpointStatus"]["targetHeatTemperature"])
    )
    assert zone.temperature == zon_status["temperatureStatus"]["temperature"]
    assert zone.until is None

    # ...but a DHW's is its until (and so is a zone's)
    assert dhw.mode == ZoneMode.TEMPORARY_OVERRIDE
    assert dhw.state == DhwState.ON
    assert dhw.until == dt(2026, 11, 13, 18, tzinfo=UTC)

    # a fault's since is TZ-naive (so is taken as local time), and may be fractional
    faults = loc.gateways[0].active_faults
    assert [f["fault_type"] for f in faults] == [FaultType.GWY_X_CL]
    assert faults[0]["since"] == dt(2025, 2, 23, 22, 34, 25, 40000, tzinfo=loc.tzinfo)

    # a zone without a temperature (e.g. its sensor is lost) has isAvailable: false
    assert tcs.zones[1].temperature is None


async def test_get_status_location_inaccessible(
    loc: Location,
    mock: AioResponses,
) -> None:
    """A 401 of a location's status, but not of userAccount, is a StaleConfigError.

    That is, the location is no longer the user's (e.g. it was deleted, or unshared),
    as the userAccount URL accepts the access token.
    """

    unauthorized: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.get(URL_LOC_STATUS, status=HTTPStatus.UNAUTHORIZED, payload=unauthorized)
    mock.get(URL_USR_ACCOUNT, payload=USR_ACCOUNT)

    with pytest.raises(StaleConfigError) as err:
        await loc.get_status()

    assert list(mock.requests) == [
        (HTTPMethod.GET, URL_LOC_STATUS),
        (HTTPMethod.GET, URL_USR_ACCOUNT),
    ]
    assert err.value.reason is ClientStateErrorReason.LOCATION_INACCESSIBLE


async def test_get_status_token_rejected(
    loc: Location,
    mock: AioResponses,
) -> None:
    """A 401 of a location's status, and of userAccount too, is raised as is.

    That is, the access token was rejected (and not that the location is not the
    user's): the 401 of a bad token has a different message.
    """

    rejected: list[TccFailureResponseT] = [
        {"code": TccFailureCode.UNAUTHORIZED, "message": "Unauthorized."}
    ]
    mock.get(URL_LOC_STATUS, status=HTTPStatus.UNAUTHORIZED, payload=rejected)
    mock.get(URL_USR_ACCOUNT, status=HTTPStatus.UNAUTHORIZED, payload=rejected)

    with pytest.raises(ApiCallFailedError) as err:
        await loc.get_status()

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}


async def test_get_not_the_users(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """An id that is not the user's is a 401 (Unauthorized).

    The vendor does not say if the id exists (e.g. another user's, or a deleted one's).
    """

    url = (
        "location/installationInfo"
        f"?userId={NOT_THE_USERS_ID}&includeTemperatureControlSystems=True"
    )
    unauthorized: list[TccFailureResponseT] = [
        {
            "code": TccFailureCode.UNAUTHORIZED,
            "message": "You are not allowed to perform this action.",
        }
    ]
    mock.get(
        f"{URL_BASE_V2}/{url}", status=HTTPStatus.UNAUTHORIZED, payload=unauthorized
    )

    with pytest.raises(ApiCallFailedError) as err:
        await ec2.auth.get(url, schema=SCH_USR_LOCATIONS)

    assert err.value.status == HTTPStatus.UNAUTHORIZED
    assert err.value.reason is ApiCallErrorReason.UNAUTHORIZED
    assert err.value.details == {"code": TccFailureCode.UNAUTHORIZED}


async def test_get_unknown_path(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """An unknown path is a 404 (Not Found), whose body is HTML, not JSON."""

    mock.get(
        f"{URL_BASE_V2}/userXxxxxxx",
        status=HTTPStatus.NOT_FOUND,
        body=HTML_NOT_FOUND,
        content_type="text/html",
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec2.auth.get("userXxxxxxx", schema=SCH_USR_ACCOUNT)

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.reason is ApiCallErrorReason.REQUEST_REJECTED
    assert err.value.details == {}  # there is no code, as there is no JSON
    assert "404 - File or directory not found." in err.value.message


async def test_get_without_query_key(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """A known path without its required query key is a 404 (Not Found), as JSON.

    Unlike other errors, its body is a dict (not a list), with no code.
    """

    url = "location/installationInfo?xxxxXx=xxxxxxx"  # i.e. without a userId
    mock.get(
        f"{URL_BASE_V2}/{url}",
        status=HTTPStatus.NOT_FOUND,
        payload={
            "message": "No HTTP resource was found that matches the request URI "
            f"'{URL_BASE_V2}/{url}'."
        },
    )

    with pytest.raises(ApiCallRejectedError) as err:
        await ec2.auth.get(url, schema=SCH_USR_LOCATIONS)

    assert err.value.status == HTTPStatus.NOT_FOUND
    assert err.value.details == {}
    assert "No HTTP resource was found" in err.value.message


async def test_get_rate_limited(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """Too many requests are a 429 (TooManyRequests), maybe with a Retry-After.

    The vendor's message has not been recorded (only its code).
    """

    too_many: list[TccFailureResponseT] = [
        {"code": TccFailureCode.TOO_MANY_REQUESTS, "message": "..."}
    ]
    mock.get(
        URL_USR_ACCOUNT,
        status=HTTPStatus.TOO_MANY_REQUESTS,
        payload=too_many,
        headers={"Retry-After": str(_RETRY_AFTER)},
    )

    with pytest.raises(ApiRateLimitExceededError) as err:
        await ec2.auth.get("userAccount", schema=SCH_USR_ACCOUNT)

    assert err.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert err.value.retry_after == _RETRY_AFTER
    assert err.value.details == {"code": TccFailureCode.TOO_MANY_REQUESTS}


async def test_get_server_error(
    ec2: EvohomeClientV2,
    mock: AioResponses,
) -> None:
    """The vendor's own failure is a 500 (Internal Server Error), as a JSON dict."""

    mock.get(
        URL_USR_ACCOUNT,
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        payload={"message": "An error has occurred."},
    )

    with pytest.raises(ApiCallFailedError) as err:
        await ec2.auth.get("userAccount", schema=SCH_USR_ACCOUNT)

    assert not isinstance(err.value, ApiCallRejectedError)
    assert err.value.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert err.value.reason is ApiCallErrorReason.SERVER_ERROR
    assert err.value.details == {}
