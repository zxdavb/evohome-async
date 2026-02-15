#!/usr/bin/env python3
"""evohomeasync - a CLI utility that is not a core part of the library."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

import aiofiles
import aiohttp
import asyncclick as click

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
    TokenCacheManager,
    delete_password_from_keyring,
    delete_username_from_keyring,
    get_password_from_keyring,
    get_username_from_keyring,
    is_keyring_available,
    save_password_to_keyring,
    save_username_to_keyring,
)
from .schedule_parser import json_to_text_schedule, parse_text_schedule

if TYPE_CHECKING:
    from io import TextIOWrapper

# all _DBG_* flags are only for dev/test and should be False for published code
_DBG_DEBUG_CLI = False  # for debugging of click

DEBUG_ADDR = "0.0.0.0"  # noqa: S104
DEBUG_PORT = 5679

SZ_CLEANUP: Final = "cleanup"
SZ_EVO: Final = "evohome"
SZ_USERNAME: Final = "username"


# User-facing messages go to stderr via click.echo(err=True), keeping stdout
# clean for data output (JSON, mode strings, etc.) that can be piped/redirected.
# The logging framework also writes to stderr, so warning/debug diagnostics from
# the library and from keyring helpers never corrupt piped data either.


def _start_debugging(*, wait_for_client: bool | None = None) -> None:
    import debugpy  # noqa: PLC0415

    try:
        debugpy.listen((DEBUG_ADDR, DEBUG_PORT))
    except RuntimeError:
        click.echo(
            f"Debugging is already enabled on: {DEBUG_ADDR}:{DEBUG_PORT}", err=True
        )
        raise
    else:
        click.echo(
            f"Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}", err=True
        )

    if wait_for_client and not debugpy.is_client_connected():
        click.echo(" - execution paused, waiting for debugger to attach...", err=True)
        debugpy.wait_for_client()
        click.echo(" - debugger is now attached, continuing execution.", err=True)


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


def _require_keyring() -> None:
    """Raise a ClickException if no working keyring backend is available."""

    if not is_keyring_available():
        raise click.ClickException(
            "No keyring backend available; install a supported backend"
            " (e.g. 'pip install keyrings.alt' or 'pip install secretstorage')."
        )


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
@click.option(
    "--save-credentials",
    is_flag=True,
    help="Save the username and password to the system keyring.",
)
@click.option("--no-load-tokens", is_flag=True, help="Don't load the token cache.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
async def cli(
    ctx: click.Context,
    username: str | None,
    password: str | None,
    *,
    save_credentials: bool | None = None,
    no_load_tokens: bool | None = None,
    debug: bool | None = None,
) -> None:
    """A demonstration CLI for the evohomeasync2 client library."""

    if debug:  # Do first
        _start_debugging(wait_for_client=True)

    async def cleanup() -> None:
        """Close the web session and save the access token to the cache."""
        await token_manager.save_access_token()
        await websession.close()

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )

    # Commands that don't need an API connection skip the auth flow entirely.
    if ctx.invoked_subcommand == "clear-credentials":
        _require_keyring()

        async def noop() -> None:
            pass

        ctx.obj[SZ_CLEANUP] = noop
        ctx.obj[SZ_USERNAME] = username  # may be None; command will handle it
        return

    if username is None:
        username = get_username_from_keyring() or await click.prompt("Username")
    assert isinstance(username, str)  # resolved via CLI arg, keyring, or prompt

    if password is None:
        password = get_password_from_keyring(username) or await click.prompt(
            "Password", hide_input=True
        )
    assert isinstance(password, str)  # resolved via CLI arg, keyring, or prompt

    websession = aiohttp.ClientSession()  # timeout=aiohttp.ClientTimeout(total=30))
    token_manager = TokenCacheManager(
        username, password, websession, cache_file=CACHE_FILE
    )

    if not no_load_tokens:  # then restore cached tokens, if any
        await token_manager.load_from_cache()

    evo = EvohomeClient(token_manager, debug=bool(debug))

    click.echo("Authenticating and retrieving installation data...", err=True)

    try:
        await evo.update()
    except exc.AuthenticationFailedError:
        await websession.close()
        raise

    if save_credentials:
        _require_keyring()
        save_username_to_keyring(username)
        save_password_to_keyring(username, password)

    # TODO: use a typed dict for ctx.obj
    ctx.obj[SZ_EVO] = evo
    ctx.obj[SZ_CLEANUP] = cleanup


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
async def get_system_mode(ctx: click.Context, loc_idx: int) -> None:
    """Retrieve the system mode."""

    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        result = _get_tcs(evo, loc_idx).system_mode_status
        await _write(sys.stdout, json.dumps(result, indent=4) + "\n")

    finally:
        await ctx.obj[SZ_CLEANUP]()


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
async def dump_location(
    ctx: click.Context, loc_idx: int, output_file: TextIOWrapper
) -> None:
    """Download all the global config and the location status."""

    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        click.echo("Retrieving location status...", err=True)

        result = {
            "config": evo.locations[loc_idx].config,
            "status": await evo.locations[loc_idx].update(),
        }

        await _write(output_file, json.dumps(result, indent=4) + "\n")

    finally:
        await ctx.obj[SZ_CLEANUP]()


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

    evo = ctx.obj[SZ_EVO]

    try:
        click.echo("Retrieving schedule...", err=True)

        zon: HotWater | Zone = _get_tcs(evo, loc_idx).zone_by_id[zone_id]
        schedule = {zon.id: {SZ_NAME: zon.name, SZ_SCHEDULE: await zon.get_schedule()}}

        await _write(output_file, json.dumps(schedule, indent=4) + "\n")

    finally:
        await ctx.obj[SZ_CLEANUP]()


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
    ctx: click.Context, loc_idx: int, output_file: TextIOWrapper, output_format: str
) -> None:
    """Download all the schedules from a TCS."""

    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        tcs = _get_tcs(evo, loc_idx)

    except IndexError:
        raise click.ClickException(f"No TCS found at location idx: {loc_idx}") from None

    else:
        click.echo("Retrieving schedules...", err=True)

        schedules = await tcs.get_schedules()

        if output_format.lower() == "text":
            content = json_to_text_schedule(schedules) + "\r\n\r\n"
        else:
            content = json.dumps(schedules, indent=4) + "\r\n\r\n"

        await _write(output_file, content)

    finally:
        await ctx.obj[SZ_CLEANUP]()


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
    ctx: click.Context, loc_idx: int, input_file: TextIOWrapper, input_format: str
) -> None:
    """Upload schedules to a TCS."""

    evo: EvohomeClient = ctx.obj[SZ_EVO]

    try:
        tcs = _get_tcs(evo, loc_idx)

    except IndexError:
        raise click.ClickException(f"No TCS found at location idx: {loc_idx}") from None

    else:
        # will TypeError if input_file is sys.stdin
        async with aiofiles.open(input_file.name) as fp:
            content = await fp.read()

        if input_format.lower() == "text":
            schedules = parse_text_schedule(content)
        else:
            schedules = json.loads(content)

        click.echo("Uploading schedules...", err=True)

        success = await tcs.set_schedules(cast("list[Any]", schedules))
        if not success:
            raise click.ClickException("Schedule restore completed with errors.")

    finally:
        await ctx.obj[SZ_CLEANUP]()


@cli.command()
@click.pass_context
async def clear_credentials(ctx: click.Context) -> None:
    """Remove all stored credentials from the system keyring."""

    cleared = False

    # delete password for the keyring-stored username
    stored_username: str | None = get_username_from_keyring()
    if stored_username:
        delete_password_from_keyring(stored_username)
        cleared = True

    # also delete password for the CLI-supplied username, if different
    cli_username: str | None = ctx.obj[SZ_USERNAME]
    if cli_username and cli_username != stored_username:
        delete_password_from_keyring(cli_username)
        cleared = True

    cleared |= delete_username_from_keyring()

    click.echo(
        "Cleared stored credentials." if cleared else "No stored credentials found.",
        err=True,
    )


@click.group()
def convert_cli() -> None:
    """Standalone file format conversion commands (no authentication required)."""


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

    click.echo("\r\nConverting text schedule to JSON format...")

    try:
        content = input_file.read()
        schedules = parse_text_schedule(content)
        json_content = json.dumps(schedules, indent=4) + "\r\n\r\n"

        if output_file.name == "<stdout>":
            output_file.write(json_content)
        else:
            # For file output, we need to write synchronously since it's not async
            Path(output_file.name).write_text(json_content)

        click.echo(f" - Converted {len(schedules)} zones to JSON format.")
        click.echo(" - finished.\r\n")

    except (ValueError, OSError, KeyError) as e:
        click.echo(f"Error: {e}\r\n")
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

    click.echo("\r\nConverting JSON schedule to text format...")

    try:
        content = input_file.read()
        schedules = json.loads(content)
        text_content = json_to_text_schedule(schedules) + "\r\n\r\n"

        if output_file.name == "<stdout>":
            output_file.write(text_content)
        else:
            # For file output, we need to write synchronously since it's not async
            Path(output_file.name).write_text(text_content)

        click.echo(f" - Converted {len(schedules)} zones to text format.")
        click.echo(" - finished.\r\n")

    except (ValueError, OSError, KeyError) as e:
        click.echo(f"Error: {e}\r\n")
        sys.exit(1)


def main() -> None:
    """Run the CLI."""

    # Check if we're running a conversion command (no auth needed)
    if len(sys.argv) > 1 and sys.argv[1] in [
        "convert-schedule-to-json",
        "convert-schedule-to-text",
    ]:
        # Handle conversion commands directly
        try:
            convert_cli()
        except click.ClickException as err:
            click.echo(f"Error: {err}")
            sys.exit(-1)
    else:
        # Handle main CLI commands (require auth)
        try:
            asyncio.run(cli(obj={}))  # default for ctx.obj is None

        except click.ClickException as err:
            click.echo(f"Error: {err}", err=True)
            sys.exit(-1)


if __name__ == "__main__":
    main()
