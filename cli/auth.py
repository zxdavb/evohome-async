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

from evohomeasync.auth import SZ_SESSION_ID_EXPIRES, AbstractSessionManager, SessionIdT
from evohomeasync2.auth import (
    SZ_ACCESS_TOKEN_EXPIRES,
    AbstractTokenManager,
    AuthTokensT,
)

TOKEN_CACHE: Final = Path(tempfile.gettempdir() + "/.evo-cache.tmp")


SZ_AUTH_TOKENS: Final = "auth_tokens"
SZ_SESSION_ID: Final = "session_id"


class UserEntryT(TypedDict):
    auth_tokens: NotRequired[AuthTokensT]
    session_id: NotRequired[SessionIdT]


# class TokenCacheT(TypedDict, total=False):
#     __root__: dict[str, UserEntry]


TokenCacheT = dict[str, UserEntryT]


class CacheManager(AbstractTokenManager, AbstractSessionManager):
    """A token manager that uses a cache file to store the tokens."""

    def __init__(
        self, *args: Any, token_cache: Path | None = None, **kwargs: Any
    ) -> None:
        """Initialise the token manager."""
        super().__init__(*args, **kwargs)

        self._token_cache: Final = token_cache

        self._clear_auth_tokens()
        self._clear_session_id()

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
            user_data: UserEntryT = {}

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

        cache: TokenCacheT = json.loads(content)
        return cache

    async def _write_cache_to_file(self, cache: TokenCacheT) -> None:
        """Write the supplied cache to file."""

        content = json.dumps(cache)

        async with aiofiles.open(self.token_cache, "w") as fp:
            await fp.write(content)

    async def load_cache(self) -> None:
        """Load the user entry from the cache."""

        cache: TokenCacheT = await self._read_cache_from_file()

        await self._load_access_token(cache=cache)
        await self._load_session_id(cache=cache)

    async def _load_access_token(self, cache: TokenCacheT | None = None) -> None:
        """Load the (serialized) auth tokens from the cache."""

        cache = cache or await self._read_cache_from_file()

        if not (entry := cache.get(self.client_id)):
            return

        if not (tokens := entry.get(SZ_AUTH_TOKENS)):
            return

        # if not self._access_token:  # not needed as dt.min is sentinel for this
        if self._access_token_expires.isoformat() < tokens[SZ_ACCESS_TOKEN_EXPIRES]:
            self._import_auth_tokens(tokens)

    async def _load_session_id(self, cache: TokenCacheT | None = None) -> None:
        """Load the (serialized) session id from the cache."""

        cache = cache or await self._read_cache_from_file()

        if not (entry := cache.get(self.client_id)):
            return

        if not (session := entry.get(SZ_SESSION_ID)):
            return

        # if not self._session_id:  # not needed as dt.min is sentinel for this
        if self._session_expires.isoformat() < session[SZ_SESSION_ID_EXPIRES]:
            self._import_session_id(session)

    async def save_access_token(self) -> None:
        """Save the (serialized) auth tokens to the cache."""

        cache: TokenCacheT = await self._read_cache_from_file()

        if self.client_id not in cache:
            cache[self.client_id] = {}

        cache[self.client_id][SZ_AUTH_TOKENS] = self._export_auth_tokens()

        await self._write_cache_to_file(self._clean_cache(cache))

    async def save_session_id(self) -> None:
        """Save the (serialized) session id to the cache."""

        cache: TokenCacheT = await self._read_cache_from_file()

        if self.client_id not in cache:
            cache[self.client_id] = {}

        cache[self.client_id][SZ_SESSION_ID] = self._export_session_id()

        await self._write_cache_to_file(self._clean_cache(cache))