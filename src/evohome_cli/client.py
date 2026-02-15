#!/usr/bin/env python3
"""evohomeasync - a CLI utility that is not a core part of the library."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
import sys
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import aiofiles.os
import aiohttp
import asyncclick as click
import debugpy

from evohomeasync2 import (
    ControlSystem,
    EvohomeClient,
    HotWater,
    Zone,
    exceptions as exc,
)
from evohomeasync2.const import SZ_NAME, SZ_SCHEDULE

from .auth import (
    CACHE_FILE,
    CredentialsManager,
    delete_stored_credentials,
    get_credential_storage_location,
    get_stored_credentials,
    store_credentials,
)
from .poll_evohome import register_command as register_poll
from .schedule_parser import json_to_text_schedule, parse_text_schedule

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
    no_tokens: bool | None = None,
    debug: bool | None = None,
) -> None:
    """A demonstration CLI for the evohomeasync2 client library."""

    if debug:  # Do first
        _start_debugging(wait_for_client=True)

    # Get credentials from command line or secure storage
    if username is None or password is None:
        stored = get_stored_credentials()
        if stored:
            stored_username, stored_password = stored
            if username is None:
                username = stored_username
            if password is None:
                password = stored_password
        else:
            # No stored credentials and not provided on command line
            if username is None:
                raise click.BadParameter(
                    "Username not provided. Use --username/-u or run 'evo-client login' to store credentials securely."
                )
            if password is None:
                raise click.BadParameter(
                    "Password not provided. Use --password/-p or run 'evo-client login' to store credentials securely."
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


# Register commands from separate modules
register_poll(cli)


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
@click.option(  # --format
    "--format",
    "-f",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="json",
    help="Output format: json or text (default: json).",
)
@click.pass_context
async def get_schedules(
    ctx: click.Context, loc_idx: int, output_file: TextIOWrapper, format: str
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

        if format.lower() == "text":
            content = json_to_text_schedule(schedules) + "\r\n\r\n"
        else:
            content = json.dumps(schedules, indent=4) + "\r\n\r\n"

        await _write(output_file, content)

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
@click.option(  # --format
    "--format",
    "-f",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="json",
    help="Input format: json or text (default: json).",
)
@click.pass_context
async def set_schedules(
    ctx: click.Context, loc_idx: int, input_file: TextIOWrapper, format: str
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

        if format.lower() == "text":
            schedules = parse_text_schedule(content)
        else:
            schedules = json.loads(content)

        success = await tcs.set_schedules(schedules)

    finally:
        await ctx.obj[SZ_CLEANUP]

    print(f" - finished{'' if success else ' (with errors)'}.\r\n")


@click.command("login")
@click.option("--username", "-u", default=None, help="The TCC account username.")
@click.option("--password", "-p", default=None, help="The TCC account password.")
@click.option("--delete", "-d", is_flag=True, help="Delete stored credentials.")
def login(username: str | None, password: str | None, delete: bool) -> None:
    """Store TCC account credentials securely for future use.

    Credentials are stored in the system's secure credential store:
    - macOS: Keychain Access
    - Windows: Credential Manager
    - Linux: Secret Service (GNOME Keyring, KWallet, etc.)

    If username or password are not provided, you will be prompted to enter them.
    The password will not be displayed while typing.
    """

    if delete:
        try:
            delete_stored_credentials()
            print("\r\n✓ Stored credentials have been deleted.\r\n")
        except Exception as e:
            print(f"\r\n✗ Error deleting credentials: {e}\r\n")
            sys.exit(1)
        return

    # Get username if not provided
    if username is None:
        username = click.prompt("TCC Username", type=str)

    # Get password if not provided (don't echo)
    if password is None:
        password = click.prompt("TCC Password", type=str, hide_input=True)

    # Store credentials
    try:
        store_credentials(username, password)
        storage_location = get_credential_storage_location()
        print(f"\r\n✓ Credentials stored securely in: {storage_location}")
        print(
            "  You can now use evo-client commands without --username and --password.\r\n"
        )
    except Exception as e:
        print(f"\r\n✗ Error storing credentials: {e}\r\n")
        print("  You may need to install keyring: pip install keyring\r\n")
        sys.exit(1)


@click.group()
def convert_cli() -> None:
    """Standalone file format conversion commands (no authentication required)."""
    pass


@convert_cli.command("convert-schedule-to-json")
@click.option(  # --input-file
    "--input-file",
    "-i",
    type=click.File("r"),
    required=True,
    help="Input text schedule file.",
)
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.File("w"),
    default="-",
    help="Output JSON schedule file (default: stdout).",
)
def convert_schedule_to_json(
    input_file: TextIOWrapper, output_file: TextIOWrapper
) -> None:
    """Convert text schedule format to JSON format."""

    print("\r\nConverting text schedule to JSON format...")

    try:
        content = input_file.read()
        schedules = parse_text_schedule(content)
        json_content = json.dumps(schedules, indent=4) + "\r\n\r\n"

        if output_file.name == "<stdout>":
            output_file.write(json_content)
        else:
            # For file output, we need to write synchronously since it's not async
            with open(output_file.name, "w") as fp:
                fp.write(json_content)

        print(f" - Converted {len(schedules)} zones to JSON format.")
        print(" - finished.\r\n")

    except Exception as e:
        print(f"Error: {e}\r\n")
        sys.exit(1)


@convert_cli.command("convert-schedule-to-text")
@click.option(  # --input-file
    "--input-file",
    "-i",
    type=click.File("r"),
    required=True,
    help="Input JSON schedule file.",
)
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.File("w"),
    default="-",
    help="Output text schedule file (default: stdout).",
)
def convert_schedule_to_text(
    input_file: TextIOWrapper, output_file: TextIOWrapper
) -> None:
    """Convert JSON schedule format to text format."""

    print("\r\nConverting JSON schedule to text format...")

    try:
        content = input_file.read()
        schedules = json.loads(content)
        text_content = json_to_text_schedule(schedules) + "\r\n\r\n"

        if output_file.name == "<stdout>":
            output_file.write(text_content)
        else:
            # For file output, we need to write synchronously since it's not async
            with open(output_file.name, "w") as fp:
                fp.write(text_content)

        print(f" - Converted {len(schedules)} zones to text format.")
        print(" - finished.\r\n")

    except Exception as e:
        print(f"Error: {e}\r\n")
        sys.exit(1)


def main() -> None:
    """Run the CLI."""

    # Check if we're running a conversion or login command (no auth needed)
    if len(sys.argv) > 1 and sys.argv[1] in [
        "convert-schedule-to-json",
        "convert-schedule-to-text",
        "login",
    ]:
        # Handle conversion/login commands directly
        try:
            if sys.argv[1] == "login":
                # Invoke login command with click's argument parsing
                # For standalone commands, click expects the program name in argv[0]
                # and the options in argv[1:], so we remove 'login' from the args
                original_argv = sys.argv[:]
                # Keep argv[0] as program name, skip argv[1] (which is 'login'), keep rest
                sys.argv = [sys.argv[0]] + sys.argv[2:]
                try:
                    login()
                finally:
                    sys.argv = original_argv
            else:
                convert_cli()
        except click.ClickException as err:
            print(f"Error: {err}")
            sys.exit(-1)
    else:
        # Handle main CLI commands (require auth)
        try:
            asyncio.run(cli(obj={}))  # default for ctx.obj is None
        except click.ClickException as err:
            print(f"Error: {err}")
            sys.exit(-1)


if __name__ == "__main__":
    main()
