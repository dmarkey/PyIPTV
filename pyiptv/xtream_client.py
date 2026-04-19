"""
Xtream Codes panel API client.

Authenticates against `player_api.php` and fetches live categories/streams,
transforming the JSON into PyIPTV's channel-dict shape so the UI pipeline
(virtualized channel list, category list, media player) can consume it
interchangeably with M3U-parsed playlists.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests


def format_user_info(user_info: dict) -> Optional[str]:
    """Format Xtream user_info for display. Returns None if nothing useful.

    Expects the server's `user_info` block (exp_date, max_connections,
    active_cons, status). All fields are strings or unix-timestamp strings
    in the wild.
    """
    if not user_info:
        return None

    parts = []

    status = str(user_info.get("status", "")).strip()
    if status and status.lower() != "active":
        parts.append(f"account {status}")

    exp_raw = user_info.get("exp_date")
    if exp_raw:
        try:
            exp = datetime.fromtimestamp(int(exp_raw), tz=timezone.utc)
            days = (exp - datetime.now(tz=timezone.utc)).days
            if days < 0:
                parts.append("EXPIRED")
            elif days == 0:
                parts.append("expires today")
            elif days <= 7:
                parts.append(f"expires in {days} day{'s' if days != 1 else ''}")
            else:
                parts.append(f"expires {exp.strftime('%Y-%m-%d')}")
        except (ValueError, TypeError, OSError):
            pass

    active = user_info.get("active_cons")
    max_cons = user_info.get("max_connections")
    if active is not None and max_cons is not None:
        parts.append(f"{active}/{max_cons} connections")

    return " · ".join(parts) if parts else None


class XtreamError(Exception):
    """Base class for Xtream client failures."""


class XtreamAuthError(XtreamError):
    """Authentication failed or account not in a usable state."""


class XtreamNetworkError(XtreamError):
    """Network- or protocol-level failure reaching the server."""


def normalize_server_url(url: str) -> str:
    """
    Accept the loose forms users paste — `host:port`, `http://host/`,
    `https://host:8080` — and return a clean `scheme://netloc` (no trailing
    slash, no path).
    """
    url = url.strip()
    if not url:
        raise ValueError("Server URL is empty")
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid server URL: {url}")
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


class XtreamClient:
    """Stateless client wrapping player_api.php."""

    DEFAULT_TIMEOUT = 30
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.server_url = normalize_server_url(server_url)
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})
        self._epg_cache: Dict[int, Tuple[float, list]] = {}

    def _api_url(self) -> str:
        return f"{self.server_url}/player_api.php"

    def _request(self, params: dict):
        full = {"username": self.username, "password": self.password, **params}
        try:
            resp = self._session.get(
                self._api_url(), params=full, timeout=self.timeout
            )
        except requests.RequestException as e:
            raise XtreamNetworkError(f"Failed to reach {self.server_url}: {e}") from e
        if resp.status_code == 401 or resp.status_code == 403:
            raise XtreamAuthError(f"Server rejected credentials (HTTP {resp.status_code})")
        if resp.status_code != 200:
            raise XtreamNetworkError(f"HTTP {resp.status_code} from server")
        try:
            return resp.json()
        except ValueError as e:
            raise XtreamNetworkError(f"Server returned non-JSON response: {e}") from e

    def authenticate(self) -> dict:
        """
        Hit player_api.php with no action to retrieve user_info + server_info.
        Raises XtreamAuthError if the account isn't active.
        """
        data = self._request({})
        if not isinstance(data, dict):
            raise XtreamAuthError("Unexpected auth response shape")
        user_info = data.get("user_info") or {}
        auth_flag = user_info.get("auth")
        if str(auth_flag) != "1":
            message = user_info.get("message") or "authentication failed"
            raise XtreamAuthError(f"Login rejected: {message}")
        status = str(user_info.get("status", "")).strip()
        if status and status.lower() not in ("active",):
            raise XtreamAuthError(f"Account status is '{status}'")
        return data

    def get_live_categories(self) -> List[dict]:
        data = self._request({"action": "get_live_categories"})
        return data if isinstance(data, list) else []

    def get_live_streams(self, category_id: Optional[str] = None) -> List[dict]:
        params = {"action": "get_live_streams"}
        if category_id is not None:
            params["category_id"] = str(category_id)
        data = self._request(params)
        return data if isinstance(data, list) else []

    def get_short_epg(self, stream_id: int, limit: int = 4) -> List[dict]:
        """
        Short EPG for one channel. In-memory cached for 5 minutes; callers can
        hammer this from a 'now playing' strip without re-fetching.
        """
        now = time.time()
        cached = self._epg_cache.get(stream_id)
        if cached and now - cached[0] < 300:
            return cached[1]
        data = self._request(
            {"action": "get_short_epg", "stream_id": str(stream_id), "limit": str(limit)}
        )
        entries = data.get("epg_listings", []) if isinstance(data, dict) else []
        self._epg_cache[stream_id] = (now, entries)
        return entries

    def build_live_url(self, stream_id: int, container: str = "ts") -> str:
        return (
            f"{self.server_url}/live/{self.username}/{self.password}"
            f"/{stream_id}.{container}"
        )

    def build_catchup_url(
        self,
        stream_id: int,
        start_ts: int,
        duration_minutes: int,
        container: str = "ts",
    ) -> str:
        """Build the path-style Xtream timeshift URL for a past program.

        Format: {server}/timeshift/{user}/{pass}/{duration}/YYYY-MM-DD:HH-MM/{id}.{ext}
        Most providers accept this; a handful use the query-style
        /streaming/timeshift.php endpoint instead (not implemented).
        """
        from datetime import datetime, timezone

        start = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime(
            "%Y-%m-%d:%H-%M"
        )
        return (
            f"{self.server_url}/timeshift/{self.username}/{self.password}"
            f"/{duration_minutes}/{start}/{stream_id}.{container}"
        )

    def fetch_all_live(
        self, progress_callback=None
    ) -> Tuple[List[dict], Dict[str, List[dict]], dict]:
        """
        One-shot fetch: authenticate, pull all live categories + streams, and
        transform into PyIPTV's channel-dict shape.

        Returns (channels, categories, user_info) where:
          - channels: flat List[dict] with keys matching M3UParser output
          - categories: Dict[category_name, List[channel_dict]]
          - user_info: raw user_info from the server (expiry, max_connections, etc.)

        progress_callback(percent: int) is called at auth/categories/streams/transform.
        """
        def progress(p):
            if progress_callback:
                progress_callback(p)

        progress(5)
        auth = self.authenticate()
        user_info = auth.get("user_info") or {}

        progress(20)
        raw_categories = self.get_live_categories()
        # Map category_id -> category_name for fast lookup during stream transform.
        category_name_by_id: Dict[str, str] = {
            str(c.get("category_id")): c.get("category_name") or "Uncategorized"
            for c in raw_categories
        }

        progress(45)
        raw_streams = self.get_live_streams()

        progress(80)
        channels, categories = self._transform(raw_streams, category_name_by_id)

        progress(100)
        return channels, categories, user_info

    def _transform(
        self, raw_streams: List[dict], category_name_by_id: Dict[str, str]
    ) -> Tuple[List[dict], Dict[str, List[dict]]]:
        """
        Translate Xtream stream dicts into the PyIPTV channel-dict shape
        consumed by virtualized_channel_list.py and qmedia_player.py.
        """
        channels: List[dict] = []
        categories: Dict[str, List[dict]] = {}

        for stream in raw_streams:
            stream_id = stream.get("stream_id")
            if stream_id is None:
                continue
            name = stream.get("name") or ""
            epg_channel_id = stream.get("epg_channel_id") or ""
            logo = stream.get("stream_icon") or ""
            cat_id = stream.get("category_id")
            group_title = category_name_by_id.get(str(cat_id), "Uncategorized")
            container = stream.get("container_extension") or "ts"

            # Catchup / archive support — only some channels have it.
            try:
                tv_archive = int(stream.get("tv_archive") or 0)
            except (TypeError, ValueError):
                tv_archive = 0
            try:
                tv_archive_duration = int(stream.get("tv_archive_duration") or 0)
            except (TypeError, ValueError):
                tv_archive_duration = 0

            channel = {
                "duration": "-1",
                "name": name,
                "tvg-id": str(epg_channel_id),
                "tvg-name": name,
                "tvg-logo": logo,
                "group-title": group_title,
                "url": self.build_live_url(int(stream_id), container=container),
                # Xtream-specific — useful later for EPG hookup without
                # breaking the existing consumer contract (extra keys are ignored).
                "xtream_stream_id": int(stream_id),
                "xtream_tv_archive": tv_archive,
                "xtream_tv_archive_duration": tv_archive_duration,
            }
            channels.append(channel)
            categories.setdefault(group_title, []).append(channel)

        return channels, categories
