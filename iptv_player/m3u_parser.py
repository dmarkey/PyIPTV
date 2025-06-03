import re
import os
import time

class M3UParser:
    """
    Parses M3U playlist files, extracting channel information.
    Enhanced for large files with progress reporting and performance optimization.
    """

    def __init__(self, progress_callback=None):
        self.channels = []
        self.categories = {} # Stores channels grouped by category title
        self.progress_callback = progress_callback
        self._should_cancel = False
        
        # Performance optimization settings
        self.chunk_size = 8192 * 4  # 32KB chunks for better I/O performance
        self.progress_update_interval = 100  # Update progress every 100 channels (more responsive)
        self.batch_size = 500  # Process channels in batches for memory efficiency

    def cancel_parsing(self):
        """Cancel the current parsing operation."""
        self._should_cancel = True

    def parse_m3u_from_file(self, filepath):
        """
        Parses an M3U file from the given filepath with progress reporting.

        Args:
            filepath (str): The path to the M3U file.

        Returns:
            tuple: A tuple containing (list of channels, dict of categories).
                   Returns ([], {}) if parsing fails or file not found.
        """
        self.channels = []
        self.categories = {}
        self._should_cancel = False
        
        try:
            # Get file size for progress calculation
            file_size = os.path.getsize(filepath)
            
            # Use binary mode for better performance with large files
            with open(filepath, 'rb') as f:
                return self._parse_content_with_progress(f, file_size)
        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            return [], {}
        except Exception as e:
            print(f"An error occurred while parsing the file: {e}")
            return [], {}
    
    def set_process_events_callback(self, callback):
        """Set a callback for processing Qt events during parsing."""
        self._process_events = callback

    def parse_m3u_from_content(self, content_lines):
        """
        Parses M3U content directly from a list of lines.

        Args:
            content_lines (list): A list of strings, where each string is a line from the M3U content.

        Returns:
            tuple: A tuple containing (list of channels, dict of categories).
        """
        self.channels = []
        self.categories = {}
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
        
        try:
            # Read first chunk to check for #EXTM3U
            first_chunk = file_obj.read(1024)
            try:
                first_chunk_text = first_chunk.decode('utf-8', errors='ignore')
                if first_chunk_text and not first_chunk_text.strip().startswith("#EXTM3U"):
                    print("Warning: File does not start with #EXTM3U. It might not be a valid M3U playlist.")
            except:
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
                    chunk_text = chunk.decode('utf-8', errors='ignore')
                except (UnicodeDecodeError, AttributeError):
                    # Skip problematic chunks
                    continue
                
                # Combine with previous incomplete line
                full_text = line_buffer + chunk_text
                lines = full_text.split('\n')
                
                # Keep the last potentially incomplete line for next iteration
                line_buffer = lines[-1]
                lines = lines[:-1]
                
                # Process complete lines in this chunk
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("#EXTINF:"):
                        current_channel_info = self._parse_extinf_line(line)
                    elif line.startswith("#EXTVLCOPT:") or line.startswith("#EXTGRP:"):
                        # Handle these tags if needed in the future
                        pass
                    elif not line.startswith("#"): # This should be the URL
                        if current_channel_info: # Ensure we have preceding #EXTINF info
                            current_channel_info['url'] = line
                            self.channels.append(current_channel_info)

                            group_title = current_channel_info.get('group-title', 'Uncategorized')
                            if group_title not in self.categories:
                                self.categories[group_title] = []
                            self.categories[group_title].append(current_channel_info)

                            current_channel_info = {} # Reset for the next channel
                            channels_processed += 1
                
                # Update progress more frequently (time-based + count-based)
                current_time = time.time()
                if (self.progress_callback and
                    (channels_processed % self.progress_update_interval == 0 or
                     current_time - last_progress_time > 0.5)):  # Update every 500ms minimum
                    
                    progress = min(100, int((bytes_read / file_size) * 100))
                    self.progress_callback(progress, channels_processed)
                    last_progress_time = current_time
                    
                    # Allow Qt event processing to prevent UI freezing
                    if hasattr(self, '_process_events'):
                        self._process_events()
            
            # Process any remaining content in buffer
            if line_buffer.strip() and not self._should_cancel:
                line = line_buffer.strip()
                if not line.startswith("#") and current_channel_info:
                    current_channel_info['url'] = line
                    self.channels.append(current_channel_info)
                    
                    group_title = current_channel_info.get('group-title', 'Uncategorized')
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

        try:
            first_line = next(line_iter).strip()
            if not first_line.startswith("#EXTM3U"):
                print("Warning: File does not start with #EXTM3U. It might not be a valid M3U playlist.")
        except StopIteration:
            print("Warning: Empty M3U content.")
            return self.channels, self.categories

        for line in line_iter:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                current_channel_info = self._parse_extinf_line(line)
            elif line.startswith("#EXTVLCOPT:") or line.startswith("#EXTGRP:"):
                pass
            elif not line.startswith("#"): # This should be the URL
                if current_channel_info: # Ensure we have preceding #EXTINF info
                    current_channel_info['url'] = line
                    self.channels.append(current_channel_info)

                    group_title = current_channel_info.get('group-title', 'Uncategorized')
                    if group_title not in self.categories:
                        self.categories[group_title] = []
                    self.categories[group_title].append(current_channel_info)

                    current_channel_info = {} # Reset for the next channel

        return self.channels, self.categories

    def _parse_extinf_line(self, line):
        """
        Parses a #EXTINF line to extract channel attributes.
        Example: #EXTINF:-1 tvg-id="BBC1.uk" tvg-name="UK: BBC 1 HD ◉" tvg-logo="http://logo.url" group-title="UK|NEWS",UK: BBC 1 HD ◉
        """
        info = {}
        # Regex to capture key-value pairs like tvg-id="value" and the trailing channel name
        # It handles cases where values might be empty or contain various characters.
        # The last part captures the channel name after the comma.
        match = re.match(r'#EXTINF:(?P<duration>-?\d+)(?:\s+(?P<attributes>.*?))?,(?P<name>.*)', line)
        if not match:
            # Fallback for lines that might not have attributes or a comma
            # e.g., #EXTINF:-1,Channel Name
            simple_match = re.match(r'#EXTINF:(?P<duration>-?\d+),(?P<name>.*)', line)
            if simple_match:
                info['duration'] = simple_match.group('duration')
                info['name'] = simple_match.group('name').strip()
                info['tvg-name'] = info['name'] # Use name as tvg-name if not present
            else:
                # If even the simple match fails, it's a malformed line.
                # We might log this or return an empty dict.
                # print(f"Warning: Malformed #EXTINF line: {line}")
                return {} # Return empty if malformed
        else:
            info['duration'] = match.group('duration')
            info['name'] = match.group('name').strip() # This is the name after the comma

            attributes_str = match.group('attributes')
            if attributes_str:
                # Regex for individual attributes: key="value"
                attr_matches = re.findall(r'([a-zA-Z0-9_-]+)=["\'](.*?)["\']', attributes_str)
                for key, value in attr_matches:
                    info[key.lower()] = value # Store keys in lowercase for consistency

            # Ensure tvg-name is present, fallback to name if not
            if 'tvg-name' not in info or not info['tvg-name']:
                info['tvg-name'] = info['name']

        # Default values for common fields if not found
        info.setdefault('tvg-id', '')
        info.setdefault('tvg-logo', '')
        info.setdefault('group-title', 'Uncategorized')

        return info

if __name__ == '__main__':
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
    all_channels_content, categories_dict_content = parser.parse_m3u_from_content(content_list)
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