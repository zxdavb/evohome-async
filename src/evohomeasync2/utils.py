#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohomeasync2 provides an async client for the *updated* Evohome API."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime as dt
from io import TextIOWrapper

import click

from . import HotWater, Zone
from .client import EvohomeClient
from .controlsystem import SZ_NAME, SZ_SCHEDULE, ControlSystem
from .schema.account import (
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_REFRESH_TOKEN,
)

# debug flags should be False for end-users
_DEBUG_CLI = False  # for debugging of CLI (*before* loading library)

DEBUG_ADDR = "0.0.0.0"
DEBUG_PORT = 5679

SZ_CACHE_TOKENS = "cache_tokens"
SZ_EVO = "evo"
SZ_USERNAME = "username"

TOKEN_FILE = ".evo-cache.tmp"


_LOGGER = logging.getLogger(__name__)


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


def _check_zone_id(ctx: click.Context, param: click.Option, value: str) -> str:
    """Validate the zone_idx argument is "00" to "11", or "HW"."""

    return value

    # if value.upper() == "HW":
    #     return "HW"

    # if not value.isdigit() or int(value) not in range(0, 12):
    #     raise click.BadParameter("must be '00' to '11', or 'HW'")

    # return f"{int(value):02X}"


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


def _dump_tokens(evo: EvohomeClient) -> None:
    """Dump the tokens to a cache (temporary file)."""

    if evo.access_token_expires:
        expires = evo.access_token_expires.isoformat()
    else:
        expires = None

    with open(TOKEN_FILE, "w") as fp:
        json.dump(
            {
                # SZ_USERNAME: evo.username,
                SZ_REFRESH_TOKEN: evo.refresh_token,
                SZ_ACCESS_TOKEN: evo.access_token,
                SZ_ACCESS_TOKEN_EXPIRES: expires,
            },
            fp,
        )

    _LOGGER.warning("Access tokens cached to: %s", TOKEN_FILE)


def _load_tokens() -> dict[str, dt | str]:
    """Load the tokens from a cache (temporary file)."""

    if not os.path.exists(TOKEN_FILE):
        return {}

    with open(TOKEN_FILE) as f:
        tokens = json.load(f)

    if SZ_ACCESS_TOKEN_EXPIRES not in tokens:
        return tokens  # type: ignore[no-any-return]

    if expires := tokens[SZ_ACCESS_TOKEN_EXPIRES]:
        tokens[SZ_ACCESS_TOKEN_EXPIRES] = dt.fromisoformat(expires)

    return tokens  # type: ignore[no-any-return]


@click.group()
@click.option("--username", "-u", required=True, help="The TCC account username.")
@click.option("--password", "-p", required=True, help="The TCC account password.")
@click.option("--cache-tokens", "-c", is_flag=True, help="Cache of/for access tokens.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(
    ctx: click.Context,
    username: str,
    password: str,
    location: int | None = None,
    cache_tokens: bool | None = None,
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
    ctx.obj[SZ_CACHE_TOKENS] = cache_tokens

    tokens = _load_tokens() if cache_tokens else {}

    ctx.obj[SZ_EVO] = EvohomeClient(
        username,
        password,
        debug=bool(debug),
        **tokens,  # type: ignore[arg-type]
    )


@cli.command()
@click.argument("zone_id", callback=_check_zone_id, type=str)
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
def get_schedule(
    ctx: click.Context, zone_id: str, loc_idx: int, filename: TextIOWrapper
) -> None:
    """Download the schedule of a zone (e.g. "00") or DHW ("HW")."""

    async def get_schedule(
        evo: EvohomeClient, zone_id: str, loc_idx: int | None
    ) -> None:
        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            child: HotWater | Zone = tcs.zones_by_id[zone_id]

            schedule = await child.get_schedule()

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        schedules = {
            child._id: {SZ_NAME: child.name, SZ_SCHEDULE: schedule},
        }

        filename.write(json.dumps(schedules, indent=4))
        filename.write("\r\n\r\n")

    print("\r\nclient.py: Starting backup...")
    evo = ctx.obj[SZ_EVO]

    asyncio.run(get_schedule(evo, zone_id, loc_idx))

    if ctx.obj[SZ_CACHE_TOKENS]:
        _dump_tokens(evo)
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
        filename.write("\r\n\r\n")

    print("\r\nclient.py: Starting backup...")
    evo = ctx.obj[SZ_EVO]

    asyncio.run(get_schedules(evo, loc_idx))

    if ctx.obj[SZ_CACHE_TOKENS]:
        _dump_tokens(evo)
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
    evo = ctx.obj[SZ_EVO]

    asyncio.run(set_schedules(evo, loc_idx))

    if ctx.obj[SZ_CACHE_TOKENS]:
        _dump_tokens(evo)
    print(" - finished.\r\n")


def main() -> None:
    try:
        cli(obj={})  # default for ctx.obj is None

    except click.ClickException as exc:
        print(f"Error: {exc}")
        sys.exit(-1)


if __name__ == "__main__":
    main()
