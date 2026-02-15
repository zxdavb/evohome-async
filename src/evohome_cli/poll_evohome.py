"""Temperature polling command for the evohome CLI."""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import re
import select
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
import aiofiles.os
import asyncclick as click
from aiofiles import open as aio_open

from evohomeasync2.exceptions import ApiRequestFailedError

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient

try:
    from influxdb_client_3 import (  # type: ignore[import-not-found]
        InfluxDBClient3,
        Point,
    )
except ImportError:
    InfluxDBClient3 = None
    Point = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]

try:
    import termios
    import tty
except ImportError:
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]


_LOGGER = logging.getLogger(__name__)

PORT_8181 = 8181
MIN_INTERVAL_SECONDS = 30
MAX_INTERVAL_SECONDS = 7200  # 120 minutes


def _parse_interval(interval_str: str) -> float:
    """Parse interval string (e.g., '30s', '1m', '120m') to seconds.

    Valid range: 30s to 120m (7200s)
    """
    # Match pattern: number followed by 's' or 'm'
    match = re.match(r"^(\d+)([sm])$", interval_str.lower())
    if not match:
        raise click.BadParameter(
            f"Invalid interval format: {interval_str}. Use format like '30s', '1m', '120m'"
        )

    value, unit = match.groups()
    value = int(value)

    seconds = value if unit == "s" else value * 60

    # Validate range
    if seconds < MIN_INTERVAL_SECONDS:
        raise click.BadParameter(
            f"Interval must be at least {MIN_INTERVAL_SECONDS} seconds, got {seconds}s"
        )
    if seconds > MAX_INTERVAL_SECONDS:
        raise click.BadParameter(
            f"Interval must be at most {MAX_INTERVAL_SECONDS / 60:.0f} minutes, got {seconds}s"
        )

    return float(seconds)


def _format_zone_key(zone_id: str, zone_name: str) -> str:
    """Format zone key as zone_id_zone_name with spaces replaced by underscores."""
    zone_name_safe = zone_name.replace(" ", "_")
    return f"{zone_id}_{zone_name_safe}"


def get_influxdb_config() -> dict[str, Any] | None:
    """Get InfluxDB configuration from environment or .env file."""
    # Try to load from .env file if python-dotenv is available
    if load_dotenv is not None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    # Use INFLUXDB3_* environment variables (InfluxDB 3 standard)
    token = os.getenv("INFLUXDB3_AUTH_TOKEN")
    host = os.getenv("INFLUXDB3_HOST", "localhost")
    port = os.getenv("INFLUXDB3_PORT", "8086")
    bucket = os.getenv("INFLUXDB3_BUCKET")
    org = os.getenv("INFLUXDB3_ORG")
    ssl = os.getenv("INFLUXDB3_SSL", "false").lower() in ("true", "1", "yes")

    # Fallback to old variable names for backward compatibility
    if not token:
        token = os.getenv("INFLUXDB_TOKEN")
    if host == "localhost" and not os.getenv("INFLUXDB3_HOST"):
        host = os.getenv("INFLUXDB_HOST", "localhost")
    if port == "8086" and not os.getenv("INFLUXDB3_PORT"):
        port = os.getenv("INFLUXDB_PORT", "8086")
    if not bucket:
        bucket = os.getenv("INFLUXDB_BUCKET")

    if not token or not bucket:
        return None

    config: dict[str, Any] = {
        "host": host,
        "token": token,
        "database": bucket,
        "port": port,
    }

    if org:
        config["org"] = org
    if ssl:
        config["ssl"] = True

    return config


async def write_to_influxdb(
    config: dict[str, Any],
    timestamp: datetime,
    system_mode: str,
    zone_temps: dict[str, float | None],
    zones: dict[str, str],
) -> None:
    """Write temperature data to InfluxDB using CSV schema."""
    if InfluxDBClient3 is None or Point is None:
        return

    try:
        # InfluxDB 3 client: write API uses HTTP, query API uses gRPC
        # For non-standard ports (like 8181), use HTTP explicitly (not HTTPS)
        port = int(config["port"]) if "port" in config else None

        # Use http:// for non-TLS connections (port 8181 typically doesn't use TLS)
        # Default ports 443 and 8086 might use HTTPS, but 8181 is usually HTTP
        if port and port == PORT_8181:
            host_url = f"http://{config['host']}"
        else:
            host_url = config["host"]

        client_kwargs: dict[str, Any] = {
            "host": host_url,
            "token": config["token"],
            "database": config["database"],
        }
        # Use port overwrite parameters for both write and query operations
        if port:
            client_kwargs["write_port_overwrite"] = port
            client_kwargs["query_port_overwrite"] = port

        client = InfluxDBClient3(**client_kwargs)

        # Create point with measurement name matching CSV import
        point = Point("roomtemperature").time(timestamp)

        # Add system_mode as a field (not a tag)
        point = point.field("system_mode", system_mode)

        # Add each zone temperature as a field with format: _zone_id_zone_name
        for zone_id, temperature in zone_temps.items():
            if temperature is not None:
                zone_name = zones.get(zone_id, "Unknown")
                field_name = f"_{_format_zone_key(zone_id, zone_name)}"
                point = point.field(field_name, float(temperature))

        client.write(point)
        client.close()
    except Exception:  # noqa: BLE001
        sys.exit(1)


async def import_csv_to_influxdb(  # noqa: C901
    config: dict[str, Any],
    csv_file: str,
    zones: dict[str, str],
) -> None:
    """Import all rows from CSV file to InfluxDB using CSV schema."""
    if InfluxDBClient3 is None or Point is None:
        return

    try:
        # InfluxDB 3 client: write API uses HTTP, query API uses gRPC
        # For non-standard ports (like 8181), use HTTP explicitly (not HTTPS)
        port = int(config["port"]) if "port" in config else None

        # Use http:// for non-TLS connections (port 8181 typically doesn't use TLS)
        if port and port == PORT_8181:
            host_url = f"http://{config['host']}"
        else:
            host_url = config["host"]

        client_kwargs: dict[str, Any] = {
            "host": host_url,
            "token": config["token"],
            "database": config["database"],
        }
        # Use port overwrite parameters for both write and query operations
        if port:
            client_kwargs["write_port_overwrite"] = port
            client_kwargs["query_port_overwrite"] = port

        client = InfluxDBClient3(**client_kwargs)
        points = []

        # Use Path.open() for better cross-platform support
        # Note: We use sync open() here because csv module requires a sync file object
        # and this function runs before the main polling loop, so blocking is acceptable.
        with Path(csv_file).open(newline="") as f:  # noqa: ASYNC230
            reader = csv.DictReader(f)
            for row in reader:
                timestamp_str = row.get("timestamp", "")
                system_mode = row.get("system_mode", "Unknown")

                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, AttributeError):
                    continue

                # Create one point per row with all zones as fields
                point = Point("roomtemperature").time(timestamp)
                point = point.field("system_mode", system_mode)

                has_fields = False
                for zone_id, zone_name in zones.items():
                    zone_key = _format_zone_key(zone_id, zone_name)
                    temperature_str = row.get(zone_key, "")

                    # Skip if no temperature data
                    if not temperature_str or temperature_str == "N/A":
                        continue

                    try:
                        temperature = float(temperature_str)
                        # Use underscore-prefixed field name to match CSV column format
                        field_name = f"_{zone_key}"
                        point = point.field(field_name, temperature)
                        has_fields = True
                    except (ValueError, TypeError):
                        # Skip invalid temperature values
                        pass

                # Only add point if it has at least one temperature field
                if has_fields:
                    points.append(point)

        if points:
            client.write(points)

        client.close()
    except Exception:  # noqa: BLE001
        sys.exit(1)


@click.command("poll")
@click.option(  # --loc-idx
    "--loc-idx",
    "-l",
    callback=lambda ctx, param, value: max(value, 0),
    default=0,
    type=int,
    help="The location idx.",
)
@click.option(  # --interval
    "--interval",
    "-i",
    default="60s",
    type=str,
    callback=lambda ctx, param, value: _parse_interval(value) if value else 60.0,
    help="Interval between temperature readings (30s to 120m, default: 60s).",
)
@click.option(  # --output-file
    "--output-file",
    "-o",
    type=click.Path(writable=True),
    required=True,
    help="Output file for temperature timeseries data (CSV format).",
)
@click.option(  # --append
    "--append",
    "-a",
    is_flag=True,
    default=False,
    help="Append to existing file if it exists (this is the default behavior).",
)
@click.option(  # --overwrite
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing file if it exists (default: append).",
)
@click.option(  # --noshow
    "--noshow",
    is_flag=True,
    default=False,
    help="Do not display temperatures on screen.",
)
@click.option(  # --influx
    "--influx",
    is_flag=True,
    default=False,
    help="Send data to InfluxDB.",
)
@click.option(  # --importcsv
    "--importcsv",
    is_flag=True,
    default=False,
    help="Import existing CSV file to InfluxDB before starting.",
)
@click.pass_context
async def poll_command(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    loc_idx: int,
    interval: float,
    output_file: str,
    append: bool,  # noqa: FBT001
    overwrite: bool,  # noqa: FBT001
    noshow: bool,  # noqa: FBT001
    influx: bool,  # noqa: FBT001
    importcsv: bool,  # noqa: FBT001
) -> None:
    """Poll zone temperatures at regular intervals.

    Continuously polls the temperature of each zone at the specified interval.
    Temperatures are written to a CSV file and optionally displayed on screen.
    Optionally sends data to InfluxDB.

    Press 'L' to show zone list and column headers, then continue polling.
    """
    # Import here to avoid circular dependencies
    from .client import SZ_CLEANUP, SZ_EVO, _get_tcs  # noqa: PLC0415

    # Get InfluxDB config if needed
    influx_config = None
    if influx or importcsv:
        influx_config = get_influxdb_config()
        if not influx_config:
            influx = False
            importcsv = False
            _LOGGER.warning(
                "InfluxDB configuration not found. InfluxDB features disabled."
            )

    evo: EvohomeClient = ctx.obj[SZ_EVO]

    # Get TCS and update to get initial zone list
    tcs = _get_tcs(evo, loc_idx)
    await evo.locations[loc_idx].update()

    # Build zone mapping: zone_id -> zone_name
    zones: dict[str, str] = {}
    zone_order: list[str] = []  # Maintain order

    for zone in tcs.zones:
        zones[zone.id] = zone.name
        zone_order.append(zone.id)

    if not zones:
        await ctx.obj[SZ_CLEANUP]
        return

    # Prepare CSV file
    zone_keys = [_format_zone_key(zid, zones[zid]) for zid in zone_order]
    csv_columns = ["timestamp", "system_mode", *zone_keys]

    # Validate append/overwrite options (mutually exclusive)
    if append and overwrite:
        raise click.BadParameter(
            "Cannot specify both --append and --overwrite. Choose one."
        )

    # Check if file exists and determine action
    try:
        file_exists = await aiofiles.os.path.exists(output_file)
    except Exception:  # noqa: BLE001
        # If we can't check, assume it doesn't exist
        file_exists = False

    write_header = True
    if file_exists:
        write_header = bool(overwrite)

    # Import CSV to InfluxDB if requested (after zones are available)
    if importcsv and influx_config and file_exists:
        await import_csv_to_influxdb(influx_config, output_file, zones)
        await ctx.obj[SZ_CLEANUP]
        return

    # Write CSV header only if needed
    if write_header:
        header_line = ",".join(csv_columns) + "\n"
        async with aio_open(output_file, "w") as fp:
            await fp.write(header_line)

    # Setup keyboard input handling for 'L' key
    show_list_event = asyncio.Event()
    keyboard_thread_running = True
    loop = asyncio.get_event_loop()

    def read_keyboard() -> None:
        """Read keyboard input in a separate thread."""
        if termios and tty:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())

                try:
                    while keyboard_thread_running:
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            char = sys.stdin.read(1)
                            if char.lower() == "l":
                                loop.call_soon_threadsafe(show_list_event.set)
                        time.sleep(0.1)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except (OSError, AttributeError):
                pass

        # Fallback loop if termios not available or failed
        if not (termios and tty):
            while keyboard_thread_running:
                time.sleep(0.5)

    # Start keyboard thread
    keyboard_thread = threading.Thread(target=read_keyboard, daemon=True)
    keyboard_thread.start()

    def print_header() -> None:
        """Print column header."""
        time_width = 19
        mode_width = 15
        temp_width = 8

        header = f"{'Time':<{time_width}} {'Mode':<{mode_width}}"
        for zid in zone_order:
            header += f" {zid:<{temp_width}}"
        print(header)  # noqa: T201

    def print_row(timestamp: str, mode: str, temps: dict[str, float | None]) -> None:
        """Print a row of temperatures."""
        time_width = 19
        mode_width = 15

        row = f"{timestamp:<{time_width}} {mode:<{mode_width}}"
        for zid in zone_order:
            temp = temps.get(zid)
            if temp is not None:
                row += f" {temp:>7.1f} "
            else:
                row += f" {'N/A':>7} "
        print(row)  # noqa: T201

    # Show initial zone list and header
    if not noshow:
        print_header()

    try:
        while True:
            # Update status with retry logic
            max_retries = 2
            retry_count = 0
            update_successful = False

            while retry_count <= max_retries:
                try:
                    await evo.locations[loc_idx].update()
                    update_successful = True
                    break
                except (
                    TimeoutError,
                    ApiRequestFailedError,
                    ConnectionError,
                    OSError,
                ):
                    retry_count += 1
                    if retry_count <= max_retries:
                        await asyncio.sleep(retry_count)
                    else:
                        update_successful = False

            if not update_successful:
                elapsed = 0.0
                check_interval = 0.1
                while elapsed < interval:
                    if show_list_event.is_set():
                        show_list_event.clear()
                        if not noshow:
                            print_header()
                    sleep_time = min(check_interval, interval - elapsed)
                    await asyncio.sleep(sleep_time)
                    elapsed += sleep_time
                continue

            # Get current timestamp with UTC awareness
            now_utc = datetime.now(UTC)
            timestamp = now_utc.isoformat()
            timestamp_short = now_utc.strftime("%Y-%m-%d %H:%M:%S")

            system_mode = str(tcs.mode)

            temps: dict[str, float | None] = {}
            csv_row: dict[str, str] = {
                "timestamp": timestamp,
                "system_mode": system_mode,
            }

            for zid in zone_order:
                zone = tcs.zone_by_id[zid]
                temp = zone.temperature
                temps[zid] = temp
                csv_row[_format_zone_key(zid, zones[zid])] = (
                    f"{temp:.1f}" if temp is not None else "N/A"
                )

            if influx and influx_config:
                await write_to_influxdb(
                    influx_config,
                    now_utc,
                    system_mode,
                    temps,
                    zones,
                )

            row_line = ",".join(str(csv_row.get(col, "")) for col in csv_columns) + "\n"
            async with aio_open(output_file, "a") as fp:
                await fp.write(row_line)

            if not noshow:
                print_row(timestamp_short, system_mode, temps)

            elapsed = 0.0
            check_interval = 0.1
            while elapsed < interval:
                if show_list_event.is_set():
                    show_list_event.clear()
                    print_header()

                sleep_time = min(check_interval, interval - elapsed)
                await asyncio.sleep(sleep_time)
                elapsed += sleep_time

    except KeyboardInterrupt:
        pass
    finally:
        keyboard_thread_running = False
        if keyboard_thread.is_alive():
            keyboard_thread.join(timeout=1.0)
        await ctx.obj[SZ_CLEANUP]


def register_command(cli_group: click.Group) -> None:
    """Register the poll command with the CLI group."""
    cli_group.add_command(poll_command)
