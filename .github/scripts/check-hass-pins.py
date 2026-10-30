"""Check this library's runtime dependency floors against Home Assistant's pins.

HA pins its core dependencies exactly (e.g. `aiohttp==3.14.3`), so our floors
must equal those pins:

  - a floor *below* HA's pin claims support for versions we never test against;
  - a floor *above* what HA stable pins makes the library uninstallable there,
    as HA's `==` pin can no longer satisfy it.

So the floors track HA stable (the `master` branch, which is the latest release);
`dev` is read only to give advance warning of a bump that is coming.

Only the deps in TRACKED are checked — dev/test deps are Renovate's business. A dep
HA no longer pins exactly belongs in UNPINNED instead: with no `==` to satisfy, our
floor cannot make the library uninstallable under HA, so it is ours to choose. Those
deps are only watched, in case HA pins them again.

The Python versions we support are also relative to those of HA stable: the one before
the one it requires, and the one it requires (see get-python-versions.py). The test
matrix follows HA by itself, but the settings in PYTHON_* have to be changed by hand, so
they are checked here. A change may bring new mypy errors, or end support for a Python.

Exits non-zero if a TRACKED floor no longer matches HA stable's pin, or if any of these
Python settings no longer agrees with the Python that HA stable requires.
"""

import logging
import os
import re
import tomllib
import urllib.request
from pathlib import Path

# runtime deps that must track HA's pins; see [project.dependencies]
TRACKED = ("aiohttp", "aiozoneinfo", "probatio")

# Runtime deps HA no longer pins, so there is no pin for us to track. None at present:
# HA 2026.9.0 replaced voluptuous with `probatio` (a clean-room, API-compatible
# reimplementation; see home-assistant/core#175128), which it pins exactly, and this
# library now imports probatio directly — so it is TRACKED, above.
UNPINNED: tuple[str, ...] = ()

STABLE = "master"  # HA cuts releases from master; dev is the next release
DEV = "dev"

CONSTRAINTS = "homeassistant/package_constraints.txt"  # flat `name==version` lines
CONST_PY = "homeassistant/const.py"
PYPROJECT = "pyproject.toml"

PYTHON_VERSION_FILE = ".python-version"
PYTHON_TYPE_WORKFLOW = ".github/workflows/check-type.yml"

ROOT = Path(
    __file__
).parent.parent.parent  # repo root (.github/scripts/ -> .github/ -> root)

_LOGGER = logging.getLogger(Path(__file__).stem)


class HassPinMismatchError(Exception):
    """A runtime dependency floor or a Python setting no longer matches HA's."""


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


def parse_ha_python(text: str) -> tuple[int, int]:
    """Return the (major, minor) of the requires-python of HA's pyproject.toml."""
    match = re.search(r'^requires-python\s*=\s*">=(\d+)\.(\d+)', text, re.MULTILINE)
    if not match:
        raise HassPinMismatchError("Could not parse requires-python from HA")
    return int(match[1]), int(match[2])


def parse_python_settings() -> dict[str, tuple[str, str | None]]:
    """Return each Python setting as (the policy's role for it, its current value)."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    floor = re.match(r">=(\d+\.\d+)", pyproject["project"]["requires-python"])
    target = re.fullmatch(r"py(\d)(\d+)", pyproject["tool"]["ruff"]["target-version"])
    type_check = re.search(
        r'python-version: \["(\d+\.\d+)"\]',
        (ROOT / PYTHON_TYPE_WORKFLOW).read_text(),
    )

    return {
        "requires-python": ("previous", floor[1] if floor else None),
        "tool.ruff.target-version": (
            "previous",
            f"{target[1]}.{target[2]}" if target else None,
        ),
        "tool.mypy.python_version": (
            "current",
            pyproject["tool"]["mypy"]["python_version"],
        ),
        PYTHON_VERSION_FILE: (
            "current",
            (ROOT / PYTHON_VERSION_FILE).read_text().strip(),
        ),
        PYTHON_TYPE_WORKFLOW: ("current", type_check[1] if type_check else None),
    }


def check_python(stable: tuple[int, int]) -> list[str]:
    """Return a mismatch for each Python setting that disagrees with HA stable."""
    expected = {
        "current": f"{stable[0]}.{stable[1]}",
        "previous": f"{stable[0]}.{stable[1] - 1}",
    }

    mismatches: list[str] = []
    for name, (role, value) in parse_python_settings().items():
        if value == expected[role]:
            _LOGGER.info("%s: %s matches HA's Python (%s)", name, value, role)
        else:
            mismatches.append(
                f"`{name}`: is `{value}`, but should be `{expected[role]}` "
                f"(HA stable requires Python `{expected['current']}`)"
            )
    return mismatches


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
    """Compare our floors & Python with HA's; raise if they have drifted."""
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
            warnings.append(
                f"`{name}`: HA dev is on `=={ahead}` (stable `=={pin}`) — a bump is coming"
            )

    warnings.extend(
        f"`{name}`: HA pins `=={pin}` again — move it to TRACKED?"
        for name in map(normalise, UNPINNED)
        if (pin := stable.get(name))
    )

    stable_python = parse_ha_python(fetch(STABLE, PYPROJECT))
    dev_python = parse_ha_python(fetch(DEV, PYPROJECT))

    mismatches.extend(check_python(stable_python))

    if dev_python > stable_python:
        warnings.append(
            f"HA dev requires Python `{dev_python[0]}.{dev_python[1]}` "
            f"(stable `{stable_python[0]}.{stable_python[1]}`) — a bump is coming"
        )

    for warning in warnings:
        _LOGGER.warning("%s", warning)

    write_summary(
        [f"### Runtime deps & Python vs Home Assistant {version}", ""]
        + [f"- ❌ {line}" for line in mismatches]
        + [f"- ⚠️ {line}" for line in warnings]
        + ([] if mismatches else ["- ✅ all tracked floors & Python match HA stable"])
    )

    if mismatches:
        raise HassPinMismatchError(
            f"Runtime deps or Python have drifted from HA {version}: "
            + "; ".join(mismatches)
        )


if __name__ == "__main__":
    main()
