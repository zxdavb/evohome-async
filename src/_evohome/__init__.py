"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

try:
    from ._version import __version__  # type: ignore[import-not-found]
except ImportError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
