"""Test the active faults of a v2 entity (e.g. a TCS), as given by its status.

The vendor's activeFaults is a list of faults (each its faultType and since): an entity
logs each one when it becomes active, and when it is cleared.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from evohomeasync2.const import SZ_FAULT_TYPE, SZ_SINCE, FaultType
from tests.common import get_tcs

from .conftest import FIXTURES_V2 as FIXTURES

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient
    from evohomeasync2.typedefs import EvoActiveFaultT


FAULT: Final[EvoActiveFaultT] = {
    SZ_FAULT_TYPE: FaultType.SYS_B_CL,
    SZ_SINCE: dt(2026, 11, 15, 12, 0, tzinfo=UTC),
}


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "fixture_folder" not in metafunc.fixturenames:
        return

    folders = [Path(FIXTURES) / "default"]

    if missing := [p for p in folders if not p.is_dir()]:
        raise pytest.fail(
            f"Missing fixture folder(s): {', '.join(str(p) for p in missing)}"
        )

    metafunc.parametrize(
        "fixture_folder", sorted(folders), ids=(p.name for p in sorted(folders))
    )


async def test_duplicate_fault(
    ec2: EvohomeClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a fault listed twice is one fault: active once, then cleared once."""

    tcs = get_tcs(ec2)
    tcs._update_faults([])  # i.e. none (whatever the fixture has)
    caplog.clear()
    caplog.set_level(logging.INFO)  # a fault is cleared at INFO

    tcs._update_faults([FAULT, FAULT.copy()])  # the same fault, twice

    faults = tcs.active_faults  # (if not a local, mypy would narrow it for good)
    assert faults == (FAULT,)
    assert [r.message for r in caplog.records].count(
        f"{tcs}: Active fault: {FAULT[SZ_SINCE].isoformat()} {FAULT[SZ_FAULT_TYPE]}"
    ) == 1

    tcs._update_faults([])  # it is cleared (was: a KeyError)

    assert tcs.active_faults == ()
    assert [r.message for r in caplog.records].count(
        f"{tcs}: Fault cleared: {FAULT[SZ_SINCE].isoformat()} {FAULT[SZ_FAULT_TYPE]}"
    ) == 1
