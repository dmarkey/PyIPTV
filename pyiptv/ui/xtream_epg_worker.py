"""Background worker that downloads and parses the Xtream XMLTV EPG.

Runs independently of the channel fetch because XMLTV payloads can be tens of
megabytes and take several seconds to parse; the channel list shouldn't wait.
"""

from PySide6.QtCore import QThread, Signal

import requests


class XtreamEpgWorker(QThread):
    """Fetches `{server}/xmltv.php`, parses it, and emits the channel-keyed index."""

    # channel_id (str) → list[(start_ts, stop_ts, title, desc)]
    epg_ready = Signal(dict)
    epg_failed = Signal(str)

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, server_url, username, password, parent=None):
        super().__init__(parent)
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        url = f"{self.server_url}/xmltv.php"
        params = {"username": self.username, "password": self.password}
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=120,
                headers={"User-Agent": self.USER_AGENT},
                stream=True,
            )
            resp.raise_for_status()
            # Read the full payload. Could stream-parse, but stdlib ET.iterparse
            # needs a seekable file-like and the memory win isn't worth the
            # complexity for the typical 20–80MB feed.
            content = resp.content
            if self._cancel:
                return
        except requests.RequestException as e:
            if not self._cancel:
                self.epg_failed.emit(f"EPG download failed: {e}")
            return

        try:
            from pyiptv.epg import parse_xmltv

            index = parse_xmltv(content)
        except Exception as e:
            if not self._cancel:
                self.epg_failed.emit(f"EPG parse failed: {e}")
            return

        if not self._cancel:
            self.epg_ready.emit(index)
