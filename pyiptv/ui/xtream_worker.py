"""Background worker for Xtream Codes API fetches.

Mirrors `url_download_worker.py`'s threading model so the same progress-dialog
wiring in `playlist_manager_window.py` can drive it.
"""

from PySide6.QtCore import QThread, Signal

from pyiptv.xtream_client import (
    XtreamAuthError,
    XtreamClient,
    XtreamError,
    XtreamNetworkError,
)


class XtreamFetchWorker(QThread):
    """Fetch live categories + streams from an Xtream server off the UI thread."""

    progress_updated = Signal(int)
    status_updated = Signal(str)
    # channels (list), categories (dict), user_info (dict)
    fetch_completed = Signal(list, dict, dict)
    fetch_failed = Signal(str)

    def __init__(self, server_url, username, password, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.username = username
        self.password = password
        self._should_cancel = False

    def cancel_download(self):
        """Match URLDownloadWorker's cancel API so existing progress-dialog wiring works."""
        self._should_cancel = True

    def run(self):
        try:
            self.status_updated.emit("Connecting to Xtream server...")
            client = XtreamClient(self.server_url, self.username, self.password)

            def progress_callback(p):
                if not self._should_cancel:
                    self.progress_updated.emit(p)
                    if p <= 20:
                        self.status_updated.emit("Authenticating...")
                    elif p <= 45:
                        self.status_updated.emit("Fetching categories...")
                    elif p <= 80:
                        self.status_updated.emit("Fetching streams...")
                    else:
                        self.status_updated.emit("Processing...")

            if self._should_cancel:
                return

            channels, categories, user_info = client.fetch_all_live(
                progress_callback=progress_callback
            )

            if self._should_cancel:
                return

            self.status_updated.emit("Done")
            self.fetch_completed.emit(channels, categories, user_info)

        except XtreamAuthError as e:
            if not self._should_cancel:
                self.fetch_failed.emit(f"Authentication failed: {e}")
        except XtreamNetworkError as e:
            if not self._should_cancel:
                self.fetch_failed.emit(f"Network error: {e}")
        except XtreamError as e:
            if not self._should_cancel:
                self.fetch_failed.emit(str(e))
        except Exception as e:
            if not self._should_cancel:
                self.fetch_failed.emit(f"Unexpected error: {e}")
