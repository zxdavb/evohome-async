#!/usr/bin/env python3
"""Tests for evohome-async."""

from __future__ import annotations

from datetime import datetime as dt
from pathlib import Path
from typing import Any, Final

import evohomeasync as evo1
import evohomeasync2 as evo2


class SessionManager(evo1.Auth):
    """An evohomeasync session manager."""

    def __init__(
        self, *args: Any, token_cache: Path | None = None, **kwargs: Any
    ) -> None:
        """Initialise the session manager."""
        super().__init__(*args, **kwargs)

        self._token_cache: Final = token_cache

    async def save_session_id(self) -> None:
        """Save the (serialized) session id to a cache."""

    async def load_session_id(self) -> None:
        """Save the (serialized) session id from a cache."""


class TokenManager(evo2.AbstractTokenManager):
    """An evohomeasync token manager."""

    def __init__(
        self, *args: Any, token_cache: Path | None = None, **kwargs: Any
    ) -> None:
        """Initialise the token manager."""
        super().__init__(*args, **kwargs)

        self._token_cache: Final = token_cache

    async def restore_access_token(self) -> None:
        """Restore the access token from the cache."""

        self._access_token = "access_token"  # noqa: S105
        self._access_token_expires = dt.max
        self._refresh_token = "refresh_token"  # noqa: S105

    async def save_access_token(self) -> None:
        """Save the access token to the cache."""
        pass
