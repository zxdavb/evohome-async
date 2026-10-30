"""Helpers for both the offline tests (tests/tests) and the real-API tests (tests_rf)."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import pytest

from tests.const import _DBG_USE_REAL_AIOHTTP, TEST_LOC_ID

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import evohomeasync as evo1
    import evohomeasync2 as evo2
    from evohomeasync.schemas import TccLocationResponseT
    from evohomeasync2.schemas.config import (
        TccGwyConfigResponseT,
        TccLocConfigResponseT,
        TccTcsConfigResponseT,
    )


def _select_loc[T](
    locs: Sequence[T],
    loc_id: Callable[[T], str],
) -> T:
    """Return the location under test from a user's list of locations.

    Against the vendor's servers, that is the location whose id is TEST_LOC_ID, if set,
    else the user's only location: if they have more than one, fail the test, as their
    v1 and v2 lists of locations may not be in the same order.

    Offline, it is the first location (raise IndexError if there is none), as the v1
    and v2 data are not mixed.
    """

    if not _DBG_USE_REAL_AIOHTTP:
        return locs[0]

    if TEST_LOC_ID is None:
        if len(locs) != 1:
            pytest.fail(f"The user has {len(locs)} locations: set TEST_LOC_ID")
        return locs[0]

    for loc in locs:
        if loc_id(loc) == TEST_LOC_ID:
            return loc
    pytest.fail(f"The user has no location with id {TEST_LOC_ID} (see TEST_LOC_ID)")


@overload
def get_loc(
    ec: evo1.EvohomeClient,
) -> evo1.Location: ...


@overload
def get_loc(
    ec: evo2.EvohomeClient,
) -> evo2.Location: ...


def get_loc(
    ec: evo1.EvohomeClient | evo2.EvohomeClient,
) -> evo1.Location | evo2.Location:
    """Return the Location object to test against (see _select_loc())."""
    locs: Sequence[evo1.Location | evo2.Location] = ec.locations
    return _select_loc(locs, lambda loc: loc.id)


@overload
def get_tcs(
    ec: evo1.EvohomeClient,
) -> evo1.ControlSystem: ...


@overload
def get_tcs(
    ec: evo2.EvohomeClient,
) -> evo2.ControlSystem: ...


def get_tcs(
    ec: evo1.EvohomeClient | evo2.EvohomeClient,
) -> evo1.ControlSystem | evo2.ControlSystem:
    """Return the TCS of the location to test against.

    Raise IndexError if it has no TCS.
    """
    if (tcs := get_loc(ec).tcs) is None:
        raise IndexError("The location under test has no TCS")
    return tcs


def get_dhw(
    ec2: evo2.EvohomeClient,
) -> evo2.HotWater | None:
    """Return the first DHW object found across all TCSs of the location under test."""
    for gwy in get_loc(ec2).gateways:
        for tcs in gwy.systems:
            if tcs.hotwater:
                return tcs.hotwater
    return None


def get_zon(
    ec2: evo2.EvohomeClient,
    idx: int = 0,
) -> evo2.Zone | None:
    """Return a Zone object of the location under test (by default, its first).

    The zones are counted across all the TCSs of the location. Return None if it has
    no such zone (i.e. fewer than idx + 1 zones).
    """
    zones = [
        z for gwy in get_loc(ec2).gateways for tcs in gwy.systems for z in tcs.zones
    ]
    return zones[idx] if idx < len(zones) else None


def find_loc_v1(
    locs: Sequence[TccLocationResponseT],
) -> TccLocationResponseT:
    """Return the (vendor-cased) v1 JSON of the location under test.

    The locs are as per GET /locations?userId={usr_id}&allData=True.
    """
    return _select_loc(locs, lambda loc: str(loc["locationID"]))


def find_loc_config(
    usr_locs: Sequence[TccLocConfigResponseT],
) -> TccLocConfigResponseT:
    """Return the (vendor-cased) v2 config of the location under test.

    The usr_locs are as per GET /location/installationInfo?userId={usr_id}&include...
    """
    return _select_loc(usr_locs, lambda loc: loc["locationInfo"]["locationId"])


def find_gwy_config(
    loc_config: TccLocConfigResponseT,
) -> TccGwyConfigResponseT | None:
    """Return the (vendor-cased) v2 config of the location's gateway, or None.

    A location has 0-1 gateways (see evo2.Location.tcs).
    """
    return next(iter(loc_config["gateways"]), None)


def find_tcs_config(
    loc_config: TccLocConfigResponseT,
) -> TccTcsConfigResponseT | None:
    """Return the (vendor-cased) v2 config of the location's TCS, or None.

    A location has 0-1 gateways, each with 0-1 TCSs (see evo2.Location.tcs).
    """
    return next(
        (
            tcs
            for gwy in loc_config["gateways"]
            for tcs in gwy["temperatureControlSystems"]
        ),
        None,
    )
