#!/usr/bin/env python3
"""Temperature polling command for the evohome CLI."""

from __future__ import annotations

import asyncio
import csv
import os
import re
import select
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os
import asyncclick as click

from evohomeasync2.exceptions import ApiRequestFailedError

if TYPE_CHECKING:
    from evohomeasync2 import EvohomeClient

try:
    from influxdb_client_3 import InfluxDBClient3, Point
except ImportError:
    InfluxDBClient3 = None
    Point = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


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

    if unit == "s":
        seconds = value
    else:  # unit == 'm'
        seconds = value * 60

    # Validate range: 30s to 120m (7200s)
    if seconds < 30:
        raise click.BadParameter(
            f"Interval must be at least 30 seconds, got {seconds}s"
        )
    if seconds > 7200:  # 120 minutes
        raise click.BadParameter(
            f"Interval must be at most 120 minutes, got {seconds}s"
        )

    return float(seconds)


def _format_zone_key(zone_id: str, zone_name: str) -> str:
    """Format zone key as zone_id_zone_name with spaces replaced by underscores."""
    zone_name_safe = zone_name.replace(" ", "_")
    return f"{zone_id}_{zone_name_safe}"


def get_influxdb_config() -> dict[str, str] | None:
    """Get InfluxDB configuration from environment or .env file.

    Uses INFLUXDB3_* environment variables:
    - INFLUXDB3_AUTH_TOKEN: Authentication token (required)
    - INFLUXDB3_HOST: Host address (default: localhost)
    - INFLUXDB3_PORT: Port number (default: 8086)
    - INFLUXDB3_BUCKET: Bucket/database name (required)
    - INFLUXDB3_ORG: Organization name (optional)
    - INFLUXDB3_SSL: Use SSL (optional, default: false)
    """
    # Try to load from .env file if python-dotenv is available
    if load_dotenv:
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

    config = {
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
    config: dict[str, str],
    timestamp: datetime,
    system_mode: str,
    zone_temps: dict[str, float | None],
    zones: dict[str, str],
) -> None:
    """Write temperature data to InfluxDB using CSV schema.

    Writes one point per timestamp with all zones as fields,
    matching the CSV format for consistency.

    Args:
        config: InfluxDB configuration
        timestamp: Timestamp for the data point
        system_mode: System mode (e.g., 'Auto', 'HeatingOff')
        zone_temps: Dictionary of zone_id -> temperature
        zones: Dictionary of zone_id -> zone_name
    """
    if InfluxDBClient3 is None or Point is None:
        return

    try:
        # InfluxDB 3 client: write API uses HTTP, query API uses gRPC
        # For non-standard ports (like 8181), use HTTP explicitly (not HTTPS)
        port = int(config["port"]) if "port" in config else None

        # Use http:// for non-TLS connections (port 8181 typically doesn't use TLS)
        # Default ports 443 and 8086 might use HTTPS, but 8181 is usually HTTP
        if port and port == 8181:
            host_url = f"http://{config['host']}"
        else:
            host_url = config["host"]

        client_kwargs = {
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
    except Exception:
        sys.exit(1)


async def import_csv_to_influxdb(
    config: dict[str, str],
    csv_file: str,
    zones: dict[str, str],
) -> None:
    """Import all rows from CSV file to InfluxDB using CSV schema.

    Imports data matching the CSV format: one point per timestamp
    with all zones as fields.
    """
    if InfluxDBClient3 is None or Point is None:
        return

    try:
        # InfluxDB 3 client: write API uses HTTP, query API uses gRPC
        # For non-standard ports (like 8181), use HTTP explicitly (not HTTPS)
        port = int(config["port"]) if "port" in config else None

        # Use http:// for non-TLS connections (port 8181 typically doesn't use TLS)
        # Default ports 443 and 8086 might use HTTPS, but 8181 is usually HTTP
        if port and port == 8181:
            host_url = f"http://{config['host']}"
        else:
            host_url = config["host"]

        client_kwargs = {
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
        row_count = 0
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_count += 1
                timestamp_str = row.get("timestamp", "")
                system_mode = row.get("system_mode", "Unknown")

                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str
                    )
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
        else:
            pass

        client.close()
    except Exception:
        sys.exit(1)


def register_command(cli_group: click.Group) -> None:
    """Register the poll command with the CLI group."""
    # Import here to avoid circular import
    from .client import SZ_CLEANUP, SZ_EVO, _check_positive_int, _get_tcs

    @cli_group.command("poll")
    @click.option(  # --loc-idx
        "--loc-idx",
        "-l",
        callback=_check_positive_int,
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
    async def poll(
        ctx: click.Context,
        loc_idx: int,
        interval: float,
        output_file: str,
        append: bool,
        overwrite: bool,
        noshow: bool,
        influx: bool,
        importcsv: bool,
    ) -> None:
        """Poll zone temperatures at regular intervals.

        Continuously polls the temperature of each zone at the specified interval.
        Temperatures are written to a CSV file and optionally displayed on screen.
        Optionally sends data to InfluxDB.

        Press 'L' to show zone list and column headers, then continue polling.
        """

        # Get InfluxDB config if needed
        influx_config = None
        if influx or importcsv:
            influx_config = get_influxdb_config()
            if not influx_config:
                influx = False
                importcsv = False
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
        file_exists = False
        try:
            file_exists = await aiofiles.os.path.exists(output_file)
        except Exception:
            # If we can't check, assume it doesn't exist
            file_exists = False

        write_header = True
        if file_exists:
            if overwrite:
                # User specified --overwrite, overwrite file
                write_header = True
            else:
                # Default behavior: append (whether --append was specified or not)
                # If --append was explicitly specified, show message; otherwise it's the default
                if append:
                    pass
                else:
                    pass
                write_header = False

        # Import CSV to InfluxDB if requested (after zones are available)
        if importcsv and influx_config and file_exists:
            await import_csv_to_influxdb(influx_config, output_file, zones)
            await ctx.obj[SZ_CLEANUP]
            return

        # Write CSV header only if needed
        if write_header:
            header_line = ",".join(csv_columns) + "\n"
            async with aiofiles.open(output_file, "w") as fp:
                await fp.write(header_line)

        # Setup keyboard input handling for 'L' key
        show_list_event = asyncio.Event()
        keyboard_thread_running = True
        loop = asyncio.get_event_loop()

        def read_keyboard() -> None:
            """Read keyboard input in a separate thread."""
            nonlocal keyboard_thread_running

            # Try to set up non-blocking stdin (Unix-like systems)
            try:
                import termios
                import tty

                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())

                try:
                    while keyboard_thread_running:
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            char = sys.stdin.read(1)
                            if char.lower() == "l":
                                # Set event in the async event loop (set() is synchronous, use call_soon_threadsafe)
                                loop.call_soon_threadsafe(show_list_event.set)
                        time.sleep(0.1)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except (ImportError, OSError, AttributeError):
                # Fallback for systems without termios (e.g., Windows)
                # On Windows or systems without termios, keyboard input won't work
                # Just sleep to keep thread alive
                while keyboard_thread_running:
                    time.sleep(0.5)

        # Start keyboard thread
        keyboard_thread = threading.Thread(target=read_keyboard, daemon=True)
        keyboard_thread.start()

        # Display header
        def print_header() -> None:
            """Print column header."""
            time_width = 19  # ISO format timestamp
            mode_width = 15  # System mode (e.g., "AutoWithEco")
            temp_width = 8  # Temperature value

            header = f"{'Time':<{time_width}} {'Mode':<{mode_width}}"
            for zid in zone_order:
                header += f" {zid:<{temp_width}}"

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

        def print_zone_list() -> None:
            """Print zone ID to name mapping."""
            for _zid in zone_order:
                pass

        # Show initial zone list and header
        print_zone_list()
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
                    except (TimeoutError, ApiRequestFailedError, ConnectionError, OSError):
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait a bit before retrying (exponential backoff: 1s, 2s)
                            await asyncio.sleep(retry_count)
                        else:
                            update_successful = False

                # If update failed after all retries, skip to next interval
                if not update_successful:
                    # Wait for interval before trying again
                    elapsed = 0.0
                    check_interval = 0.1
                    while elapsed < interval:
                        if show_list_event.is_set():
                            show_list_event.clear()
                            print_zone_list()
                            if not noshow:
                                print_header()
                        sleep_time = min(check_interval, interval - elapsed)
                        await asyncio.sleep(sleep_time)
                        elapsed += sleep_time
                    continue

                # Get current timestamp
                timestamp = datetime.now().isoformat()
                timestamp_short = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Get system mode
                system_mode = str(tcs.mode)

                # Collect temperatures
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

                # Write to InfluxDB if enabled (one point with all zones)
                if influx and influx_config:
                    await write_to_influxdb(
                        influx_config,
                        datetime.now(),
                        system_mode,
                        temps,
                        zones,
                    )

                # Write to CSV
                row_line = (
                    ",".join(str(csv_row.get(col, "")) for col in csv_columns) + "\n"
                )
                async with aiofiles.open(output_file, "a") as fp:
                    await fp.write(row_line)

                # Display on screen
                if not noshow:
                    print_row(timestamp_short, system_mode, temps)

                # Wait for interval, but check for 'L' key press periodically
                elapsed = 0.0
                check_interval = 0.1  # Check every 100ms
                while elapsed < interval:
                    # Check for 'L' key press
                    if show_list_event.is_set():
                        show_list_event.clear()
                        print_zone_list()
                        if not noshow:
                            print_header()

                    # Sleep in small increments to allow responsive 'L' key handling
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
