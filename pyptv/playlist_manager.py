import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QObject, Signal
from pyptv.m3u_parser import M3UParser
import requests
from pyptv.cache_manager import M3UCacheManager


class PlaylistEntry:
    """Represents a single playlist entry with metadata."""

    def __init__(
        self,
        name: str,
        source: str,
        source_type: str = "file",
        playlist_id: Optional[str] = None,
        created_at: Optional[str] = None,
        last_opened: Optional[str] = None,
        channel_count: int = 0,
        cached_file_path: Optional[str] = None,
    ):
        self.id = playlist_id or str(uuid.uuid4())
        self.name = name
        self.source = source  # File path or URL
        self.source_type = source_type  # "file" or "url"
        self.created_at = created_at or datetime.now().isoformat()
        self.last_opened = last_opened
        self.channel_count = channel_count
        self.cached_file_path = (
            cached_file_path  # For URL playlists, path to cached local file
        )

    def to_dict(self) -> dict:
        """Convert playlist entry to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "source_type": self.source_type,
            "created_at": self.created_at,
            "last_opened": self.last_opened,
            "channel_count": self.channel_count,
            "cached_file_path": self.cached_file_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlaylistEntry":
        """Create playlist entry from dictionary."""
        return cls(
            name=data.get("name", ""),
            source=data.get("source", ""),
            source_type=data.get("source_type", "file"),
            playlist_id=data.get("id"),
            created_at=data.get("created_at"),
            last_opened=data.get("last_opened"),
            channel_count=data.get("channel_count", 0),
            cached_file_path=data.get("cached_file_path"),
        )

    def update_last_opened(self):
        """Update the last opened timestamp."""
        self.last_opened = datetime.now().isoformat()

    def is_available(self) -> bool:
        """Check if the playlist source is available."""
        if self.source_type == "file":
            return os.path.exists(self.source)
        elif self.source_type == "url":
            # For URL playlists, check if we have a cached file first
            if self.cached_file_path and os.path.exists(self.cached_file_path):
                return True
            # Otherwise check if the URL is accessible
            try:
                response = requests.head(self.source, timeout=5)
                return response.status_code == 200
            except (requests.RequestException, OSError):
                return False
        return False

    def get_effective_path(self) -> str:
        """Get the effective file path to use for parsing."""
        if self.source_type == "file":
            return self.source
        elif self.source_type == "url":
            # Return cached file path if available, otherwise return the URL
            return (
                self.cached_file_path
                if (self.cached_file_path and os.path.exists(self.cached_file_path))
                else self.source
            )
        return self.source

    def has_cached_file(self) -> bool:
        """Check if URL playlist has a valid cached file."""
        return (
            self.source_type == "url"
            and bool(self.cached_file_path)
            and os.path.exists(self.cached_file_path)
        )

    def needs_refresh(self) -> bool:
        """Check if a file-based playlist needs to be refreshed based on file modification time."""
        if self.source_type != "file":
            return False

        if not os.path.exists(self.source):
            return False

        # Get the file modification time
        try:
            file_mtime = os.path.getmtime(self.source)
            file_modified = datetime.fromtimestamp(file_mtime)

            # Check if we have a last_opened time to compare against
            if self.last_opened:
                try:
                    last_opened = datetime.fromisoformat(
                        self.last_opened.replace("Z", "+00:00")
                    )
                    last_opened_naive = last_opened.replace(tzinfo=None)

                    # Return True if file is newer than last opened time
                    return file_modified > last_opened_naive
                except (ValueError, TypeError, OSError):
                    # If we can't parse the date, assume refresh is needed
                    return True
            else:
                # If no last_opened time, refresh is needed
                return True

        except (OSError, ValueError):
            # If we can't get file stats, don't refresh
            return False

    def get_file_modification_time(self) -> Optional[datetime]:
        """Get the modification time of the source file for file-based playlists."""
        if self.source_type != "file" or not os.path.exists(self.source):
            return None

        try:
            file_mtime = os.path.getmtime(self.source)
            return datetime.fromtimestamp(file_mtime)
        except (OSError, ValueError):
            return None


class PlaylistManager(QObject):
    """Manages multiple PyPTV playlists with persistence."""

    # Signals
    playlist_added = Signal(PlaylistEntry)
    playlist_removed = Signal(str)  # playlist_id
    playlist_updated = Signal(PlaylistEntry)
    playlists_loaded = Signal()

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.playlists: Dict[str, PlaylistEntry] = {}
        self._playlists_file = self._get_playlists_file_path()

        # Initialize cache manager with the playlist cache directory
        cache_dir = self._get_cache_directory()
        self.cache_manager = M3UCacheManager(cache_dir)

        self.load_playlists()

    def _get_playlists_file_path(self) -> str:
        """Get the path for the playlists configuration file."""
        # Use the same directory as settings
        settings_dir = os.path.dirname(self.settings_manager.settings_filepath)
        return os.path.join(settings_dir, "playlists.json")

    def _get_cache_directory(self) -> str:
        """Get the directory for cached playlist files."""
        settings_dir = os.path.dirname(self.settings_manager.settings_filepath)
        cache_dir = os.path.join(settings_dir, "playlist_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _get_cached_file_path(self, playlist_id: str) -> str:
        """Get the cached file path for a playlist."""
        cache_dir = self._get_cache_directory()
        return os.path.join(cache_dir, f"{playlist_id}.m3u8")

    def add_playlist(
        self, name: str, source: str, source_type: str = "file"
    ) -> PlaylistEntry:
        """Add a new playlist."""
        # Validate source
        if source_type == "file" and not os.path.exists(source):
            raise FileNotFoundError(f"File not found: {source}")
        elif source_type == "url" and not source.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        # Check for duplicate names
        existing_names = [p.name.lower() for p in self.playlists.values()]
        if name.lower() in existing_names:
            raise ValueError(f"Playlist with name '{name}' already exists")

        # Create new playlist entry
        playlist = PlaylistEntry(name=name, source=source, source_type=source_type)

        # For URL playlists, set up cache file path
        if source_type == "url":
            playlist.cached_file_path = self._get_cached_file_path(playlist.id)

        self.playlists[playlist.id] = playlist

        # Save to file
        self.save_playlists()

        # Emit signal
        self.playlist_added.emit(playlist)

        return playlist

    def remove_playlist(self, playlist_id: str) -> bool:
        """Remove a playlist by ID."""
        if playlist_id in self.playlists:
            del self.playlists[playlist_id]
            self.save_playlists()
            self.playlist_removed.emit(playlist_id)
            return True
        return False

    def rename_playlist(self, playlist_id: str, new_name: str) -> bool:
        """Rename a playlist."""
        if playlist_id not in self.playlists:
            return False

        # Check for duplicate names (excluding current playlist)
        existing_names = [
            p.name.lower() for pid, p in self.playlists.items() if pid != playlist_id
        ]
        if new_name.lower() in existing_names:
            raise ValueError(f"Playlist with name '{new_name}' already exists")

        playlist = self.playlists[playlist_id]
        playlist.name = new_name
        self.save_playlists()
        self.playlist_updated.emit(playlist)
        return True

    def update_playlist_source(
        self, playlist_id: str, new_source: str, new_source_type: Optional[str] = None
    ) -> bool:
        """Update the source of a playlist."""
        if playlist_id not in self.playlists:
            return False

        playlist = self.playlists[playlist_id]
        playlist.source = new_source
        if new_source_type:
            playlist.source_type = new_source_type

        self.save_playlists()
        self.playlist_updated.emit(playlist)
        return True

    def get_playlist(self, playlist_id: str) -> Optional[PlaylistEntry]:
        """Get a playlist by ID."""
        return self.playlists.get(playlist_id)

    def get_all_playlists(self) -> List[PlaylistEntry]:
        """Get all playlists sorted by last opened (most recent first), then by name."""
        playlists = list(self.playlists.values())

        def sort_key(p):
            # If last_opened is None, use created_at for sorting
            last_opened = p.last_opened or p.created_at or "1970-01-01"
            return (last_opened, p.name.lower())

        return sorted(playlists, key=sort_key, reverse=True)

    def mark_playlist_opened(self, playlist_id: str):
        """Mark a playlist as recently opened."""
        if playlist_id in self.playlists:
            playlist = self.playlists[playlist_id]

            # Check if file-based playlist needs refresh before marking as opened
            if playlist.source_type == "file" and playlist.needs_refresh():
                self.auto_refresh_file_playlist(playlist)

            playlist.update_last_opened()
            self.save_playlists()
            self.playlist_updated.emit(playlist)

    def auto_refresh_file_playlist(self, playlist: PlaylistEntry) -> bool:
        """Automatically refresh a file-based playlist if the source file is newer."""
        if playlist.source_type != "file":
            return False

        try:
            # For file-based playlists, we just need to update the channel count
            # and last opened time since the file is accessed directly
            if os.path.exists(playlist.source):
                # Read and parse the playlist to update channel count
                try:

                    parser = M3UParser()
                    with open(playlist.source, "r", encoding="utf-8") as f:
                        content = f.read()

                    content_lines = content.splitlines()
                    channels, _ = parser.parse_m3u_from_content(content_lines)
                    playlist.channel_count = len(channels)

                    # Update last opened to current time to mark the refresh
                    playlist.update_last_opened()

                    # Save the updated playlist data
                    self.save_playlists()

                    return True
                except Exception as e:
                    print(f"Warning: Could not refresh playlist {playlist.name}: {e}")
                    return False
            return False
        except Exception as e:
            print(f"Error auto-refreshing playlist {playlist.name}: {e}")
            return False

    def update_channel_count(self, playlist_id: str, count: int):
        """Update the channel count for a playlist."""
        if playlist_id in self.playlists:
            self.playlists[playlist_id].channel_count = count
            self.save_playlists()

    def get_playlist_by_source(self, source: str) -> Optional[PlaylistEntry]:
        """Find a playlist by its source path/URL."""
        for playlist in self.playlists.values():
            if playlist.source == source:
                return playlist
        return None

    def validate_playlists(self) -> List[str]:
        """Validate all playlists and return list of unavailable playlist IDs."""
        unavailable = []
        for playlist_id, playlist in self.playlists.items():
            if not playlist.is_available():
                unavailable.append(playlist_id)
        return unavailable

    def cache_url_playlist(
        self, playlist: PlaylistEntry, timeout: int = 300, progress_callback=None
    ) -> str:
        """Download and cache a URL playlist. Returns the cached file path."""
        if playlist.source_type != "url":
            raise ValueError("This method is only for URL playlists")

        if not playlist.cached_file_path:
            playlist.cached_file_path = self._get_cached_file_path(playlist.id)

        # Download the content
        content = self.download_url_playlist(
            playlist.source, timeout, progress_callback
        )

        # Save to cache file
        with open(playlist.cached_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update playlist and save
        self.save_playlists()

        return playlist.cached_file_path

    def refresh_url_playlist(
        self, playlist_id: str, timeout: int = 300, progress_callback=None
    ) -> bool:
        """
        Refresh a URL playlist by re-downloading it and updating the cache.
        Only makes changes if the refresh is successful.

        Args:
            playlist_id: ID of the playlist to refresh
            timeout: Download timeout in seconds
            progress_callback: Optional callback for progress updates

        Returns:
            True if refresh was successful, False otherwise
        """
        if playlist_id not in self.playlists:
            raise ValueError(f"Playlist with ID '{playlist_id}' not found")

        playlist = self.playlists[playlist_id]

        if playlist.source_type != "url":
            raise ValueError("This method is only for URL playlists")

        if not playlist.cached_file_path:
            playlist.cached_file_path = self._get_cached_file_path(playlist.id)

        # Create a temporary file to store the new content
        import tempfile

        temp_file = None

        try:
            # Download the content to a temporary file first
            content = self.download_url_playlist(
                playlist.source, timeout, progress_callback
            )

            # Create temporary file
            temp_fd, temp_file = tempfile.mkstemp(
                suffix=".m3u8", prefix="pyptv_refresh_"
            )
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                os.close(temp_fd)  # Close if write failed
                raise

            # If we get here, download was successful
            # Remove old cache file if it exists
            if os.path.exists(playlist.cached_file_path):
                os.remove(playlist.cached_file_path)

            # Move temp file to cache location
            import shutil

            shutil.move(temp_file, playlist.cached_file_path)
            temp_file = None  # Don't clean up - file was moved

            # Update playlist metadata
            playlist.update_last_opened()
            self.save_playlists()

            # Emit update signal
            self.playlist_updated.emit(playlist)

            return True

        except Exception as e:
            # Clean up temporary file if it exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

            # Re-raise the exception for the caller to handle
            raise e

    def invalidate_playlist_cache(self, playlist_id: str) -> bool:
        """
        Invalidate cache for a URL playlist.

        Args:
            playlist_id: ID of the playlist to invalidate cache for

        Returns:
            True if cache was invalidated successfully, False otherwise
        """
        if playlist_id not in self.playlists:
            return False

        playlist = self.playlists[playlist_id]

        if playlist.source_type != "url":
            return False

        if playlist.cached_file_path and os.path.exists(playlist.cached_file_path):
            try:
                # Remove cached file
                os.remove(playlist.cached_file_path)

                # Reset cached file path to force re-download on next use
                playlist.cached_file_path = self._get_cached_file_path(playlist.id)
                self.save_playlists()

                return True
            except Exception as e:
                print(f"Error invalidating cache for playlist {playlist.name}: {e}")
                return False

        return True

    def download_url_playlist(
        self, url: str, timeout: int = 300, progress_callback=None
    ) -> str:
        """Download a playlist from URL and return the content."""
        try:
            # Add headers to avoid being blocked by some servers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, timeout=timeout, stream=True, headers=headers)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "text" not in content_type and "application" not in content_type:
                raise ValueError("Invalid content type for M3U playlist")

            # Get total file size if available
            total_size = int(response.headers.get("content-length", 0))

            # Read content with size limit (500MB max)
            max_size = 500 * 1024 * 1024  # 500MB
            content_bytes = b""
            downloaded_size = 0

            # Read as bytes first, then decode (using larger chunks for better speed)
            for chunk in response.iter_content(chunk_size=262144 * 4):  # 1M chunks
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > max_size:
                        raise ValueError("Playlist file too large (>500MB)")
                    content_bytes += chunk

                    # Report progress if callback provided
                    if progress_callback and total_size > 0:
                        progress = min(int((downloaded_size / total_size) * 100), 100)
                        progress_callback(progress)
                    elif progress_callback:
                        # If no total size, report progress based on downloaded size
                        # Use a logarithmic scale to show some progress
                        mb_downloaded = downloaded_size / (1024 * 1024)
                        progress = min(
                            int(30 + (mb_downloaded / 10) * 40), 90
                        )  # 30-90% range
                        progress_callback(progress)

            # Decode the content to string
            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ["latin1", "cp1252", "iso-8859-1"]:
                    try:
                        content = content_bytes.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Unable to decode playlist content")

            return content
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to download playlist: {str(e)}")

    def save_playlists(self):
        """Save playlists to file."""
        try:
            data = {
                "version": "1.0",
                "playlists": [
                    playlist.to_dict() for playlist in self.playlists.values()
                ],
                "last_updated": datetime.now().isoformat(),
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(self._playlists_file), exist_ok=True)

            with open(self._playlists_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving playlists: {e}")

    def load_playlists(self):
        """Load playlists from file."""
        try:
            if not os.path.exists(self._playlists_file):
                self.playlists = {}
                self.playlists_loaded.emit()
                return

            with open(self._playlists_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Load playlists
            self.playlists = {}
            for playlist_data in data.get("playlists", []):
                playlist = PlaylistEntry.from_dict(playlist_data)
                self.playlists[playlist.id] = playlist

            self.playlists_loaded.emit()

        except Exception as e:
            print(f"Error loading playlists: {e}")
            self.playlists = {}
            self.playlists_loaded.emit()

    def export_playlists(self, export_path: str) -> bool:
        """Export playlists configuration to a file."""
        try:
            data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "playlists": [
                    playlist.to_dict() for playlist in self.playlists.values()
                ],
            }

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting playlists: {e}")
            return False

    def import_playlists(self, import_path: str) -> Tuple[int, int]:
        """Import playlists from a file. Returns (imported_count, skipped_count)."""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_count = 0
            skipped_count = 0

            for playlist_data in data.get("playlists", []):
                try:
                    playlist = PlaylistEntry.from_dict(playlist_data)

                    # Check if playlist with same name already exists
                    existing_names = [p.name.lower() for p in self.playlists.values()]
                    if playlist.name.lower() in existing_names:
                        skipped_count += 1
                        continue

                    # Generate new ID to avoid conflicts
                    playlist.id = str(uuid.uuid4())
                    self.playlists[playlist.id] = playlist
                    imported_count += 1

                except Exception as e:
                    print(f"Error importing playlist: {e}")
                    skipped_count += 1

            if imported_count > 0:
                self.save_playlists()

            return imported_count, skipped_count

        except Exception as e:
            print(f"Error importing playlists: {e}")
            return 0, 0
