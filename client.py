"""A CLI for the evohome-sync2 library."""

# import tracemalloc
# tracemalloc.start()

import sys

try:
    from evohomeasync2.utils import main

except ModuleNotFoundError:
    import os

    sys.path.append(f"{os.path.dirname(__file__)}/src")

    from evohomeasync2.utils import main

if __name__ == "__main__":
    main()
