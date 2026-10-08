"""Validate how the vendor interprets the end of a zone's temporary override.

A zone's temporary override ends at a datetime: its NextTime (v0 API), or its timeUntil
(v2 API). These tests confirm how the vendor interprets each, by setting an override via
one API and reading it back via both:
  - v2: setpointStatus.until (of the zone's status) is in UTC, with a Z (this is taken
    as the reference, as it is the instant that HA displays, and it has not been
    reported as wrong)
  - v0: heatSetpoint.nextTime (of the zone's changeableValues) is without a Z

Expected (as documented in test_v0_urls.py):
  - v2: a timeUntil is UTC: so the until (v2) is as sent, and the nextTime (v0) is the
    same instant, but in the location's local time (and without a Z)
  - v0: a NextTime is the location's local time, and its Z (if any) is ignored: so the
    nextTime (v0) is as sent (but without a Z), and the until (v2) is that local time
    in UTC (i.e. earlier than sent, by the location's UTC offset)

So, the v2 client sends a timeUntil in UTC (with a Z, see as_utc_str()), but the v0
client sends a NextTime in the location's local time (see as_local_str()). Between
v2.0.0 and v3.0.0, the v0 client sent it in UTC, so (e.g. in BST) its override was
ended early by the location's UTC offset. test_v0_client_until() confirms that the v0
client's override now ends at the instant given.

The two interpretations differ only if the location's UTC offset is not zero (e.g. the
UK in summer), and so the tests are skipped otherwise.

Each test overrides a live zone to its current setpoint (so is a no-op in practice), and
then reverts it to its schedule, and waits until it is (see _revert()).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime as dt, timedelta as td
from http import HTTPMethod
from typing import TYPE_CHECKING, Any

import pytest

from _evohome.helpers import TCC_DTM_STRFTIME
from evohomeasync.schemas import TCC_GET_USR_LOCS
from evohomeasync2.schemas.status import TCC_GET_ZON_STATUS
from tests.common import get_loc
from tests.const import _DBG_USE_REAL_AIOHTTP, TEST_LOC_IDX

from .common import (
    is_alive_v0,
    is_zone_v0,
    should_work_v0,
    should_work_v2,
    skipif_auth_failed,
    status_of_v0,
    task_id_v0,
    wait_for_comm_task_v0,
)

if TYPE_CHECKING:
    from evohomeasync import EvohomeClient as EvohomeClientV0
    from evohomeasync.schemas import TccDeviceResponseT, TccLocationResponseT
    from evohomeasync2 import EvohomeClient as EvohomeClientV2


_LOCAL_STRFTIME = "%Y-%m-%dT%H:%M:%S"  # as a v0 nextTime (i.e. without a Z)
_STATUS_INTERVAL = 3  # seconds, between polls of the status
_STATUS_TIMEOUT = 120  # seconds, as the gateway can take a while to apply a change


async def _get_location(evo: EvohomeClientV0) -> TccLocationResponseT:
    """Return the (vendor-cased) location under test, via v0."""

    usr_id: int = evo.user_account["user_id"]

    url = f"locations?userId={usr_id}&allData=True"
    locs = await should_work_v0(evo.auth, HTTPMethod.GET, url, schema=TCC_GET_USR_LOCS)

    return locs[TEST_LOC_IDX]


async def _get_zone(evo: EvohomeClientV0, zon_id: int) -> TccDeviceResponseT:
    """Return the (vendor-cased) zone, via v0."""
    return next(
        d for d in (await _get_location(evo))["devices"] if d["deviceID"] == zon_id
    )


async def _setup(
    evo0: EvohomeClientV0,
    evo2: EvohomeClientV2,
) -> tuple[int, float, td, dt]:
    """Return a live zone's id & setpoint, the location's UTC offset, and the hour.

    The zone must be following its schedule, else the test is skipped. It is also
    skipped if the location's UTC offset is zero, as then UTC and local time are the
    same (so the expected behaviour can't be confirmed).
    """

    if not _DBG_USE_REAL_AIOHTTP:
        pytest.skip("Mocked server not implemented for this test")

    await evo0.update()  # get user_id
    await evo2.setup()  # needed by should_work_v2()

    loc = await _get_location(evo0)

    offset = td(minutes=loc["timeZone"]["currentOffsetMinutes"])
    if not offset:
        pytest.skip("The location's UTC offset is zero (so is the same as local time)")

    zone = next(
        (
            d
            for d in loc["devices"]
            if is_zone_v0(d) and is_alive_v0(d) and status_of_v0(d) == "Scheduled"
        ),
        None,
    )
    if zone is None:
        pytest.skip("No live zone found that is following its schedule")

    values: dict[str, Any] = dict(zone["thermostat"]["changeableValues"])
    setpoint: float = values["heatSetpoint"]["value"]

    now = dt.now(tz=UTC).replace(minute=0, second=0, microsecond=0)  # on the hour

    return zone["deviceID"], setpoint, offset, now


async def _get_next_time(evo: EvohomeClientV0, zon_id: int) -> str | None:
    """Return the nextTime of a zone's override, via v0 (it is without a Z)."""

    values: dict[str, Any] = dict(
        (await _get_zone(evo, zon_id))["thermostat"]["changeableValues"]
    )
    next_time: str | None = values["heatSetpoint"].get("nextTime")
    return next_time


async def _get_setpoint_status(evo: EvohomeClientV2, zon_id: int) -> dict[str, Any]:
    """Return the setpointStatus of a zone, via v2."""

    url = f"temperatureZone/{zon_id}/status"
    status = await should_work_v2(
        evo.auth, HTTPMethod.GET, url, schema=TCC_GET_ZON_STATUS
    )

    return dict(status["setpointStatus"])


async def _get_until(evo: EvohomeClientV2, zon_id: int) -> str | None:
    """Return the until of a zone's override, via v2 (it is UTC, with a Z)."""

    until: str | None = (await _get_setpoint_status(evo, zon_id)).get("until")
    return until


async def _wait_for_until(
    evo: EvohomeClientV2, zon_id: int, previous: str | None
) -> str | None:
    """Poll a zone (via v2) until the until of its override changes, and return it.

    Returns the last-seen until (not necessarily a new one), so that the caller can
    assert against it and get a useful failure message.
    """

    until: str | None = previous

    try:
        async with asyncio.timeout(_STATUS_TIMEOUT):
            while True:
                if (until := await _get_until(evo, zon_id)) != previous:
                    return until

                await asyncio.sleep(_STATUS_INTERVAL)

    except TimeoutError:
        return until


async def _is_following_schedule(evo: EvohomeClientV2, zon_id: int) -> bool:
    """Poll a zone (via v2) until it follows its schedule, and return True if it does."""

    try:
        async with asyncio.timeout(_STATUS_TIMEOUT):
            while True:
                status = await _get_setpoint_status(evo, zon_id)
                if status["setpointMode"] == "FollowSchedule":
                    return True

                await asyncio.sleep(_STATUS_INTERVAL)

    except TimeoutError:
        return False


async def _revert(
    evo0: EvohomeClientV0,
    evo2: EvohomeClientV2,
    zon_id: int,
) -> None:
    """Revert a zone to its schedule, and wait until it is.

    The vendor sometimes answers a PUT with the comm task of an earlier, equivalent PUT,
    and then does not apply it (see is_stale_task_v0() in common.py), e.g. if another
    test has just sent a revert. So, the revert is sent via v2, and if that is not
    applied, then via v0.
    """

    url = f"temperatureZone/{zon_id}/heatSetpoint"
    json: dict[str, object] = {"setpointMode": "FollowSchedule"}

    await should_work_v2(evo2.auth, HTTPMethod.PUT, url, json=json)
    if await _is_following_schedule(evo2, zon_id):
        return

    url = f"devices/{zon_id}/thermostat/changeableValues/heatSetpoint"
    json = {"status": "Scheduled", "value": None, "nextTime": None}

    rsp = await should_work_v0(evo0.auth, HTTPMethod.PUT, url, json=json)
    await wait_for_comm_task_v0(evo0.auth, task_id_v0(rsp))

    assert await _is_following_schedule(evo2, zon_id), "Unable to revert the zone"


# PUT /devices/{zone_id}/thermostat/changeableValues/heatSetpoint (NextTime)
@skipif_auth_failed
async def test_v0_next_time(
    evohome_v0: EvohomeClientV0,
    evohome_v2: EvohomeClientV2,
) -> None:
    """Test a v0 NextTime is the location's local time (and that any Z is ignored).

    Each override is sent with a NextTime that is a UTC time on the hour: with a Z (as
    this library sends it) or without one. Either way, the vendor is expected to treat
    it as the location's local time. So:
      - the nextTime (v0) is as sent, but without its Z
      - the until (v2) is that local time in UTC, i.e. it is earlier than the instant
        that was sent (with a Z) by the location's UTC offset (e.g. an hour in BST)

    For example, in BST: a NextTime of "2026-10-08T21:00:00Z" (22:00 local) gives a
    nextTime of "2026-10-08T21:00:00" and an until of "2026-10-08T20:00:00Z".
    """

    zon_id, setpoint, offset, now = await _setup(evohome_v0, evohome_v2)

    url = f"devices/{zon_id}/thermostat/changeableValues/heatSetpoint"
    until: str | None = await _get_until(evohome_v2, zon_id)  # None, as Scheduled

    try:
        for hours, suffix in (
            (2, "Z"),  # with a Z (as this library)
            (3, ""),  # without a Z
        ):
            sent = now + td(hours=hours)  # on the hour (so not rounded)
            next_time = sent.strftime(_LOCAL_STRFTIME) + suffix

            json = {"value": setpoint, "status": "Temporary", "nextTime": next_time}
            rsp = await should_work_v0(evohome_v0.auth, HTTPMethod.PUT, url, json=json)
            await wait_for_comm_task_v0(evohome_v0.auth, task_id_v0(rsp))

            until = await _wait_for_until(evohome_v2, zon_id, until)

            # the nextTime is as sent, but without any Z (as it's in local time)...
            assert await _get_next_time(evohome_v0, zon_id) == sent.strftime(
                _LOCAL_STRFTIME
            ), json

            # ...and so the until is earlier than the instant sent (if it had a Z)
            assert until == (sent - offset).strftime(TCC_DTM_STRFTIME), json

    finally:
        await _revert(evohome_v0, evohome_v2, zon_id)


# PUT /temperatureZone/{zone_id}/heatSetpoint (timeUntil)
@skipif_auth_failed
async def test_v2_time_until(
    evohome_v0: EvohomeClientV0,
    evohome_v2: EvohomeClientV2,
) -> None:
    """Test a v2 timeUntil is UTC (as is the until of the zone's status).

    The override is sent with a timeUntil that is a UTC time on the hour, with a Z (as
    this library sends it). The vendor is expected to treat it as UTC. So:
      - the until (v2) is as sent
      - the nextTime (v0) is that instant in the location's local time (without a Z)

    For example, in BST: a timeUntil of "2026-10-08T21:00:00Z" gives an until of
    "2026-10-08T21:00:00Z" and a nextTime of "2026-10-08T22:00:00".
    """

    zon_id, setpoint, offset, now = await _setup(evohome_v0, evohome_v2)

    url = f"temperatureZone/{zon_id}/heatSetpoint"
    until: str | None = await _get_until(evohome_v2, zon_id)  # None, as Scheduled

    try:
        sent = now + td(hours=2)  # on the hour (so not rounded)
        time_until = sent.strftime(TCC_DTM_STRFTIME)  # with a Z (as this library)

        json = {
            "setpointMode": "TemporaryOverride",
            "heatSetpointValue": setpoint,
            "timeUntil": time_until,
        }
        await should_work_v2(evohome_v2.auth, HTTPMethod.PUT, url, json=json)

        until = await _wait_for_until(evohome_v2, zon_id, until)

        # the until is as sent (as it's in UTC)...
        assert until == time_until, json

        # ...and the nextTime is that instant, but in local time
        assert await _get_next_time(evohome_v0, zon_id) == (sent + offset).strftime(
            _LOCAL_STRFTIME
        ), json

    finally:
        await _revert(evohome_v0, evohome_v2, zon_id)


# via the v0 client: Zone.set_temperature(..., until=...)
@skipif_auth_failed
async def test_v0_client_until(
    evohome_v0: EvohomeClientV0,
    evohome_v2: EvohomeClientV2,
) -> None:
    """Test the v0 client's Zone.set_temperature() ends its override when it should.

    The until is an aware (UTC) datetime on the hour. The client sends it as a NextTime
    in the location's local time, so:
      - the until (v2) is the same instant (in UTC)
      - the nextTime (v0) is that instant in the location's local time (without a Z)

    For example, in BST: an until of 21:00 UTC is sent as a NextTime of 22:00 (local),
    and so gives an until (v2) of 21:00 UTC (but gave 20:00 UTC before v3.0.0).
    """

    zon_id, setpoint, offset, now = await _setup(evohome_v0, evohome_v2)

    zone = get_loc(evohome_v0).zone_by_id[str(zon_id)]
    until: str | None = await _get_until(evohome_v2, zon_id)  # None, as Scheduled

    try:
        sent = now + td(hours=2)  # on the hour (so not rounded)

        await zone.set_temperature(setpoint, until=sent)

        until = await _wait_for_until(evohome_v2, zon_id, until)

        # the until is the instant sent...
        assert until == sent.strftime(TCC_DTM_STRFTIME)

        # ...and the nextTime is that instant, but in local time
        assert await _get_next_time(evohome_v0, zon_id) == (sent + offset).strftime(
            _LOCAL_STRFTIME
        )

    finally:
        await _revert(evohome_v0, evohome_v2, zon_id)
