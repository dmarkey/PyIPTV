from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication


class BackgroundOperation(QThread):
    """Base class for background operations with status-only reporting."""

    # Signals
    status_updated = Signal(str)  # Status message only
    operation_completed = Signal(bool, str, object)  # success, message, result
    operation_cancelled = Signal()

    def __init__(self, operation_title: str):
        super().__init__()
        self.operation_title = operation_title
        self._should_cancel = False
        self.operation_id: Optional[str] = None
        self.start_time = None

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self._should_cancel

    def emit_status(self, status: str):
        """Emit status update."""
        if not self._should_cancel:
            self.status_updated.emit(status)

    def emit_completion(self, success: bool, message: str = "", result: Any = None):
        """Emit completion signal."""
        self.operation_completed.emit(success, message, result)

    def run(self):
        """Override this method in subclasses."""
        raise NotImplementedError


class SimplifiedM3UParseOperation(BackgroundOperation):
    """Simplified M3U parsing operation with status-only reporting."""

    def __init__(self, filepath: str, enable_cache: bool = True):
        super().__init__(f"Parsing {filepath.split('/')[-1]}")
        self.filepath = filepath
        self.enable_cache = enable_cache
        self.parser = None

    def run(self):
        """Run the parsing operation."""
        try:
            self.emit_status("Initializing parser...")

            # Import here to avoid circular imports
            from ...m3u_parser import M3UParser

            def progress_callback(progress_percent, channels_processed):
                if not self._should_cancel:
                    if progress_percent < 25:
                        status = "Reading file..."
                    elif progress_percent < 75:
                        status = (
                            f"Processing channels... ({channels_processed:,} found)"
                        )
                    else:
                        status = "Finalizing..."
                    self.emit_status(status)

            self.parser = M3UParser(
                progress_callback=progress_callback, enable_cache=self.enable_cache
            )

            # Set up Qt event processing
            def process_events():
                QApplication.processEvents()

            self.parser.set_process_events_callback(process_events)

            # Check for cache
            if self.enable_cache:
                cache_info = self.parser.get_cache_info(self.filepath)
                if cache_info and cache_info.get("is_valid", False):
                    self.emit_status("Loading from cache...")

            # Parse
            channels, categories = self.parser.parse_m3u_from_file(self.filepath)

            if self._should_cancel:
                return

            if channels:
                self.emit_completion(
                    True,
                    f"Loaded {len(channels):,} channels successfully",
                    (channels, categories),
                )
            else:
                self.emit_completion(False, "No channels found in playlist")

        except Exception as e:
            if not self._should_cancel:
                self.emit_completion(False, f"Parsing failed: {str(e)}")


class SimplifiedURLDownloadOperation(BackgroundOperation):
    """Simplified URL download operation with status-only reporting."""

    def __init__(self, url: str, playlist_manager):
        super().__init__(f"Downloading {url.split('/')[-1] or 'playlist'}")
        self.url = url
        self.playlist_manager = playlist_manager

    def run(self):
        """Run the download operation."""
        try:
            self.emit_status("Connecting to URL...")

            def progress_callback(progress):
                if not self._should_cancel:
                    if progress < 25:
                        status = "Connecting..."
                    elif progress < 90:
                        status = f"Downloading... ({progress:.0f}%)"
                    else:
                        status = "Saving file..."
                    self.emit_status(status)

            content = self.playlist_manager.download_url_playlist(
                self.url, timeout=600, progress_callback=progress_callback
            )

            if self._should_cancel:
                return

            self.emit_status("Saving playlist...")

            # Create temporary file
            import os
            import tempfile
            import uuid
            from urllib.parse import urlparse

            temp_dir = tempfile.gettempdir()
            parsed_url = urlparse(self.url)
            filename = os.path.basename(parsed_url.path) or "playlist"
            if not filename.endswith((".m3u", ".m3u8")):
                filename += ".m3u8"

            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            temp_file_path = os.path.join(temp_dir, unique_filename)

            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.emit_completion(
                True, "Download completed successfully", temp_file_path
            )

        except Exception as e:
            if not self._should_cancel:
                self.emit_completion(False, f"Download failed: {str(e)}")


class SimplifiedOperationManager(QObject):
    """Simplified operation manager that only uses status bar."""

    # Signals
    operation_result = Signal(
        str, bool, str, object
    )  # operation_type, success, message, result
    operation_started = Signal()  # When any operation starts
    operation_finished = Signal()  # When all operations are complete

    def __init__(self, status_manager):
        super().__init__()
        self.status_manager = status_manager
        self.active_operations: Dict[str, BackgroundOperation] = {}
        self._operation_counter = 0

    def start_m3u_parsing(self, filepath: str, enable_cache: bool = True) -> str:
        """Start M3U parsing operation."""
        operation = SimplifiedM3UParseOperation(filepath, enable_cache)
        return self._start_operation(operation, "m3u_parse")

    def start_url_download(self, url: str, playlist_manager) -> str:
        """Start URL download operation."""
        operation = SimplifiedURLDownloadOperation(url, playlist_manager)
        return self._start_operation(operation, "url_download")

    def _start_operation(
        self, operation: BackgroundOperation, operation_type: str
    ) -> str:
        """Start a background operation."""
        self._operation_counter += 1
        operation_id = f"op_{self._operation_counter}"

        # Store operation
        self.active_operations[operation_id] = operation
        operation.operation_id = operation_id

        # Connect signals
        operation.status_updated.connect(
            lambda status: self._on_status_updated(operation_id, status)
        )
        operation.operation_completed.connect(
            lambda success, msg, result: self._on_operation_completed(
                operation_id, operation_type, success, msg, result
            )
        )

        # Start the operation
        operation.start()

        # Show initial status
        self.status_manager.show_info(
            f"Starting {operation.operation_title.lower()}..."
        )

        # Emit started signal if this is the first active operation
        if len(self.active_operations) == 1:
            self.operation_started.emit()

        return operation_id

    def _on_status_updated(self, operation_id: str, status: str):
        """Handle operation status update."""
        if operation_id in self.active_operations:
            self.status_manager.show_info(
                status, timeout=0
            )  # No timeout for ongoing operations

    def _on_operation_completed(
        self,
        operation_id: str,
        operation_type: str,
        success: bool,
        message: str,
        result: Any,
    ):
        """Handle operation completion."""
        # Clean up
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]

        # Show completion status
        if success:
            self.status_manager.show_success(message)
        else:
            self.status_manager.show_error(message)

        # Emit finished signal if no more active operations
        if len(self.active_operations) == 0:
            self.operation_finished.emit()

        # Emit result
        self.operation_result.emit(operation_type, success, message, result)

    def cancel_all_operations(self):
        """Cancel all active operations."""
        for operation_id, operation in list(self.active_operations.items()):
            operation._should_cancel = True
        self.active_operations.clear()
        self.status_manager.show_info("Operations cancelled")

    def has_active_operations(self) -> bool:
        """Check if there are active operations."""
        return len(self.active_operations) > 0
