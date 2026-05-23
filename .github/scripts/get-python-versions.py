"""Build the Python test matrix for GitHub Actions.

Queries endoflife.date for all non-EOL CPython versions >= the project's
requires-python floor (read from pyproject.toml). If the API is unavailable
the script exits with an error. Also adds HA dev's required Python if it is
a pre-release not yet listed on endoflife.date.

Writes a JSON array to $GITHUB_OUTPUT as `matrix=["3.x.y", ...]`.
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent.parent  # repo root

# Floor derived from requires-python in pyproject.toml — fail loudly if missing
_rp = re.search(
    r'requires-python\s*=\s*">=(\d+)\.(\d+)',
    (ROOT / "pyproject.toml").read_text(),
)
if not _rp:
    raise ValueError("Could not parse requires-python from pyproject.toml")
FLOOR = (int(_rp.group(1)), int(_rp.group(2)))

# All non-EOL Python versions >= floor from endoflife.date
with urllib.request.urlopen("https://endoflife.date/api/python.json", timeout=10) as r:
    cycles = json.loads(r.read())
today = dt.now(tz=UTC).date().isoformat()
versions: list[str] = sorted(
    c["latest"]
    for c in cycles
    if c["eol"] > today and tuple(int(x) for x in c["cycle"].split(".")) >= FLOOR
)

# Also include HA dev's required Python if it's a pre-release not yet on endoflife.date
try:
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/home-assistant/core/dev/pyproject.toml",
        timeout=10,
    ) as r:
        content = r.read().decode()
    m = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)', content)
    if m:
        ha_minor = m.group(1)
        if not any(v.startswith(ha_minor + ".") or v == ha_minor for v in versions):
            versions.append(ha_minor)  # minor-only; allow-prereleases resolves latest
            versions.sort()
except (urllib.error.URLError, OSError, ValueError):
    pass  # best-effort; HA's version is normally covered by endoflife.date

with Path(os.environ["GITHUB_OUTPUT"]).open("a") as f:
    f.write(f"matrix={json.dumps(versions)}\n")
