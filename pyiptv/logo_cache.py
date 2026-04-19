"""Async channel-logo fetcher with memory + disk caching.

Channel lists can have tens of thousands of entries, but only ~30 rows are
visible at a time, so logos are fetched lazily on first paint. Results are
LRU-cached in memory and persisted on disk — restarts don't refetch.
"""

from __future__ import annotations

import hashlib
import os
from collections import OrderedDict
from typing import Dict, Optional, Set

from PySide6.QtCore import (
    QByteArray,
    QObject,
    QStandardPaths,
    QUrl,
    Signal,
)
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


MAX_MEMORY_ENTRIES = 500
FETCH_TIMEOUT_MS = 10_000


def _cache_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    if not base:
        base = os.path.expanduser("~/.config/PyIPTV")
    path = os.path.join(base, "logo_cache")
    os.makedirs(path, exist_ok=True)
    return path


def _disk_path(url: str) -> str:
    return os.path.join(_cache_dir(), hashlib.md5(url.encode("utf-8")).hexdigest() + ".bin")


class LogoCache(QObject):
    """
    Request logos with `request(url)`. Returns an already-cached QPixmap if
    one is available, otherwise schedules an async fetch and returns None.
    `logo_ready(url)` fires when a previously-requested URL completes.

    Pixmaps are stored at native size; callers scale at paint time.
    """

    logo_ready = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._memory: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._in_flight: Set[str] = set()
        self._failed: Set[str] = set()  # Don't re-try failures every repaint.
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_finished)
        self._reply_url: Dict[QNetworkReply, str] = {}

    def request(self, url: str) -> Optional[QPixmap]:
        if not url:
            return None
        if url in self._memory:
            # Touch for LRU.
            self._memory.move_to_end(url)
            return self._memory[url]
        if url in self._failed or url in self._in_flight:
            return None

        # Disk hit?
        disk = _disk_path(url)
        if os.path.exists(disk):
            try:
                with open(disk, "rb") as f:
                    data = f.read()
                pix = QPixmap()
                if pix.loadFromData(QByteArray(data)) and not pix.isNull():
                    self._cache_in_memory(url, pix)
                    return pix
            except OSError:
                pass
            # Disk entry unreadable — treat as miss.

        # Network fetch.
        self._start_fetch(url)
        return None

    def _cache_in_memory(self, url: str, pix: QPixmap) -> None:
        self._memory[url] = pix
        self._memory.move_to_end(url)
        while len(self._memory) > MAX_MEMORY_ENTRIES:
            self._memory.popitem(last=False)

    def _start_fetch(self, url: str) -> None:
        parsed = QUrl(url)
        if not parsed.isValid() or parsed.scheme() not in ("http", "https"):
            self._failed.add(url)
            return
        req = QNetworkRequest(parsed)
        req.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        # Spoof a browser UA — some providers' CDNs reject the default Qt UA.
        req.setRawHeader(
            b"User-Agent",
            b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            b"(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        req.setTransferTimeout(FETCH_TIMEOUT_MS)
        reply = self._nam.get(req)
        self._reply_url[reply] = url
        self._in_flight.add(url)

    def _on_finished(self, reply: QNetworkReply) -> None:
        url = self._reply_url.pop(reply, "")
        self._in_flight.discard(url)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._failed.add(url)
                return
            data = bytes(reply.readAll())
            if not data:
                self._failed.add(url)
                return
            pix = QPixmap()
            if not pix.loadFromData(QByteArray(data)) or pix.isNull():
                self._failed.add(url)
                return
            # Persist to disk and cache in memory.
            try:
                with open(_disk_path(url), "wb") as f:
                    f.write(data)
            except OSError:
                pass
            self._cache_in_memory(url, pix)
            if url:
                self.logo_ready.emit(url)
        finally:
            reply.deleteLater()


_singleton: Optional[LogoCache] = None


def shared() -> LogoCache:
    """Process-wide shared cache. Instantiated lazily on first use."""
    global _singleton
    if _singleton is None:
        _singleton = LogoCache()
    return _singleton
