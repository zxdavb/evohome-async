"""Check this library's runtime dependency floors against Home Assistant's pins.

HA pins its core dependencies exactly (e.g. `aiohttp==3.14.3`), so our floors
must equal those pins:

  - a floor *below* HA's pin claims support for versions we never test against;
  - a floor *above* what HA stable pins makes the library uninstallable there,
    as HA's `==` pin can no longer satisfy it.

So the floors track HA stable (the `master` branch, which is the latest release);
`dev` is read only to give advance warning of a bump that is coming.

Only the deps in TRACKED are checked — dev/test deps are Renovate's business.
Exits non-zero if a floor no longer matches HA stable's pin.
"""

import logging
import os
import re
import tomllib
import urllib.request
from pathlib import Path

# runtime deps that must track HA's pins; see [project.dependencies]
TRACKED = ("aiohttp", "aiozoneinfo", "voluptuous")

STABLE = "master"  # HA cuts releases from master; dev is the next release
DEV = "dev"

CONSTRAINTS = "homeassistant/package_constraints.txt"  # flat `name==version` lines
CONST_PY = "homeassistant/const.py"

ROOT = Path(
    __file__
).parent.parent.parent  # repo root (.github/scripts/ -> .github/ -> root)

_LOGGER = logging.getLogger(Path(__file__).stem)


class HassPinMismatchError(Exception):
    """A runtime dependency floor no longer matches Home Assistant's pin."""


def normalise(name: str) -> str:
    """Return a PEP 503 normalised distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def fetch(ref: str, path: str) -> str:
    """Return a file from home-assistant/core (raises: the check must fail loudly)."""
    with urllib.request.urlopen(
        f"https://raw.githubusercontent.com/home-assistant/core/{ref}/{path}",
        timeout=10,
    ) as rsp:
        body: bytes = rsp.read()
    return body.decode()


def parse_pins(text: str) -> dict[str, str]:
    """Return the `name==version` pins of a constraints file, keyed by name."""
    matches = (re.match(r"([\w.-]+)==([^\s;#]+)", line) for line in text.splitlines())
    return {normalise(m[1]): m[2] for m in matches if m}


def parse_floors() -> dict[str, str]:
    """Return the `name>=version` floors of [project.dependencies], keyed by name."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    matches = (
        re.fullmatch(r"([\w.-]+)>=([^\s,;]+)", spec)
        for spec in pyproject["project"]["dependencies"]
    )
    return {normalise(m[1]): m[2] for m in matches if m}


def version_key(version: str) -> tuple[int, ...]:
    """Return an orderable key for a version string (numeric segments only)."""
    return tuple(int(segment) for segment in re.findall(r"\d+", version))


def ha_version() -> str:
    """Return HA stable's version, e.g. '2026.7.4' (best-effort: it is cosmetic)."""
    try:
        const = fetch(STABLE, CONST_PY)
    except (OSError, ValueError):
        return "unknown"

    parts = [
        re.search(rf'^{part}_VERSION: Final = "?([\w.]+)"?', const, re.MULTILINE)
        for part in ("MAJOR", "MINOR", "PATCH")
    ]
    return ".".join(m[1] for m in parts if m) if all(parts) else "unknown"


def write_summary(lines: list[str]) -> None:
    """Append lines to the GitHub Actions step summary, when running in CI."""
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a") as f:
            f.write("\n".join(lines) + "\n")


def main() -> None:
    """Compare our floors with HA's pins; raise if they have drifted."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    floors = parse_floors()
    stable = parse_pins(fetch(STABLE, CONSTRAINTS))
    dev = parse_pins(fetch(DEV, CONSTRAINTS))

    version = ha_version()
    _LOGGER.info("Comparing [project.dependencies] with HA %s (%s)", version, STABLE)

    mismatches: list[str] = []
    warnings: list[str] = []

    for name in map(normalise, TRACKED):
        floor, pin = floors.get(name), stable.get(name)

        if floor is None:
            mismatches.append(f"`{name}`: no `>=` floor in [project.dependencies]")
            continue
        if pin is None:
            mismatches.append(f"`{name}`: not pinned by HA — still a core dep?")
            continue

        if floor != pin:
            mismatches.append(f"`{name}`: floor `>={floor}` != HA's `=={pin}`")
        else:
            _LOGGER.info("%s: >=%s matches HA's pin", name, floor)

        if (ahead := dev.get(name)) and version_key(ahead) > version_key(pin):
            warnings.append(f"`{name}`: HA dev is on `=={ahead}` (stable `=={pin}`)")

    for warning in warnings:
        _LOGGER.warning("A bump is coming — %s", warning)

    write_summary(
        [f"### Runtime deps vs Home Assistant {version}", ""]
        + [f"- ❌ {line}" for line in mismatches]
        + [f"- ⚠️ {line} — a bump is coming" for line in warnings]
        + ([] if mismatches else ["- ✅ all tracked floors match HA stable"])
    )

    if mismatches:
        raise HassPinMismatchError(
            f"Runtime dependency floors have drifted from HA {version}: "
            + "; ".join(mismatches)
        )


if __name__ == "__main__":
    main()
