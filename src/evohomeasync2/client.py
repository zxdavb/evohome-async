#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the *updated* Evohome API."""

import asyncio
import json
import logging
import sys
import tempfile
from datetime import datetime as dt
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Final

import aiofiles
import aiofiles.os
import aiohttp
import asyncclick as click
import debugpy  # type: ignore[import-untyped]

from . import HotWater, Zone, exceptions as exc
from .base import EvohomeClient
from .broker import AbstractTokenManager, _EvoTokenData
from .const import SZ_NAME, SZ_SCHEDULE
from .controlsystem import ControlSystem
from .schema import SZ_ACCESS_TOKEN_EXPIRES

# all _DBG_* flags should be False for published code
_DBG_DEBUG_CLI = False  # for debugging of click

DEBUG_ADDR = "0.0.0.0"  # noqa: S104
DEBUG_PORT = 5679

SZ_CLEANUP: Final = "cleanup"
SZ_EVO: Final = "evo"
SZ_USERNAME: Final = "username"

TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tmp")

_LOGGER: Final = logging.getLogger(__name__)


def _start_debugging(wait_for_client: bool) -> None:
    try:
        debugpy.listen(address=(DEBUG_ADDR, DEBUG_PORT))
    except RuntimeError:
        print(f" - Debugging is already enabled on: {DEBUG_ADDR}:{DEBUG_PORT}")
    else:
        print(f" - Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}")

    if wait_for_client and not debugpy.is_client_connected():
        print("   - execution paused, waiting for debugger to attach...")
        debugpy.wait_for_client()
        print("   - debugger is now attached, continuing execution.")


if _DBG_DEBUG_CLI:
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


async def _write(filename: TextIOWrapper | Any, content: str) -> None:
    """Write to a file, async if possible and sync otherwise."""

    try:
        async with aiofiles.open(filename, "w") as fp:  # type: ignore[call-overload]
            await fp.write(content)
    except TypeError:  # if filename is sys.stdout:
        filename.write(content)


class TokenManager(AbstractTokenManager):
    """A token manager that uses a cache file to store the tokens."""

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        /,
        *,
        token_cache: Path = TOKEN_CACHE,
    ) -> None:
        super().__init__(username, password, websession)

        self._token_cache = token_cache

    @property
    def token_cache(self) -> str:
        """Return the token cache path."""
        return str(self._token_cache)

    async def restore_access_token(self) -> None:
        """Load the tokens from a cache (temporary file).

        Reset the token data if the cache is not found, or is for a different user.
        """

        self._token_data_reset()

        try:
            async with aiofiles.open(self._token_cache) as fp:
                content = await fp.read()
        except FileNotFoundError:
            return

        # allow to fail if json.JSONDecodeError:
        tokens_cache: dict[str, _EvoTokenData] = json.loads(content)

        if tokens := tokens_cache.get(self.username):
            self._token_data_from_dict(tokens)

    async def save_access_token(self) -> None:
        """Dump the tokens to a cache (temporary file)."""

        try:
            async with aiofiles.open(self._token_cache) as fp:
                content = await fp.read()
        except FileNotFoundError:
            content = "{}"

        try:
            token_cache = json.loads(content)
        except json.JSONDecodeError:
            token_cache = {}

        # remove any expired tokens
        token_cache = {
            k: v
            for k, v in token_cache.items()
            if v[SZ_ACCESS_TOKEN_EXPIRES] > dt.now().isoformat()
        }

        content = json.dumps(
            token_cache | {self.username: self._token_data_as_dict()}, indent=4
        )

        async with aiofiles.open(self._token_cache, "w") as fp:
            await fp.write(content)


@click.group()
@click.option("--username", "-u", required=True, help="The TCC account username.")
@click.option("--password", "-p", required=True, help="The TCC account password.")
@click.option("--cache-tokens", "-c", is_flag=True, help="Load the token cache.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
async def cli(
    ctx: click.Context,
    username: str,
    password: str,
    cache_tokens: bool | None = None,
    debug: bool | None = None,
) -> None:
    """A demonstration CLI for the evohomeasync2 client library."""

    if debug:  # Do first
        _start_debugging(True)

    async def cleanup(
        session: aiohttp.ClientSession,
        token_manager: TokenManager,
    ) -> None:
        """Close the web session and save the access token to the cache."""

        await session.close()
        await token_manager.save_access_token()

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    websession = aiohttp.ClientSession()  # timeout=aiohttp.ClientTimeout(total=30))
    token_manager = TokenManager(
        username, password, websession, token_cache=TOKEN_CACHE
    )

    if cache_tokens:  # restore cached tokens, if any
        await token_manager.restore_access_token()

    evo = EvohomeClient(token_manager, websession, debug=bool(debug))

    try:
        await evo.login()
    except exc.AuthenticationFailed:
        await websession.close()
        raise

    # TODO: use a typed dict for ctx.obj
    ctx.obj[SZ_EVO] = evo
    ctx.obj[SZ_CLEANUP] = cleanup(websession, token_manager)


@cli.command()
@click.option(  # --loc-idx
    "--loc-idx",
    "-l",
    callback=_check_positive_int,
    default=0,
    type=int,
    help="The location idx.",
)
@click.pass_context
async def mode(ctx: click.Context, loc_idx: int) -> None:
    """Retrieve the system mode."""

    print("\r\nclient.py: Retrieving the system mode...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    await _write(
        sys.stdout, "\r\n" + str(_get_tcs(evo, loc_idx).system_mode) + "\r\n\r\n"
    )

    await ctx.obj[SZ_CLEANUP]
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
async def dump(ctx: click.Context, loc_idx: int, filename: TextIOWrapper) -> None:
    """Download all the global config and the location status."""

    print("\r\nclient.py: Starting dump of config and status...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    result = {
        "config": evo.installation_info,
        "status": await evo.locations[loc_idx].refresh_status(),
    }

    await _write(filename, json.dumps(result, indent=4) + "\r\n\r\n")

    await ctx.obj[SZ_CLEANUP]
    print(" - finished.\r\n")


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
async def get_schedule(
    ctx: click.Context, zone_id: str, loc_idx: int, filename: TextIOWrapper
) -> None:
    """Download the schedule of a zone of a TCS (WIP)."""

    print("\r\nclient.py: Starting backup of zone schedule (WIP)...")
    evo = ctx.obj[SZ_EVO]

    zon: HotWater | Zone = _get_tcs(evo, loc_idx).zones_by_id[zone_id]
    schedule = {zon.id: {SZ_NAME: zon.name, SZ_SCHEDULE: await zon.get_schedule()}}

    await _write(filename, json.dumps(schedule, indent=4) + "\r\n\r\n")

    await ctx.obj[SZ_CLEANUP]
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
async def get_schedules(
    ctx: click.Context, loc_idx: int, filename: TextIOWrapper
) -> None:
    """Download all the schedules from a TCS."""

    print("\r\nclient.py: Starting backup of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    schedules = await _get_tcs(evo, loc_idx).get_schedules()

    await _write(filename, json.dumps(schedules, indent=4) + "\r\n\r\n")

    await ctx.obj[SZ_CLEANUP]
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
async def set_schedules(
    ctx: click.Context, loc_idx: int, filename: TextIOWrapper
) -> None:
    """Upload schedules to a TCS."""

    print("\r\nclient.py: Starting restore of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    # will TypeError if filename is sys.stdin
    async with aiofiles.open(filename) as fp:  # type: ignore[call-overload]
        content = await fp.read()

    success = await _get_tcs(evo, loc_idx).set_schedules(json.loads(content))

    await ctx.obj[SZ_CLEANUP]
    print(f" - finished{'' if success else ' (with errors)'}.\r\n")


def main() -> None:
    """Run the CLI."""

    try:
        asyncio.run(cli(obj={}))  # default for ctx.obj is None

    except click.ClickException as err:
        print(f"Error: {err}")
        sys.exit(-1)


if __name__ == "__main__":
    main()
