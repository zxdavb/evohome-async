#!/usr/bin/env python3
"""Tests for evohome-async."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime as dt, timedelta as td
from pathlib import Path
from typing import Any, Final, NotRequired, TypedDict

import aiofiles
import aiofiles.os

import evohomeasync2 as evo2
from evohomeasync.auth import SZ_SESSION_ID_EXPIRES
from evohomeasync2.auth import SZ_ACCESS_TOKEN_EXPIRES

TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tmp")


class SessionId(TypedDict):
    session_id: str
    session_id_expires: str


class AuthTokens(TypedDict):
    access_token: str
    access_token_expires: str
    refresh_token: str


SZ_AUTH_TOKENS: Final = "auth_tokens"
SZ_SESSION_ID: Final = "session_id"


class UserEntry(TypedDict):
    auth_tokens: NotRequired[AuthTokens]
    session_id: NotRequired[SessionId]


# class TokenCacheT(TypedDict, total=False):
#     __root__: dict[str, UserEntry]


TokenCacheT = dict[str, UserEntry]


class TokenManager(evo2.AbstractTokenManager):
    """A token manager that uses a cache file to store the tokens."""

    def __init__(
        self, *args: Any, token_cache: Path | None = None, **kwargs: Any
    ) -> None:
        """Initialise the token manager."""
        super().__init__(*args, **kwargs)

        self._token_cache: Final = token_cache

    @property
    def token_cache(self) -> str:
        """Return the token cache path."""
        return str(self._token_cache)

    @staticmethod
    def _clean_cache(old_cache: TokenCacheT) -> TokenCacheT:
        """Clear any expired data from the cache entry."""

        new_cache: TokenCacheT = {}

        dt_now = (dt.now() + td(seconds=15)).isoformat()

        for user_id, entry in old_cache.items():
            user_data: UserEntry = {}

            if (t := entry.get(SZ_AUTH_TOKENS)) and t[SZ_ACCESS_TOKEN_EXPIRES] > dt_now:
                user_data[SZ_AUTH_TOKENS] = t

            # session_id is not used by evohomeasync2
            if (s := entry.get(SZ_SESSION_ID)) and s[SZ_SESSION_ID_EXPIRES] > dt_now:
                user_data[SZ_SESSION_ID] = s

            if user_data:
                new_cache[user_id] = user_data

        return new_cache  # could be Falsey

    async def _read_cache_from_file(self) -> TokenCacheT:
        """Return a copy of the cache as read from file."""

        try:
            async with aiofiles.open(self.token_cache) as fp:
                content = await fp.read() or "{}"
        except FileNotFoundError:
            return {}

        return json.loads(content)

    async def _write_cache_to_file(self, cache: TokenCacheT) -> None:
        """Writen the supplied cache to file."""

        content = json.dumps(cache)

        async with aiofiles.open(self.token_cache, "w") as fp:
            await fp.write(content)

    async def load_access_token(self) -> None:
        """Load the (serialized) auth tokens from the cache."""

        cache: TokenCacheT = await self._read_cache_from_file()

        if not (entry := cache.get(self.client_id)):
            return

        if not self._access_token:
            self._import_auth_token(entry)
            return

        if self._access_token_expires.isoformat() < entry[SZ_ACCESS_TOKEN_EXPIRES]:
            self._import_auth_token(entry)

    async def save_access_token(self) -> None:
        """Save the (serialized) auth tokens to the cache."""

        cache: TokenCacheT = await self._read_cache_from_file()

        if self.client_id not in cache:
            cache[self.client_id] = {}

        if SZ_AUTH_TOKENS not in cache[self.client_id]:
            cache[self.client_id][SZ_AUTH_TOKENS] = {}

        cache[self.client_id][SZ_AUTH_TOKENS] = self._export_auth_token()

        self._write_cache_to_file(self._clean_cache(cache))
