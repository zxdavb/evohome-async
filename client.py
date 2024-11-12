"""A CLI for the evohome-sync2 library."""

import sys

try:
    from cli.client import main

except ModuleNotFoundError:
    import os

    sys.path.append(f"{os.path.dirname(__file__)}/cli")
    sys.path.append(f"{os.path.dirname(__file__)}/src")

    from cli.client import main

if __name__ == "__main__":
    main()
