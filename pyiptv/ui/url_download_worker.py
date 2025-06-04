import os
import tempfile
from PySide6.QtCore import QThread, Signal


class URLDownloadWorker(QThread):
    """Worker thread for downloading URL-based playlists."""

    # Signals
    progress_updated = Signal(int)  # Progress percentage
    status_updated = Signal(str)  # Status message
    download_completed = Signal(str)  # Downloaded file path
    download_failed = Signal(str)  # Error message

    def __init__(self, url, playlist_manager, parent=None):
        super().__init__(parent)
        self.url = url
        self.playlist_manager = playlist_manager
        self._should_cancel = False

    def cancel_download(self):
        """Cancel the download operation."""
        self._should_cancel = True

    def run(self):
        """Download the playlist from URL."""
        try:
            self.status_updated.emit("Connecting to URL...")
            self.progress_updated.emit(5)

            if self._should_cancel:
                return

            # Download the playlist content with progress callback
            self.status_updated.emit("Downloading playlist...")

            def progress_callback(progress):
                if not self._should_cancel:
                    # Map progress to 10-90% range (leaving room for file operations)
                    mapped_progress = 10 + int(progress * 0.8)
                    self.progress_updated.emit(mapped_progress)

            content = self.playlist_manager.download_url_playlist(
                self.url, timeout=600, progress_callback=progress_callback
            )

            if self._should_cancel:
                return

            self.progress_updated.emit(95)
            self.status_updated.emit("Saving playlist...")

            # Create a temporary file to store the downloaded content
            temp_dir = tempfile.gettempdir()
            from urllib.parse import urlparse

            parsed_url = urlparse(self.url)

            # Generate a filename from the URL
            filename = os.path.basename(parsed_url.path) or "playlist"
            if not filename.endswith((".m3u", ".m3u8")):
                filename += ".m3u8"

            # Create a unique filename to avoid conflicts
            import uuid

            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            temp_file_path = os.path.join(temp_dir, unique_filename)

            # Write the content to the temporary file
            try:
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                if not self._should_cancel:
                    self.download_failed.emit(f"Failed to save playlist: {str(e)}")
                return

            self.progress_updated.emit(100)
            self.status_updated.emit("Download completed!")

            if not self._should_cancel:
                self.download_completed.emit(temp_file_path)

        except ConnectionError as e:
            if not self._should_cancel:
                self.download_failed.emit(f"Network error: {str(e)}")
        except ValueError as e:
            if not self._should_cancel:
                self.download_failed.emit(f"Invalid playlist: {str(e)}")
        except Exception as e:
            if not self._should_cancel:
                self.download_failed.emit(f"Unexpected error: {str(e)}")
