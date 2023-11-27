#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the *updated* Evohome API.

It is (largely) a faithful port of https://github.com/watchforstock/evohome-client

Further information at: https://evohome-client.readthedocs.io
"""

import asyncio
import json
import logging
import sys
from io import TextIOWrapper

import click

from .broker import Broker  # noqa: F401
from .client import EvohomeClient  # noqa: F401
from .controlsystem import ControlSystem  # noqa: F401
from .exceptions import (  # noqa: F401
    AuthenticationFailed,
    DeprecationError,
    EvohomeError,
    InvalidParameter,
    InvalidSchedule,
    InvalidSchema,
    NoSingleTcsError,
    RateLimitExceeded,
    RequestFailed,
)
from .gateway import Gateway  # noqa: F401
from .hotwater import HotWater  # noqa: F401
from .location import Location  # noqa: F401
from .zone import Zone  # noqa: F401

__version__ = "0.4.12"


# debug flags should be False for end-users
_DEBUG_CLI = False  # for debugging of CLI (*before* loading library)

DEBUG_ADDR = "0.0.0.0"
DEBUG_PORT = 5679

SZ_EVO = "evo"


def _start_debugging(wait_for_client: bool) -> None:
    import debugpy  # type: ignore[import-untyped]

    debugpy.listen(address=(DEBUG_ADDR, DEBUG_PORT))
    print(f" - Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}")

    if wait_for_client:
        print("   - execution paused, waiting for debugger to attach...")
        debugpy.wait_for_client()
        print("   - debugger is now attached, continuing execution.")


if _DEBUG_CLI:
    _start_debugging(True)


def _check_zone_idx(ctx: click.Context, param: click.Option, value: str) -> str:
    """Validate the zone_idx argument is "00" to "11", or "HW"."""

    if value.upper() == "HW":
        return "HW"

    if not value.isdigit() or int(value) not in range(0, 12):
        raise click.BadParameter("must be '00' to '11', or 'HW'")

    return f"{int(value):02X}"


def _check_positive_int(ctx: click.Context, param: click.Option, value: int) -> int:
    """Validate the parameter is a positive int."""

    if value < 0:
        raise click.BadParameter("must >= 0")

    return value


def _get_tcs(evo: EvohomeClient, loc_idx: int | None) -> ControlSystem:
    """Get the ControlSystem object for the specified location idx."""

    if loc_idx is None:
        return evo._get_single_tcs()

    return evo.locations[int(loc_idx)]._gateways[0]._control_systems[0]


@click.group()
@click.option("--username", "-u", required=True, help="The TCC account username.")
@click.option("--password", "-p", required=True, help="The TCC account password.")
@click.option("--location", "-l", help="The location idx to use.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(
    ctx: click.Context,
    username: str,
    password: str,
    location: int | None = None,
    debug: bool | None = None,
) -> None:
    # if debug:  # Do first
    #     _start_debugging(True)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    ctx.obj = ctx.obj or {}  # may be None

    ctx.obj[SZ_EVO] = EvohomeClient(username, password, debug=bool(debug))


@cli.command()
@click.option(  # --loc-idx
    "--loc-idx",
    "-l",
    callback=_check_positive_int,
    default=0,
    type=int,
    help="The location idx.",
)
@click.option(  # --filename
    "--filename", "-f", type=click.File("w"), default="-", help="The output file."
)
@click.pass_context
def get_schedules(ctx: click.Context, loc_idx: int, filename: TextIOWrapper) -> None:
    """Download the schedule of a zone (e.g. "00") or DHW ("HW")."""

    async def get_schedules(evo: EvohomeClient, loc_idx: int | None) -> None:
        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            schedules = await tcs._get_schedules()

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        filename.write(json.dumps(schedules, indent=4))

    print("\r\nclient.py: Starting backup...")

    asyncio.run(get_schedules(ctx.obj[SZ_EVO], loc_idx))

    print(" - finished.\r\n")


@cli.command()
@click.option(  # --loc-idx
    "--loc-idx",
    "-l",
    callback=_check_positive_int,
    default=0,
    type=int,
    help="The location idx.",
)
@click.option("--filename", "-f", type=click.File(), help="The input file.")
@click.pass_context
def set_schedules(ctx: click.Context, loc_idx: int, filename: TextIOWrapper) -> None:
    """Upload a schedule for a zone (e.g. "00") or DHW ("HW")."""

    async def set_schedules(evo: EvohomeClient, loc_idx: int | None) -> bool:
        schedules = json.loads(filename.read())

        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            success = await tcs._set_schedules(schedules)

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        return success

    print("\r\nclient.py: Starting restore...")
    asyncio.run(set_schedules(ctx.obj[SZ_EVO], loc_idx))
    print(" - finished.\r\n")


def main() -> None:
    try:
        cli(obj={})  # default for ctx.obj is None

    except click.ClickException as exc:
        print(f"Error: {exc}")
        sys.exit(-1)


if __name__ == "__main__":
    main()
