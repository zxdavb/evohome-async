"""Tests for evohome-async."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime as dt, timedelta as td
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, NotRequired, TypedDict

import aiofiles
import aiofiles.os

from evohomeasync.auth import (
    SZ_SESSION_ID,
    SZ_SESSION_ID_EXPIRES,
    AbstractSessionManager,
)
from evohomeasync2.auth import (
    SZ_ACCESS_TOKEN,
    SZ_ACCESS_TOKEN_EXPIRES,
    AbstractTokenManager,
)

if TYPE_CHECKING:
    from evohomeasync.auth import SessionIdEntryT
    from evohomeasync2.auth import AccessTokenEntryT


CACHE_FILE: Final = Path(tempfile.gettempdir()) / ".evo-cache.tmp"


class UserEntryT(TypedDict):
    access_token: NotRequired[AccessTokenEntryT]
    session_id: NotRequired[SessionIdEntryT]


CacheDataT = dict[str, UserEntryT]  # str is the client_id

"""
{
    "username@gmail.com": {
        "access_token": {
            "access_token": "iiuyz2-...",
            "access_token_expires": "2024-09-24T10:25:12+01:00",
            "refresh_token": "dfsadgf..."
            },
        "session_id": {
            "session_id": "94A76CB4-8BD4-4600-AAE4-...",
            "session_id_expires": "2024-09-24T10:25:12+01:00"
        }
    },
    "username@email.com": {}
  }
"""


class CredentialsManager(AbstractTokenManager, AbstractSessionManager):
    """A credentials manager that uses a file to cache the tokens."""

    def __init__(
        self, *args: Any, cache_file: Path | None = None, **kwargs: Any
    ) -> None:
        """Initialise the credentials manager (for access_token & session_id)."""
        super().__init__(*args, **kwargs)

        self._cache_file: Final = cache_file

    @property
    def cache_file(self) -> str:
        """Return the token cache path."""
        return str(self._cache_file)

    @staticmethod
    def _clean_cache(old_cache: CacheDataT) -> CacheDataT:
        """Return a copy of a cache with any expired data removed."""

        new_cache: CacheDataT = {}

        dt_now = (dt.now(tz=UTC) + td(seconds=15)).isoformat()

        for user_id, entry in old_cache.items():
            user_data: UserEntryT = {}

            if (t := entry.get(SZ_ACCESS_TOKEN)) and t[
                SZ_ACCESS_TOKEN_EXPIRES
            ] > dt_now:
                user_data[SZ_ACCESS_TOKEN] = t

            # session_id is not used by evohomeasync2
            if (s := entry.get(SZ_SESSION_ID)) and s[SZ_SESSION_ID_EXPIRES] > dt_now:
                user_data[SZ_SESSION_ID] = s

            if user_data:
                new_cache[user_id] = user_data

        return new_cache  # could be Falsey

    async def _read_cache_from_file(self) -> CacheDataT:
        """Return a copy of the cache as read from file."""

        try:
            async with aiofiles.open(self.cache_file) as fp:
                content = await fp.read() or "{}"
        except FileNotFoundError:
            return {}

        cache: CacheDataT = json.loads(content)
        return cache

    async def _write_cache_to_file(self, cache: CacheDataT) -> None:
        """Write the supplied cache to file."""

        content = json.dumps(cache, indent=4)

        async with aiofiles.open(self.cache_file, "w") as fp:
            await fp.write(content)

    async def load_from_cache(self) -> None:
        """Load the user entry from the cache."""

        cache: CacheDataT = await self._read_cache_from_file()

        await self._load_access_token(cache=cache)
        await self._load_session_id(cache=cache)

    async def _load_access_token(self, cache: CacheDataT | None = None) -> None:
        """Load the (serialized) auth tokens from the cache."""

        cache = cache or await self._read_cache_from_file()

        entry: UserEntryT | None = cache.get(self.client_id)
        if not entry:
            return

        tokens: AccessTokenEntryT | None = entry.get(SZ_ACCESS_TOKEN)
        if not tokens:
            return

        # if not self._access_token:  # not needed as dt.min is sentinel for this
        if self._access_token_expires.isoformat() < tokens[SZ_ACCESS_TOKEN_EXPIRES]:
            self._import_access_token(tokens)

    async def _load_session_id(self, cache: CacheDataT | None = None) -> None:
        """Load the (serialized) session id from the cache."""

        cache = cache or await self._read_cache_from_file()

        entry: UserEntryT | None = cache.get(self.client_id)
        if not entry:
            return

        session: SessionIdEntryT | None = entry.get(SZ_SESSION_ID)
        if not session:
            return

        # if not self._session_id:  # not needed as dt.min is sentinel for this
        if self._session_id_expires.isoformat() < session[SZ_SESSION_ID_EXPIRES]:
            self._import_session_id(session)

    async def save_to_cache(self) -> None:
        """Save the user entry to the cache."""

        await self.save_access_token()
        await self.save_session_id()

    async def save_access_token(self) -> None:
        """Save the (serialized) access token to the cache.

        Includes the access token expiry datetime, and the refresh token.
        """

        cache: CacheDataT = await self._read_cache_from_file()

        if self.client_id not in cache:
            cache[self.client_id] = {}

        cache[self.client_id][SZ_ACCESS_TOKEN] = self._export_access_token()

        await self._write_cache_to_file(self._clean_cache(cache))

    async def save_session_id(self) -> None:
        """Save the (serialized) session id to the cache.

        Includes the session id expiry datetime.
        """

        cache: CacheDataT = await self._read_cache_from_file()

        if self.client_id not in cache:
            cache[self.client_id] = {}

        cache[self.client_id][SZ_SESSION_ID] = self._export_session_id()

        await self._write_cache_to_file(self._clean_cache(cache))
