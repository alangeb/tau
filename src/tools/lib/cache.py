"""Shared file-based cache for tool modules.

Provides a simple TTL-based file cache that eliminates duplicated
_cleanup_cache / _load_cache / _save_cache code across tools.

Usage:
    _fetch_cache = FileCache("tau_fetch_cache", ttl=3600, extension=".md")
    _lookup_cache = FileCache("tau_lookup_cache", ttl=3600)
    _search_cache = FileCache("tau_search_cache", ttl=300)

    # Load (returns None on miss/expiry):
    result = _fetch_cache.load(key)
    if result is not None:
        return result

    # Save (auto-creates dir, auto-cleans stale files):
    _fetch_cache.save(key, data)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

__all__ = ["FileCache"]


class FileCache:
    """Simple TTL-based file cache.

    Each instance owns a cache directory under TMPDIR (or /tmp).
    Files are stored as <key><extension>.
    On save, stale files (older than *ttl*) are cleaned up.
    """

    def __init__(
        self,
        name: str,
        ttl: int = 3600,
        *,
        extension: str = ".json",
    ) -> None:
        """Create a cache instance.

        Args:
            name: Subdirectory name under TMPDIR (e.g. "tau_fetch_cache").
            ttl: Time-to-live in seconds for cached entries.
            extension: File extension for cached entries (default ".json").
        """
        self._dir = os.path.join(os.getenv("TMPDIR", "/tmp"), name)
        self._ttl = ttl
        self._ext = extension

    def _path(self, key: str) -> str:
        return os.path.join(self._dir, f"{key}{self._ext}")

    def cleanup(self) -> None:
        """Remove stale cache files older than *ttl* seconds."""
        try:
            cutoff = time.time() - self._ttl
            for fname in os.listdir(self._dir):
                fpath = os.path.join(self._dir, fname)
                if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
        except OSError:
            pass

    def load(self, key: str) -> Any | None:
        """Load a cached entry by key.

        Returns None if the file does not exist or has expired.
        JSON files are deserialized; other files are returned as strings.
        """
        path = self._path(key)
        if not os.path.exists(path):
            return None
        if time.time() - os.path.getmtime(path) > self._ttl:
            return None
        with open(path, "r") as f:
            if self._ext == ".json":
                return json.load(f)
            return f.read()

    def save(self, key: str, data: Any) -> None:
        """Save data to cache under *key*.

        Auto-creates the cache directory and cleans up stale files.
        JSON files are serialized; other data is written as-is (must be str).
        """
        os.makedirs(self._dir, exist_ok=True)
        self.cleanup()
        path = self._path(key)
        with open(path, "w") as f:
            if self._ext == ".json":
                json.dump(data, f)
            else:
                f.write(data)
