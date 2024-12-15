#!/usr/bin/env python3
"""A CLI for the evohome-sync2 library."""

import sys

try:
    from cli.client import main

except ModuleNotFoundError:
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent / "cli"))
    sys.path.append(str(Path(__file__).parent / "src"))

    from cli.client import main

if __name__ == "__main__":
    main()
