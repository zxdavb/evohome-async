"""Build the Python test matrix for GitHub Actions.

The Python versions we support are defined relative to those of HA stable (the
`master` branch, which is the latest release):

  - the version before the one HA requires;
  - the version HA requires;
  - the version after the one HA requires, if (and only if) it has been released.

A release is determined via endoflife.date. If it, or HA's pyproject.toml, is
unavailable then the script exits with an error, as the matrix depends upon both.

Each entry is a cycle (e.g. "3.15"), not its latest patch (e.g. "3.15.0"): a new
patch is listed by endoflife.date before actions/python-versions publishes a build
for it, so an exact patch can fail setup-python.

The settings that must agree with this policy are checked by check-hass-pins.py.

Writes a JSON array to $GITHUB_OUTPUT as `matrix=["3.x", ...]`.
"""

import json
import os
import re
import urllib.request
from datetime import UTC, datetime as dt
from pathlib import Path

with urllib.request.urlopen(
    "https://raw.githubusercontent.com/home-assistant/core/master/pyproject.toml",
    timeout=10,
) as r:
    content = r.read().decode()

_rp = re.search(r'requires-python\s*=\s*">=(\d+)\.(\d+)', content)
if not _rp:
    raise ValueError("Could not parse requires-python from HA's pyproject.toml")
MAJOR, MINOR = int(_rp.group(1)), int(_rp.group(2))

with urllib.request.urlopen("https://endoflife.date/api/python.json", timeout=10) as r:
    cycles = json.loads(r.read())
today = dt.now(tz=UTC).date().isoformat()
released = {c["cycle"] for c in cycles if c["releaseDate"] <= today}

versions = [f"{MAJOR}.{MINOR - 1}", f"{MAJOR}.{MINOR}"]
if (upcoming := f"{MAJOR}.{MINOR + 1}") in released:
    versions.append(upcoming)

with Path(os.environ["GITHUB_OUTPUT"]).open("a") as f:
    f.write(f"matrix={json.dumps(versions)}\n")
