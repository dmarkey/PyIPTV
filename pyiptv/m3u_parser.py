import os
import re
import time
from typing import IO, Any, Callable, Dict, List, Optional, Tuple, Union

from .cache_manager import M3UCacheManager


class M3UParser:
    """
    Parses M3U playlist files, extracting channel information.
    Enhanced for large files with progress reporting, performance optimization, and intelligent caching.
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        enable_cache: bool = True,
        cache_dir: Optional[str] = None,
        cache_manager: Optional[M3UCacheManager] = None,
    ) -> None:
        self.channels: List[Dict[str, str]] = []
        self.categories: Dict[str, List[Dict[str, str]]] = (
            {}
        )  # Stores channels grouped by category title
        self.progress_callback = progress_callback
        self._should_cancel = False
        self._process_events: Optional[Callable[[], None]] = None

        # Cache settings
        self.enable_cache = enable_cache
        self.cache_manager = cache_manager or (
            M3UCacheManager(cache_dir) if enable_cache else None
        )

        # Performance optimization settings
        self.chunk_size = 8192 * 4  # 32KB chunks for better I/O performance
        self.progress_update_interval = (
            100  # Update progress every 100 channels (more responsive)
        )
        self.batch_size = 500  # Process channels in batches for memory efficiency

    def cancel_parsing(self) -> None:
        """Cancel the current parsing operation."""
        self._should_cancel = True

    def parse_m3u_from_file(
        self, filepath: str
    ) -> Tuple[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]:
        """
        Parses an M3U file from the given filepath with progress reporting and intelligent caching.

        Args:
            filepath: The path to the M3U file.

        Returns:
            A tuple containing (list of channels, dict of categories).
            Returns ([], {}) if parsing fails or file not found.
        """
        self.channels = []
        self.categories = {}
        self._should_cancel = False

        try:
            # Check if file exists
            if not os.path.exists(filepath):
                print(f"Error: File not found at {filepath}")
                return [], {}

            # Try to load from cache first (if enabled)
            if self.enable_cache and self.cache_manager:
                cache_result = self.cache_manager.load_cache(filepath)
                if cache_result is not None:
                    print(
                        f"Loading M3U data from cache for: {os.path.basename(filepath)}"
                    )
                    self.channels, self.categories = cache_result

                    # Report instant completion to progress callback
                    if self.progress_callback:
                        self.progress_callback(100, len(self.channels))

                    return self.channels, self.categories

            # Cache miss or disabled - parse normally
            print(f"Parsing M3U file: {os.path.basename(filepath)}")

            # Get file size for progress calculation
            file_size = os.path.getsize(filepath)

            # Use binary mode for better performance with large files
            with open(filepath, "rb") as f:
                result = self._parse_content_with_progress(f, file_size)

            # Save to cache if enabled and parsing was successful
            if (
                self.enable_cache
                and self.cache_manager
                and not self._should_cancel
                and self.channels
            ):
                try:
                    if self.cache_manager.save_cache(
                        filepath, self.channels, self.categories
                    ):
                        print(
                            f"Cached M3U data for future use: {os.path.basename(filepath)}"
                        )
                except Exception as e:
                    print(f"Warning: Could not save cache: {e}")

            return result

        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            return [], {}
        except Exception as e:
            print(f"An error occurred while parsing the file: {e}")
            return [], {}

    def set_process_events_callback(self, callback: Callable[[], None]) -> None:
        """Set a callback for processing Qt events during parsing."""
        self._process_events = callback

    def parse_m3u_from_content(
        self,
        content_lines: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]:
        """
        Parses M3U content directly from a list of lines.

        Args:
            content_lines: A list of strings, where each string is a line from the M3U content.
            progress_callback: Optional callback for progress reporting.

        Returns:
            A tuple containing (list of channels, dict of categories).
        """
        self.channels = []
        self.categories = {}
        # Use provided progress callback or instance callback
        if progress_callback:
            old_callback = self.progress_callback
            self.progress_callback = progress_callback
            result = self._parse_content(content_lines)
            self.progress_callback = old_callback
            return result
        return self._parse_content(content_lines)

    def _parse_content_with_progress(self, file_obj, file_size):
        """
        Internal method to parse M3U content with optimized progress reporting.
        Uses chunked reading and more frequent progress updates for better performance.
        """
        current_channel_info = {}
        channels_processed = 0
        bytes_read = 0
        last_progress_time = time.time()

        # Buffer for incomplete lines
        line_buffer = ""

        # Detect encoding from the first chunk
        detected_encoding = self._detect_encoding_from_bytes(file_obj)

        try:
            # Read first chunk to check for #EXTM3U
            first_chunk = file_obj.read(1024)
            try:
                first_chunk_text = first_chunk.decode(detected_encoding, errors="ignore")
                if first_chunk_text:
                    # Remove BOM if present
                    if first_chunk_text.startswith('\ufeff'):
                        first_chunk_text = first_chunk_text[1:]

                    # Check if #EXTM3U appears anywhere in the first few lines
                    first_lines = first_chunk_text.strip().split('\n')[:3]
                    has_extm3u = any(line.strip().startswith("#EXTM3U") for line in first_lines)
                    if not has_extm3u:
                        print(
                            "Warning: File does not start with #EXTM3U. It might not be a valid M3U playlist."
                        )
            except (UnicodeDecodeError, AttributeError):
                pass

            # Reset file position and start chunked reading
            file_obj.seek(0)

            while True:
                if self._should_cancel:
                    break

                # Read chunk in binary mode for performance
                chunk = file_obj.read(self.chunk_size)
                if not chunk:
                    break

                bytes_read += len(chunk)

                # Decode chunk with error handling
                try:
                    chunk_text = chunk.decode(detected_encoding, errors="ignore")
                except (UnicodeDecodeError, AttributeError):
                    # Try fallback encodings
                    chunk_text = None
                    for fallback_encoding in ["utf-8", "latin-1", "cp1252"]:
                        try:
                            chunk_text = chunk.decode(fallback_encoding, errors="ignore")
                            break
                        except (UnicodeDecodeError, AttributeError):
                            continue

                    if chunk_text is None:
                        # Skip problematic chunks
                        continue

                # Remove BOM if present at the beginning of the file
                if not line_buffer and chunk_text.startswith('\ufeff'):
                    chunk_text = chunk_text[1:]

                # Combine with previous incomplete line
                full_text = line_buffer + chunk_text
                lines = full_text.split("\n")

                # Keep the last potentially incomplete line for next iteration
                line_buffer = lines[-1]
                lines = lines[:-1]

                # Process complete lines in this chunk
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("#EXTINF:"):
                        try:
                            current_channel_info = self._parse_extinf_line(line)
                        except Exception as e:
                            print(f"Error parsing line: {line}")
                            print(f"Error: {e}")
                            import traceback
                            traceback.print_exc()
                            current_channel_info = {}
                    elif line.startswith("#EXTVLCOPT:") or line.startswith("#EXTGRP:"):
                        # Handle these tags if needed in the future
                        pass
                    elif not line.startswith("#"):  # This should be the URL
                        if (
                            current_channel_info
                        ):  # Ensure we have preceding #EXTINF info
                            current_channel_info["url"] = line
                            self.channels.append(current_channel_info)

                            group_title = current_channel_info.get(
                                "group-title", "Uncategorized"
                            )
                            if group_title not in self.categories:
                                self.categories[group_title] = []
                            self.categories[group_title].append(current_channel_info)

                            current_channel_info = {}  # Reset for the next channel
                            channels_processed += 1

                # Update progress more frequently (time-based + count-based)
                current_time = time.time()
                if self.progress_callback and (
                    channels_processed % self.progress_update_interval == 0
                    or current_time - last_progress_time > 0.5
                ):  # Update every 500ms minimum

                    progress = min(100, int((bytes_read / file_size) * 100))
                    self.progress_callback(progress, channels_processed)
                    last_progress_time = current_time

                    # Allow Qt event processing to prevent UI freezing
                    if hasattr(self, "_process_events"):
                        self._process_events()

            # Process any remaining content in buffer
            if line_buffer.strip() and not self._should_cancel:
                line = line_buffer.strip()
                if not line.startswith("#") and current_channel_info:
                    current_channel_info["url"] = line
                    self.channels.append(current_channel_info)

                    group_title = current_channel_info.get(
                        "group-title", "Uncategorized"
                    )
                    if group_title not in self.categories:
                        self.categories[group_title] = []
                    self.categories[group_title].append(current_channel_info)
                    channels_processed += 1

        except Exception as e:
            print(f"Error during parsing: {e}")

        # Final progress update
        if self.progress_callback:
            self.progress_callback(100, channels_processed)

        return self.channels, self.categories

    def _parse_content(self, content_iterable):
        """
        Internal method to parse M3U content from an iterable (file object or list of lines).
        Maintained for backwards compatibility.
        """
        current_channel_info = {}
        line_iter = iter(content_iterable)

        # Convert to list to check first line and process normally
        content_lines = list(line_iter)
        if not content_lines:
            print("Warning: Empty M3U content.")
            return self.channels, self.categories

        # Check if first few lines contain #EXTM3U
        first_few_lines = content_lines[:3]
        has_extm3u = any(line.strip().startswith("#EXTM3U") for line in first_few_lines)
        if not has_extm3u:
            print(
                "Warning: File does not start with #EXTM3U. It might not be a valid M3U playlist."
            )

        for line in content_lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                try:
                    current_channel_info = self._parse_extinf_line(line)
                except Exception as e:
                    print(f"Error parsing line: {line}")
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()
                    current_channel_info = {}
            elif line.startswith("#EXTVLCOPT:") or line.startswith("#EXTGRP:"):
                pass
            elif not line.startswith("#"):  # This should be the URL
                if current_channel_info:  # Ensure we have preceding #EXTINF info
                    current_channel_info["url"] = line
                    self.channels.append(current_channel_info)

                    group_title = current_channel_info.get(
                        "group-title", "Uncategorized"
                    )
                    if group_title not in self.categories:
                        self.categories[group_title] = []
                    self.categories[group_title].append(current_channel_info)

                    current_channel_info = {}  # Reset for the next channel

        return self.channels, self.categories

    def _detect_encoding_from_bytes(self, file_obj):
        """
        Detect encoding from file bytes.

        Args:
            file_obj: File object opened in binary mode

        Returns:
            str: Detected encoding
        """
        # Save current position
        current_pos = file_obj.tell()

        try:
            # Read first few bytes to check for BOM
            file_obj.seek(0)
            raw_data = file_obj.read(4)

            # Check for UTF-16 BOM
            if raw_data.startswith(b'\xff\xfe'):
                return "utf-16le"
            elif raw_data.startswith(b'\xfe\xff'):
                return "utf-16be"
            # Check for UTF-8 BOM
            elif raw_data.startswith(b'\xef\xbb\xbf'):
                return "utf-8-sig"

            # Read more data to test encodings
            file_obj.seek(0)
            test_data = file_obj.read(1024)

            # Try different encodings
            encodings_to_try = ["utf-8", "utf-16", "utf-16le", "utf-16be", "latin-1", "cp1252", "iso-8859-1"]

            for encoding in encodings_to_try:
                try:
                    decoded = test_data.decode(encoding)
                    # Check if it looks like M3U content
                    if "#EXTM3U" in decoded or "#EXTINF" in decoded:
                        return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue

            # Default fallback
            return "utf-8"

        except Exception:
            return "utf-8"
        finally:
            # Restore file position
            file_obj.seek(current_pos)

    def _parse_extinf_line(self, line):
        """
        Parses a #EXTINF line to extract channel attributes.
        Example: #EXTINF:-1 tvg-id="BBC1.uk" tvg-name="UK: BBC 1 HD ◉" tvg-logo="http://logo.url" group-title="UK|NEWS",UK: BBC 1 HD ◉
        """
        info = {}
        # Regex to capture key-value pairs like tvg-id="value" and the trailing channel name
        # It handles cases where values might be empty or contain various characters.
        # The last part captures the channel name after the comma.
        match = re.match(
            r"#EXTINF:(?P<duration>-?\d+)(?:\s+(?P<attributes>.*?))?,(?P<name>.*)", line
        )

        if not match:
            # Fallback for lines that might not have attributes or a comma
            # e.g., #EXTINF:-1,Channel Name
            simple_match = re.match(r"#EXTINF:(?P<duration>-?\d+),(?P<name>.*)", line)
            if simple_match:
                info["duration"] = simple_match.group("duration")
                info["name"] = simple_match.group("n").strip()
                info["tvg-name"] = info["name"]  # Use name as tvg-name if not present
            else:
                # If even the simple match fails, it's a malformed line.
                # We might log this or return an empty dict.
                # print(f"Warning: Malformed #EXTINF line: {line}")
                return {}  # Return empty if malformed
        else:
            # Match found - parse attributes and name
            info["duration"] = match.group("duration")
            # Handle both "n" and "name" group names for compatibility
            try:
                info["name"] = match.group("n").strip()
            except IndexError:
                info["name"] = match.group("name").strip()

            attributes_str = match.group("attributes")
            if attributes_str:
                # Regex for individual attributes: key="value"
                attr_matches = re.findall(
                    r'([a-zA-Z0-9_-]+)=["\'](.*?)["\']', attributes_str
                )
                for key, value in attr_matches:
                    info[key.lower()] = value  # Store keys in lowercase for consistency

            # Ensure tvg-name is present, fallback to name if not
            if "tvg-name" not in info or not info["tvg-name"]:
                info["tvg-name"] = info["name"]

        # Default values for common fields if not found
        info.setdefault("tvg-id", "")
        info.setdefault("tvg-logo", "")
        info.setdefault("group-title", "Uncategorized")

        # Detect content type based on attributes
        tvg_type = info.get("tvg-type", "").lower()
        if tvg_type in ["serie", "series", "episode"]:
            info["content_type"] = "series"
        elif tvg_type in ["movie", "film"]:
            info["content_type"] = "movie"
        else:
            # Check if it looks like series content based on name patterns
            name = info.get("name", "").lower()
            if any(pattern in name for pattern in ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "e0", "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9", "season", "episode"]):
                info["content_type"] = "series"
            elif any(pattern in name for pattern in ["movie", "film", "(20", "(19"]):
                info["content_type"] = "movie"
            else:
                info["content_type"] = "live"

        return info

    def invalidate_cache(self, filepath):
        """
        Invalidate cache for a specific M3U file.

        Args:
            filepath (str): Path to the M3U file

        Returns:
            bool: True if cache was invalidated, False otherwise
        """
        if self.enable_cache and self.cache_manager:
            return self.cache_manager.invalidate_cache(filepath)
        return False

    def get_cache_info(self, filepath):
        """
        Get cache information for a specific M3U file.

        Args:
            filepath (str): Path to the M3U file

        Returns:
            dict or None: Cache information or None if no cache exists
        """
        if self.enable_cache and self.cache_manager:
            return self.cache_manager.get_cache_info(filepath)
        return None

    def cleanup_old_cache(self, max_age_days=None):
        """
        Clean up old cache files.

        Args:
            max_age_days (int, optional): Maximum age in days for cache files

        Returns:
            int: Number of cache entries removed
        """
        if self.enable_cache and self.cache_manager:
            return self.cache_manager.cleanup_old_cache(max_age_days)
        return 0

    def get_cache_stats(self):
        """
        Get statistics about the cache.

        Returns:
            dict: Cache statistics
        """
        if self.enable_cache and self.cache_manager:
            return self.cache_manager.get_cache_stats()
        return {}


if __name__ == "__main__":
    # Example Usage:
    parser = M3UParser()

    # Create a dummy M3U file for testing
    dummy_m3u_content = """#EXTM3U
#EXTINF:-1 tvg-id="BBCOneOxford.uk" tvg-name="UK: BBC ONE LONDON 4K ◉" tvg-logo="http://icon-tmdb.me/stalker_portal/misc/logos/320/11987.jpg" group-title="UK| GENERAL ᴴᴰ/ᴿᴬᵂ",UK: BBC ONE LONDON 4K ◉
http://cf.3331-cloud.me:80/123467dav/n329alc52j/497001
#EXTINF:-1 tvg-id="BBC1.uk" tvg-name="UK: BBC 1 HD ◉" tvg-logo="http://icon-tmdb.me/stalker_portal/misc/logos/320/12016.jpg" group-title="UK| GENERAL ᴴᴰ/ᴿᴬᵂ",UK: BBC 1 HD ◉
http://cf.3331-cloud.me:80/123467dav/n329alc52j/162096
#EXTINF:-1 tvg-id="" tvg-name="#### GENERAL HD/4K ####" tvg-logo="" group-title="UK| GENERAL ᴴᴰ/ᴿᴬᵂ",#### GENERAL HD/4K ####
http://cf.3331-cloud.me:80/123467dav/n329alc52j/1015349
#EXTINF:-1 tvg-name="No Attributes Channel",No Attributes Channel
http://stream.example.com/no_attributes
#EXTINF:-1 ,Nameless Channel with Attributes tvg-id="NCWA" group-title="Test"
http://stream.example.com/nameless_attributes
#EXTINF:-1 tvg-id="NoComma.uk" tvg-name="No Comma Channel" tvg-logo="logo.png" group-title="Special"
http://stream.example.com/no_comma
    """
    with open("test.m3u", "w", encoding="utf-8") as f:
        f.write(dummy_m3u_content)

    print("--- Parsing from file 'test.m3u' ---")
    all_channels, categories_dict = parser.parse_m3u_from_file("test.m3u")

    if all_channels:
        print(f"\nTotal channels parsed: {len(all_channels)}")
        # print("\nFirst 3 Channels:")
        # for i, channel in enumerate(all_channels[:3]):
        #     print(f"  Channel {i+1}:")
        #     for key, value in channel.items():
        #         print(f"    {key}: {value}")

        print("\nCategories and their channel counts:")
        for cat, chans in categories_dict.items():
            print(f"  Category '{cat}': {len(chans)} channels")
            # print(f"    First channel in '{cat}': {chans[0]['name']}")

    # Example parsing from content lines
    print("\n--- Parsing from direct content ---")
    content_list = dummy_m3u_content.splitlines()
    all_channels_content, categories_dict_content = parser.parse_m3u_from_content(
        content_list
    )
    if all_channels_content:
        print(f"\nTotal channels parsed from content: {len(all_channels_content)}")
        print("\nCategories and their channel counts (from content):")
        for cat, chans in categories_dict_content.items():
            print(f"  Category '{cat}': {len(chans)} channels")

    # Clean up dummy file
    import os

    try:
        os.remove("test.m3u")
    except OSError as e:
        print(f"Error removing test.m3u: {e}")
