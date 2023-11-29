"""A CLI for the evohome-sync2 library."""

import sys

try:
    from evohomeasync2.client import main

except ModuleNotFoundError:
    import os

    sys.path.append(f"{os.path.dirname(__file__)}/src")

    from evohomeasync2.client import main

if __name__ == "__main__":
    main()
