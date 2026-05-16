#!/usr/bin/env python3
"""HA platinum quality scale compliance checks."""

from __future__ import annotations

import http.client
import re
import sys
import tomllib
import urllib.parse
import zipfile
from pathlib import Path
from typing import NoReturn

from packaging.requirements import Requirement
from packaging.version import Version

HA_STABLE_PYPROJECT = (
    "https://raw.githubusercontent.com/home-assistant/core/master/pyproject.toml"
)
LIB_SRC = Path("src")
EXCLUDED_PARTS = {"evohome_cli", "tests", "test"}
EXPECTED_ARGC = 2


def _echo(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _fail(message: str) -> NoReturn:
    sys.stderr.write(f"{message}\n")
    raise SystemExit(1)


def _load_pyproject(path: Path) -> dict[str, object]:
    with path.open("rb") as file:
        return tomllib.load(file)


def load_our_pyproject() -> dict[str, object]:
    return _load_pyproject(Path("pyproject.toml"))


def load_ha_pyproject() -> dict[str, object]:
    parsed = urllib.parse.urlsplit(HA_STABLE_PYPROJECT)
    if parsed.scheme != "https" or parsed.netloc != "raw.githubusercontent.com":
        _fail(f"FAIL: unsupported HA pyproject URL: {HA_STABLE_PYPROJECT}")

    connection = http.client.HTTPSConnection(parsed.netloc, timeout=30)
    try:
        connection.request("GET", parsed.path)
        response = connection.getresponse()
        if response.status != http.client.OK:
            _fail(
                "FAIL: could not fetch HA pyproject "
                f"(HTTP {response.status} {response.reason})"
            )
        return tomllib.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def _project_dependencies(data: dict[str, object]) -> list[str]:
    project = data.get("project")
    if not isinstance(project, dict):
        return []
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        return []
    return [dep for dep in dependencies if isinstance(dep, str)]


def _project_requires_python(data: dict[str, object]) -> str:
    project = data.get("project")
    if not isinstance(project, dict):
        return ""

    requires_python = project.get("requires-python", "")
    if not isinstance(requires_python, str):
        return ""
    return requires_python.strip()


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _iter_library_files() -> list[Path]:
    files = []
    for path in LIB_SRC.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def _highest_lower_bound(requirement: Requirement) -> Version | None:
    lower_bound: Version | None = None
    for specifier in requirement.specifier:
        if specifier.operator != ">=":
            continue
        version = Version(specifier.version)
        if lower_bound is None or version > lower_bound:
            lower_bound = version
    return lower_bound


def check_no_exact_pins() -> None:
    deps = _project_dependencies(load_our_pyproject())
    exact_pins: list[str] = []
    unsupported: list[str] = []

    for dep in deps:
        requirement = Requirement(dep)
        for specifier in requirement.specifier:
            if specifier.operator in {"==", "==="}:
                exact_pins.append(dep)
            if specifier.operator not in {">=", "!="}:
                unsupported.append(dep)

    if exact_pins:
        _echo("FAIL: exact pins (==) found in [project].dependencies:")
        for dep in exact_pins:
            _echo(f"  - {dep}")
        raise SystemExit(1)

    if unsupported:
        _echo("FAIL: unsupported dependency operators found.")
        _echo("Use >= floor constraints (and optional != exclusions) only:")
        for dep in sorted(set(unsupported)):
            _echo(f"  - {dep}")
        raise SystemExit(1)

    _echo(f"OK: dependency constraints are floor-based across {len(deps)} entries")


def check_dep_ceiling() -> None:
    our_deps = _project_dependencies(load_our_pyproject())
    ha_deps = _project_dependencies(load_ha_pyproject())

    ha_pins: dict[str, Version] = {}
    for dep in ha_deps:
        requirement = Requirement(dep)
        exact_versions = [
            Version(specifier.version)
            for specifier in requirement.specifier
            if specifier.operator == "=="
        ]
        if exact_versions:
            ha_pins[_normalize_name(requirement.name)] = max(exact_versions)

    failures: list[str] = []
    for dep in our_deps:
        requirement = Requirement(dep)
        name = _normalize_name(requirement.name)
        our_floor = _highest_lower_bound(requirement)
        if our_floor is None:
            continue

        ha_pin = ha_pins.get(name)
        if ha_pin is None:
            _echo(f"OK: {name}>={our_floor} (not pinned by HA, skipped)")
            continue

        if our_floor > ha_pin:
            failures.append(f"  {name}>={our_floor} exceeds HA stable pin {ha_pin}")
            continue

        _echo(f"OK: {name}>={our_floor} <= HA stable {ha_pin}")

    if failures:
        _echo("FAIL: these dependency floors exceed HA current stable pins:")
        for failure in failures:
            _echo(failure)
        raise SystemExit(1)


def check_async_dep() -> None:
    failures: list[str] = []
    for path in _iter_library_files():
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "import requests" in line:
                failures.append(f"  {path}:{line_no}: 'import requests' (use aiohttp)")
            if "time.sleep(" in line:
                failures.append(
                    f"  {path}:{line_no}: 'time.sleep()' (use asyncio.sleep)"
                )

    if failures:
        _echo("FAIL: blocking I/O found in library source:")
        for failure in failures:
            _echo(failure)
        raise SystemExit(1)

    _echo("OK: no blocking I/O found in library source")


def check_inject_websession() -> None:
    failures: list[str] = []
    for path in _iter_library_files():
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "aiohttp.ClientSession()" in line:
                failures.append(
                    f"  {path}:{line_no}: internal aiohttp.ClientSession() construction"
                )

    if failures:
        _echo("FAIL: internal ClientSession construction found:")
        for failure in failures:
            _echo(failure)
        raise SystemExit(1)

    _echo("OK: no internal ClientSession construction found")


def check_py_typed() -> None:
    markers = [
        path
        for path in LIB_SRC.rglob("py.typed")
        if not any(part in EXCLUDED_PARTS for part in path.parts)
    ]
    if not markers:
        _fail(f"FAIL: no py.typed marker found under {LIB_SRC}/")

    _echo(f"OK: py.typed found at {markers[0]}")


def check_python_versions() -> None:
    ha_pyproject = load_ha_pyproject()
    our_pyproject = load_our_pyproject()

    ha_requires = _project_requires_python(ha_pyproject)
    our_requires = _project_requires_python(our_pyproject)

    ha_match = re.search(r"3\.(\d+)", ha_requires)
    our_match = re.search(r"3\.(\d+)", our_requires)

    if not ha_match:
        _fail(f"FAIL: could not parse HA requires-python: {ha_requires}")
    if not our_match:
        _fail(f"FAIL: could not parse our requires-python: {our_requires}")

    ha_minor = int(ha_match.group(1))
    our_minor_floor = int(our_match.group(1))

    if our_minor_floor > ha_minor - 1:
        _fail(
            f"FAIL: requires-python='{our_requires}' does not cover "
            f"HA previous minor 3.{ha_minor - 1}"
        )

    _echo(
        f"OK: requires-python='{our_requires}' covers HA previous/current "
        f"minor versions (3.{ha_minor - 1}, 3.{ha_minor})"
    )


def check_py_typed_wheel() -> None:
    dist_dir = Path("dist")
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        _fail("FAIL: no wheel found in dist/")

    found = False
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            if any(member.endswith("/py.typed") for member in archive.namelist()):
                found = True
                break

    if not found:
        _fail("FAIL: py.typed missing from built wheel")

    _echo("OK: py.typed found in built wheel")


COMMANDS = {
    "no-exact-pins": check_no_exact_pins,
    "dep-ceiling": check_dep_ceiling,
    "async-dep": check_async_dep,
    "inject-websession": check_inject_websession,
    "py-typed": check_py_typed,
    "python-versions": check_python_versions,
    "py-typed-wheel": check_py_typed_wheel,
}


if __name__ == "__main__":
    if len(sys.argv) != EXPECTED_ARGC or sys.argv[1] not in COMMANDS:
        _echo(f"Usage: check_ha_compliance.py <{'|'.join(COMMANDS)}>")
        raise SystemExit(2)
    COMMANDS[sys.argv[1]]()
