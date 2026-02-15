#!/usr/bin/env python3
"""evohomeasync - a CLI utility that is not a core part of the library."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import aiofiles.os
import aiohttp
import asyncclick as click
import debugpy

from _evohome.exceptions import CredentialStorageError
from evohomeasync2 import (
    ControlSystem,
    EvohomeClient,
    HotWater,
    Zone,
    exceptions as exc,
)
from evohomeasync2.const import SZ_NAME, SZ_SCHEDULE

from .auth import CACHE_FILE, CredentialsManager, KeyringCredentialManager

if TYPE_CHECKING:
    from io import TextIOWrapper

# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DEBUG_CLI = False  # for debugging of click

DEBUG_ADDR = "0.0.0.0"  # noqa: S104
DEBUG_PORT = 5679

SZ_CLEANUP: Final = "cleanup"
SZ_EVO: Final = "evo"
SZ_USERNAME: Final = "username"


_LOGGER: Final = logging.getLogger(__name__)


def _start_debugging(*, wait_for_client: bool | None = None) -> None:
    try:
        debugpy.listen((DEBUG_ADDR, DEBUG_PORT))
    except RuntimeError:
        print(f" - Debugging is already enabled on: {DEBUG_ADDR}:{DEBUG_PORT}")
        raise
    else:
        print(f" - Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}")

    if wait_for_client and not debugpy.is_client_connected():
        print("   - execution paused, waiting for debugger to attach...")
        debugpy.wait_for_client()
        print("   - debugger is now attached, continuing execution.")


if _DBG_DEBUG_CLI:
    _start_debugging(wait_for_client=True)


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
        loc_idx = 0
    return evo.locations[loc_idx].gateways[0].systems[0]


async def _write(output_file: TextIOWrapper | Any, content: str) -> None:
    """Write to a file, async if possible and sync otherwise."""

    if output_file.name == "<stdout>":
        output_file.write(content)
    else:
        async with aiofiles.open(output_file.name, "w") as fp:
            await fp.write(content)


@click.group()
@click.option("--username", "-u", default=None, help="The TCC account username.")
@click.option("--password", "-p", default=None, help="The TCC account password.")
@click.option("--no-tokens", "-c", is_flag=True, help="Dont load the token cache.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
async def cli(
    ctx: click.Context,
    username: str | None,
    password: str | None,
    *,
    no_tokens: bool | None = None,
    debug: bool | None = None,
) -> None:
    """A demonstration CLI for the evohomeasync2 client library.

    Credentials can be provided via --username/--password options or stored
    securely using the 'login' command. Stored credentials will be used if
    options are not provided.
    """

    if debug:  # Do first
        _start_debugging(wait_for_client=True)

    # Resolve credentials: command-line args take priority over stored credentials
    if username is None or password is None:
        try:
            keyring_manager = KeyringCredentialManager()
            stored_creds = keyring_manager.get_credentials()
            if stored_creds:
                username = username or stored_creds[0]
                password = password or stored_creds[1]
        except CredentialStorageError:
            # Keyring not available, continue without stored credentials
            pass

    # Verify we have credentials after resolution
    if username is None or password is None:
        raise click.UsageError(
            "Credentials required. Provide --username and --password, "
            "or use 'evohome-cli login' to store credentials securely."
        )

    async def cleanup(
        websession: aiohttp.ClientSession,
        token_manager: CredentialsManager,
    ) -> None:
        """Close the web session and save the access token to the cache."""

        await websession.close()
        await token_manager.save_access_token()

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    websession = aiohttp.ClientSession()  # timeout=aiohttp.ClientTimeout(total=30))
    token_manager = CredentialsManager(
        username, password, websession, cache_file=CACHE_FILE
    )

    if not no_tokens:  # then restore cached tokens, if any
        await token_manager._load_access_token()

    evo = EvohomeClient(token_manager, debug=bool(debug))

    try:
        await evo.update()
    except exc.AuthenticationFailedError:
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

    await _write(sys.stdout, "\r\n" + str(_get_tcs(evo, loc_idx).mode) + "\r\n\r\n")

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
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.File("w"),
    default="-",
    help="The output file.",
)
@click.pass_context
async def dump(ctx: click.Context, loc_idx: int, output_file: TextIOWrapper) -> None:
    """Download all the global config and the location status."""

    print("\r\nclient.py: Starting dump of config and status...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    result = {
        "config": evo.locations[loc_idx].config,
        "status": await evo.locations[loc_idx].update(),
    }

    await _write(output_file, json.dumps(result, indent=4) + "\r\n\r\n")

    await ctx.obj[SZ_CLEANUP]
    print(" - finished.\r\n")


@cli.command()
@click.argument(  # zone-id
    "zone-id",
    callback=_check_zone_id,
    type=str,
)
@click.option(  # --loc-idx
    "--loc-idx",
    "-l",
    callback=_check_positive_int,
    default=0,
    type=int,
    help="The location idx.",
)
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.File("w"),
    default="-",
    help="The output file.",
)
@click.pass_context
async def get_schedule(
    ctx: click.Context, zone_id: str, loc_idx: int, output_file: TextIOWrapper
) -> None:
    """Download the schedule of a zone of a TCS (WIP)."""

    print("\r\nclient.py: Starting backup of zone schedule (WIP)...")
    evo = ctx.obj[SZ_EVO]

    zon: HotWater | Zone = _get_tcs(evo, loc_idx).zone_by_id[zone_id]
    schedule = {zon.id: {SZ_NAME: zon.name, SZ_SCHEDULE: await zon.get_schedule()}}

    await _write(output_file, json.dumps(schedule, indent=4) + "\r\n\r\n")

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
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.File("w"),
    default="-",
    help="The output file.",
)
@click.pass_context
async def get_schedules(
    ctx: click.Context, loc_idx: int, output_file: TextIOWrapper
) -> None:
    """Download all the schedules from a TCS."""

    print("\r\nclient.py: Starting backup of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        tcs = _get_tcs(evo, loc_idx)

    except IndexError:
        print("Aborted: No TCS found at location idx: %s", loc_idx)

    else:
        schedules = await tcs.get_schedules()

        await _write(output_file, json.dumps(schedules, indent=4) + "\r\n\r\n")

    finally:
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
@click.option(  # --input-file
    "--input-file",
    "-i",
    type=click.File(),
    help="The input file.",
)
@click.pass_context
async def set_schedules(
    ctx: click.Context, loc_idx: int, input_file: TextIOWrapper
) -> None:
    """Upload schedules to a TCS."""

    print("\r\nclient.py: Starting restore of schedules...")
    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        tcs = _get_tcs(evo, loc_idx)

    except IndexError:
        print("Aborted: No TCS found at location idx: %s", loc_idx)

    else:
        # will TypeError if input_file is sys.stdin
        async with aiofiles.open(input_file.name) as fp:
            content = await fp.read()

        success = await tcs.set_schedules(json.loads(content))

    finally:
        await ctx.obj[SZ_CLEANUP]

    print(f" - finished{'' if success else ' (with errors)'}.\r\n")


@click.command("login")
@click.option("--username", "-u", default=None, help="The TCC account username.")
@click.option("--password", "-p", default=None, help="The TCC account password.")
@click.option("--delete", "-d", is_flag=True, help="Delete stored credentials.")
def login(username: str | None, password: str | None, *, delete: bool) -> None:
    """Store or delete TCC credentials securely in the system keyring.

    Use this command to save your credentials so you don't need to provide
    --username and --password for every command.
    """
    try:
        keyring_manager = KeyringCredentialManager()
    except CredentialStorageError as err:
        print(f"\r\n✗ Error: {err}")
        print("\r\nTo install keyring support, run: pip install keyring\r\n")
        sys.exit(1)

    if delete:
        try:
            keyring_manager.delete_credentials()
            print("\r\n✓ Credentials deleted successfully.\r\n")
        except CredentialStorageError as err:
            print(f"\r\n✗ Failed to delete credentials: {err}\r\n")
            sys.exit(1)
        return

    # Get username if not provided
    if username is None:
        username = str(click.prompt("TCC Username", type=str))

    # Get password if not provided (don't echo)
    if password is None:
        password = str(click.prompt("TCC Password", type=str, hide_input=True))

    # Store credentials
    try:
        keyring_manager.store_credentials(username, password)
        storage_location = keyring_manager.storage_location
        print(f"\r\n✓ Credentials stored securely in: {storage_location}")
        print(
            "\r\nYou can now use evohome-cli commands "
            "without --username/--password.\r\n"
        )
    except CredentialStorageError as err:
        print(f"\r\n✗ Failed to store credentials: {err}\r\n")
        sys.exit(1)


def main() -> None:
    """Run the CLI."""

    # Handle login command separately (not async, doesn't need full CLI setup)
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login(standalone_mode=False)
        return

    try:
        asyncio.run(cli(obj={}))  # default for ctx.obj is None

    except click.ClickException as err:
        print(f"Error: {err}")
        sys.exit(-1)


if __name__ == "__main__":
    main()
