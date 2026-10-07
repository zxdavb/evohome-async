"""Helpers for both the offline tests (tests/tests) and the real-API tests (tests_rf)."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from tests.const import TEST_LOC_IDX

if TYPE_CHECKING:
    import evohomeasync as evo0
    import evohomeasync2 as evo2


@overload
def get_loc(evo: evo0.EvohomeClient) -> evo0.Location: ...


@overload
def get_loc(evo: evo2.EvohomeClient) -> evo2.Location: ...


def get_loc(
    evo: evo0.EvohomeClient | evo2.EvohomeClient,
) -> evo0.Location | evo2.Location:
    """Return the Location object to test against (see TEST_LOC_IDX)."""
    return evo.locations[TEST_LOC_IDX]


def get_tcs(evo: evo2.EvohomeClient) -> evo2.ControlSystem:
    """Return the first TCS of the location to test against (v2 only).

    The v1 API has no TCS: its zones/DHW belong to the location (see get_loc()).
    """
    return get_loc(evo).gateways[0].systems[0]


def get_dhw(evo: evo2.EvohomeClient) -> evo2.HotWater | None:
    """Return the first DHW object found across all TCSs of the location under test."""
    for gwy in get_loc(evo).gateways:
        for tcs in gwy.systems:
            if tcs.hotwater:
                return tcs.hotwater
    return None


def get_zon(evo: evo2.EvohomeClient) -> evo2.Zone | None:
    """Return the first Zone object found across all TCSs of the location under test."""
    for gwy in get_loc(evo).gateways:
        for tcs in gwy.systems:
            if tcs.zones:
                return tcs.zones[0]
    return None
