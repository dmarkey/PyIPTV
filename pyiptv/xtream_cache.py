"""Time-based JSON cache for Xtream fetches (channels + categories).

The existing M3UCacheManager keys on file size/mtime which doesn't apply to
live API responses, so this is a separate tiny cache. Payload shape mirrors
what `M3UParser.parse_m3u_from_content` returns so MainWindow can consume
either interchangeably.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import time
from typing import Optional, Tuple

DEFAULT_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _key(server_url: str, username: str) -> str:
    raw = f"{server_url}|{username}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _cache_path(cache_dir: str, server_url: str, username: str) -> str:
    return os.path.join(cache_dir, f"xtream_{_key(server_url, username)}.pkl")


def save(
    cache_dir: str,
    server_url: str,
    username: str,
    channels: list,
    categories: dict,
) -> str:
    """Write (channels, categories) to the cache. Returns the file path."""
    os.makedirs(cache_dir, exist_ok=True)
    path = _cache_path(cache_dir, server_url, username)
    payload = {
        "cached_at": time.time(),
        "channels": channels,
        "categories": categories,
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)
    return path


def load(
    cache_dir: str,
    server_url: str,
    username: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Optional[Tuple[list, dict]]:
    """Return (channels, categories) if cache exists and is fresh, else None.

    ttl_seconds=0 disables freshness check — caller gets whatever's cached,
    useful for offline degraded-mode reads.
    """
    path = _cache_path(cache_dir, server_url, username)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError):
        return None
    if ttl_seconds > 0:
        age = time.time() - payload.get("cached_at", 0)
        if age > ttl_seconds:
            return None
    return payload.get("channels", []), payload.get("categories", {})


def load_stale(
    cache_dir: str, server_url: str, username: str
) -> Optional[Tuple[list, dict]]:
    """Load the cache regardless of age (for offline fallback)."""
    return load(cache_dir, server_url, username, ttl_seconds=0)


def invalidate(cache_dir: str, server_url: str, username: str) -> bool:
    path = _cache_path(cache_dir, server_url, username)
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except OSError:
            return False
    return False
