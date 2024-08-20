#!/usr/bin/env python3
"""evohomeasync2 provides an async client for the *updated* Evohome API."""

import asyncio
import json
import logging
import sys
import tempfile
from io import TextIOWrapper
from pathlib import Path
from typing import Final

import aiofiles
import aiofiles.os
import aiohttp
import asyncclick as click

from . import HotWater, Zone
from .base import EvohomeClient
from .broker import AbstractTokenManager, _EvoTokenData
from .const import SZ_NAME, SZ_SCHEDULE
from .controlsystem import ControlSystem
from .schema import (
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    SZ_REFRESH_TOKEN,
    _EvoDictT,
)
from .schema.schedule import _ScheduleT

# all _DBG_* flags should be False for published code
_DBG_DEBUG_CLI = False  # for debugging of CLI (*before* loading EvohomeClient library)

DEBUG_ADDR = "0.0.0.0"
DEBUG_PORT = 5679

SZ_CACHE_TOKENS: Final = "cache_tokens"
SZ_EVO: Final = "evo"
SZ_TOKEN_MANAGER: Final = "token_manager"
SZ_USERNAME: Final = "username"
SZ_WEBSESSION: Final = "websession"

TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tmp")

_LOGGER: Final = logging.getLogger(__name__)


def _start_debugging(wait_for_client: bool) -> None:
    import debugpy  # type: ignore[import-untyped]

    debugpy.listen(address=(DEBUG_ADDR, DEBUG_PORT))
    print(f" - Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}")

    if wait_for_client:
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

    async def fetch_access_token(self) -> None:  # HA api
        """If required, fetch an (updated) access token (somehow).

        If there is a valid cached token use that, otherwise fetch via the web API.
        """

        if self.is_token_data_valid():
            return

        await self._load_access_token()

        if not self.is_token_data_valid():
            await super().fetch_access_token()
            await self.save_access_token(None)

    async def _load_access_token(self) -> None:
        """Load the tokens from a cache (temporary file)."""

        self._token_data_reset()

        try:
            async with aiofiles.open(self._token_cache) as fp:
                content = await fp.read()
        except FileNotFoundError:
            return

        try:
            tokens: _EvoTokenData = json.loads(content)
        except json.JSONDecodeError:
            return

        if tokens.pop(SZ_USERNAME) == self.username:
            self._token_data_from_dict(tokens)

    async def save_access_token(self, evo: EvohomeClient | None) -> None:  # type: ignore[override]
        """Dump the tokens to a cache (temporary file)."""

        content = json.dumps(
            {SZ_USERNAME: self.username} | self._token_data_as_dict(evo)
        )

        async with aiofiles.open(self._token_cache, "w") as fp:
            await fp.write(content)


@click.group()
@click.option("--username", "-u", required=True, help="The TCC account username.")
@click.option("--password", "-p", required=True, help="The TCC account password.")
@click.option("--cache-tokens", "-c", is_flag=True, help="Use a token cache.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
async def cli(
    ctx: click.Context,
    username: str,
    password: str,
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

    ctx.obj[SZ_WEBSESSION] = websession = (
        aiohttp.ClientSession()
    )  # timeout=aiohttp.ClientTimeout(total=30))

    ctx.obj[SZ_TOKEN_MANAGER] = token_manager = TokenManager(
        username, password, websession, token_cache=TOKEN_CACHE
    )

    if not cache_tokens:
        tokens = {}
    else:
        await token_manager._load_access_token()  # not: fetch_access_token()
        tokens = {
            SZ_ACCESS_TOKEN: token_manager.access_token,
            SZ_ACCESS_TOKEN_EXPIRES: token_manager.access_token_expires,
            SZ_REFRESH_TOKEN: token_manager.refresh_token,
        }

    ctx.obj[SZ_EVO] = EvohomeClient(
        username,
        password,
        **tokens,  # type: ignore[arg-type]
        session=websession,
        debug=bool(debug),
    )


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

    async def get_state(evo: EvohomeClient, loc_idx: int) -> _EvoDictT:
        try:
            await evo.login()

            status = await evo.locations[loc_idx].refresh_status()

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        return {
            "config": evo.installation_info,
            "status": status,
        }

    print("\r\nclient.py: Starting dump of config and status...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    result = await get_state(evo, loc_idx)
    content = json.dumps(result, indent=4) + "\r\n\r\n"

    async with aiofiles.open(filename, "w") as fp:
        await fp.write(content)

    await ctx.obj[SZ_TOKEN_MANAGER].save_access_token(ctx.obj[SZ_EVO])
    result = await ctx.obj[SZ_WEBSESSION].close()
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

    async def get_schedule(
        evo: EvohomeClient, zone_id: str, loc_idx: int | None
    ) -> _ScheduleT:
        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            child: HotWater | Zone = tcs.zones_by_id[zone_id]

            schedule = await child.get_schedule()

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        return {child._id: {SZ_NAME: child.name, SZ_SCHEDULE: schedule}}

    print("\r\nclient.py: Starting backup of zone schedule (WIP)...")
    evo = ctx.obj[SZ_EVO]

    schedule = await get_schedule(evo, zone_id, loc_idx)
    content = json.dumps(schedule, indent=4) + "\r\n\r\n"

    async with aiofiles.open(filename, "w") as fp:
        await fp.write(content)

    await ctx.obj[SZ_TOKEN_MANAGER].save_access_token(evo)
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

    async def get_schedules(evo: EvohomeClient, loc_idx: int | None) -> _ScheduleT:
        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            schedules = await tcs.get_schedules()

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        return schedules

    print("\r\nclient.py: Starting backup of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    schedules = await get_schedules(evo, loc_idx)
    content = json.dumps(schedules, indent=4) + "\r\n\r\n"

    async with aiofiles.open(filename, "w") as fp:
        await fp.write(content)

    await ctx.obj[SZ_TOKEN_MANAGER].save_access_token(evo)
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

    async def set_schedules(
        evo: EvohomeClient, schedules: _ScheduleT, loc_idx: int | None
    ) -> bool:
        try:
            await evo.login()

            tcs: ControlSystem = _get_tcs(evo, loc_idx)
            success = await tcs.set_schedules(schedules)

        finally:  # FIXME: EvohomeClient should do this...
            assert evo.broker._session is not None  # mypy hint
            await evo.broker._session.close()  # FIXME

        return success

    print("\r\nclient.py: Starting restore of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    async with aiofiles.open(filename, "r") as fp:
        content = await fp.read()

    schedules = json.loads(content)
    success = await set_schedules(evo, schedules, loc_idx)

    await ctx.obj[SZ_TOKEN_MANAGER].save_access_token(evo)
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
