import hashlib
import json
import os
import pickle
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class M3UCacheManager:
    """
    High-performance cache manager for M3U playlist data.
    Uses binary serialization for maximum speed and includes intelligent cache validation.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files. If None, uses default location.
        """
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self._ensure_cache_dir_exists()
        self._cache_lock = threading.RLock()

        # Cache settings for optimal performance
        self.cache_version = "1.0"
        self.max_cache_age_days = 30  # Auto-cleanup old cache files

    def _get_default_cache_dir(self) -> str:
        """Get the default cache directory."""
        # Use system temp directory with application-specific subfolder
        import tempfile

        return os.path.join(tempfile.gettempdir(), "pyiptv_cache")

    def _ensure_cache_dir_exists(self):
        """Ensure the cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_file_path(self, source_path: str) -> str:
        """
        Generate cache file path for a given M3U source.

        Args:
            source_path: Path to the original M3U file

        Returns:
            Path to the cache file
        """
        # Create a safe filename from the source path
        safe_name = hashlib.md5(source_path.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_name}.cache")

    def _get_cache_metadata_path(self, source_path: str) -> str:
        """Get the metadata file path for a cache entry."""
        cache_file = self._get_cache_file_path(source_path)
        return cache_file + ".meta"

    def _calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """
        Calculate SHA256 hash of a file efficiently.

        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read at a time

        Returns:
            SHA256 hash as hex string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError):
            return ""

    def _get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for a file (size, modification time, hash).

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file metadata
        """
        try:
            stat = os.stat(file_path)
            return {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": self._calculate_file_hash(file_path),
                "path": file_path,
            }
        except (OSError, IOError):
            return {}

    def _is_cache_valid(self, source_path: str) -> bool:
        """
        Check if cached data is still valid for the given source.

        Args:
            source_path: Path to the original M3U file

        Returns:
            True if cache is valid, False otherwise
        """
        cache_file = self._get_cache_file_path(source_path)
        metadata_file = self._get_cache_metadata_path(source_path)

        # Check if cache files exist
        if not os.path.exists(cache_file) or not os.path.exists(metadata_file):
            return False

        # Check if source file exists
        if not os.path.exists(source_path):
            return False

        try:
            # Load cached metadata
            with open(metadata_file, "r", encoding="utf-8") as f:
                cached_metadata = json.load(f)

            # Verify cache version
            if cached_metadata.get("cache_version") != self.cache_version:
                return False

            # Get current source file metadata
            current_metadata = self._get_file_metadata(source_path)
            source_metadata = cached_metadata.get("source_metadata", {})

            # Quick checks first (size and mtime)
            if current_metadata.get("size") != source_metadata.get(
                "size"
            ) or current_metadata.get("mtime") != source_metadata.get("mtime"):
                return False

            # If quick checks pass, verify hash for absolute certainty
            if current_metadata.get("hash") != source_metadata.get("hash"):
                return False

            return True

        except (json.JSONDecodeError, KeyError, OSError):
            return False

    def save_cache(
        self, source_path: str, channels: List[Dict], categories: Dict[str, List[Dict]]
    ) -> bool:
        """
        Save parsed M3U data to cache.

        Args:
            source_path: Path to the original M3U file
            channels: List of channel dictionaries
            categories: Dictionary of categories with channel lists

        Returns:
            True if saved successfully, False otherwise
        """
        with self._cache_lock:
            cache_file = self._get_cache_file_path(source_path)
            metadata_file = self._get_cache_metadata_path(source_path)

            try:
                # Prepare cache data
                cache_data = {
                    "channels": channels,
                    "categories": categories,
                    "cached_at": time.time(),
                    "cache_version": self.cache_version,
                }

                # Save cache data using pickle for maximum speed
                with open(cache_file, "wb") as f:
                    pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)

                # Save metadata
                metadata = {
                    "cache_version": self.cache_version,
                    "cached_at": datetime.now().isoformat(),
                    "source_metadata": self._get_file_metadata(source_path),
                    "channel_count": len(channels),
                    "category_count": len(categories),
                }

                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)

                return True

            except Exception as e:
                print(f"Error saving cache for {source_path}: {e}")
                # Clean up partial files
                for file_path in [cache_file, metadata_file]:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                return False

    def load_cache(
        self, source_path: str
    ) -> Optional[Tuple[List[Dict], Dict[str, List[Dict]]]]:
        """
        Load cached M3U data if valid.

        Args:
            source_path: Path to the original M3U file

        Returns:
            Tuple of (channels, categories) if cache is valid, None otherwise
        """
        with self._cache_lock:
            if not self._is_cache_valid(source_path):
                return None

            try:
                cache_file = self._get_cache_file_path(source_path)

                # Load cache data using pickle for maximum speed
                with open(cache_file, "rb") as f:
                    cache_data = pickle.load(f)

                # Verify cache structure
                if not all(key in cache_data for key in ["channels", "categories"]):
                    return None

                channels = cache_data["channels"]
                categories = cache_data["categories"]

                # Basic validation
                if not isinstance(channels, list) or not isinstance(categories, dict):
                    return None

                return channels, categories

            except Exception as e:
                print(f"Error loading cache for {source_path}: {e}")
                # Invalid cache, remove it
                self._remove_cache(source_path)
                return None

    def _remove_cache(self, source_path: str):
        """Remove cache files for a source."""
        cache_file = self._get_cache_file_path(source_path)
        metadata_file = self._get_cache_metadata_path(source_path)

        for file_path in [cache_file, metadata_file]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def invalidate_cache(self, source_path: str) -> bool:
        """
        Manually invalidate cache for a specific source.

        Args:
            source_path: Path to the original M3U file

        Returns:
            True if cache was removed, False otherwise
        """
        with self._cache_lock:
            try:
                self._remove_cache(source_path)
                return True
            except Exception as e:
                print(f"Error invalidating cache for {source_path}: {e}")
                return False

    def get_cache_info(self, source_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about cached data for a source.

        Args:
            source_path: Path to the original M3U file

        Returns:
            Dictionary with cache information or None if no cache exists
        """
        metadata_file = self._get_cache_metadata_path(source_path)

        if not os.path.exists(metadata_file):
            return None

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Add cache validity status
            metadata["is_valid"] = self._is_cache_valid(source_path)

            return metadata

        except Exception:
            return None

    def cleanup_old_cache(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old cache files.

        Args:
            max_age_days: Maximum age in days. If None, uses default.

        Returns:
            Number of cache entries removed
        """
        max_age = max_age_days or self.max_cache_age_days
        cutoff_time = time.time() - (max_age * 24 * 60 * 60)
        removed_count = 0

        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith(".cache"):
                    continue

                cache_file = os.path.join(self.cache_dir, filename)
                metadata_file = cache_file + ".meta"

                try:
                    cache_stat = os.stat(cache_file)
                    if cache_stat.st_mtime < cutoff_time:
                        # Remove old cache
                        os.remove(cache_file)
                        if os.path.exists(metadata_file):
                            os.remove(metadata_file)
                        removed_count += 1
                except Exception:
                    continue

        except Exception as e:
            print(f"Error during cache cleanup: {e}")
        return removed_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache directory.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "cache_dir": self.cache_dir,
            "total_cache_files": 0,
            "total_size_bytes": 0,
            "cache_entries": [],
        }

        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith(".cache"):
                    continue

                cache_file = os.path.join(self.cache_dir, filename)
                metadata_file = cache_file + ".meta"

                try:
                    cache_stat = os.stat(cache_file)
                    stats["total_cache_files"] += 1
                    stats["total_size_bytes"] += cache_stat.st_size

                    # Try to get metadata
                    entry_info = {
                        "cache_file": cache_file,
                        "size_bytes": cache_stat.st_size,
                        "modified": datetime.fromtimestamp(
                            cache_stat.st_mtime
                        ).isoformat(),
                    }

                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                            entry_info.update(
                                {
                                    "channel_count": metadata.get("channel_count", 0),
                                    "category_count": metadata.get("category_count", 0),
                                    "source_path": metadata.get(
                                        "source_metadata", {}
                                    ).get("path", "Unknown"),
                                }
                            )
                        except Exception:
                            pass
                    stats["cache_entries"].append(entry_info)

                except Exception:
                    continue

        except Exception as e:
            print(f"Error getting cache stats: {e}")

        return stats
