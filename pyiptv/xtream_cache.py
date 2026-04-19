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
EPG_TTL_SECONDS = 60 * 60  # 1 hour — EPG turns over fast, but programs don't

# Bumped when the channel-dict schema changes so we can invalidate older
# caches silently on load rather than keeping stale data around.
# v2: added xtream_tv_archive / xtream_tv_archive_duration for catchup.
CACHE_SCHEMA_VERSION = 2


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
    user_info: Optional[dict] = None,
) -> str:
    """Write (channels, categories, user_info) to the cache. Returns the file path."""
    os.makedirs(cache_dir, exist_ok=True)
    path = _cache_path(cache_dir, server_url, username)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "cached_at": time.time(),
        "channels": channels,
        "categories": categories,
        "user_info": user_info or {},
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)
    return path


def load(
    cache_dir: str,
    server_url: str,
    username: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Optional[Tuple[list, dict, dict]]:
    """Return (channels, categories, user_info) if cache exists and is fresh, else None.

    ttl_seconds=0 disables freshness check — caller gets whatever's cached,
    useful for offline degraded-mode reads.

    user_info is {} for caches written before v1.1 (backward-compat).
    """
    path = _cache_path(cache_dir, server_url, username)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError):
        return None
    # Invalidate caches written before the current schema so we don't serve
    # channel dicts missing newer fields (e.g. catchup flags).
    if payload.get("schema_version", 0) != CACHE_SCHEMA_VERSION:
        return None
    if ttl_seconds > 0:
        age = time.time() - payload.get("cached_at", 0)
        if age > ttl_seconds:
            return None
    return (
        payload.get("channels", []),
        payload.get("categories", {}),
        payload.get("user_info", {}),
    )


def load_stale(
    cache_dir: str, server_url: str, username: str
) -> Optional[Tuple[list, dict, dict]]:
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


def _epg_path(cache_dir: str, server_url: str, username: str) -> str:
    return os.path.join(cache_dir, f"epg_{_key(server_url, username)}.pkl")


def save_epg(
    cache_dir: str, server_url: str, username: str, epg_index: dict
) -> str:
    """Persist the parsed EPG index (channel_id → program list)."""
    os.makedirs(cache_dir, exist_ok=True)
    path = _epg_path(cache_dir, server_url, username)
    payload = {"cached_at": time.time(), "epg_index": epg_index}
    with open(path, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def load_epg(
    cache_dir: str,
    server_url: str,
    username: str,
    ttl_seconds: int = EPG_TTL_SECONDS,
) -> Optional[dict]:
    """Return the cached EPG index if present and fresh, else None."""
    path = _epg_path(cache_dir, server_url, username)
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
    return payload.get("epg_index", {})


def invalidate_epg(cache_dir: str, server_url: str, username: str) -> bool:
    path = _epg_path(cache_dir, server_url, username)
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except OSError:
            return False
    return False
