"""
Subtitle management for PyIPTV.

This module provides comprehensive subtitle support including:
- Multiple subtitle format support (SRT, VTT, ASS, SSA)
- Automatic subtitle detection and loading
- Manual subtitle file selection
- Subtitle track switching
- Subtitle styling and positioning
"""

import os
import re
import requests
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox


@dataclass
class SubtitleTrack:
    """Represents a subtitle track."""
    id: str
    language: str
    title: str
    format: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    is_embedded: bool = False
    is_active: bool = False
    stream_index: Optional[int] = None  # For embedded tracks
    codec: Optional[str] = None  # Subtitle codec (mov_text, subrip, etc.)

    @property
    def display_name(self) -> str:
        """Get display name for the track."""
        if self.is_embedded:
            return f"{self.language} (Embedded)"
        else:
            return f"{self.language} (External)"


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry with timing."""
    start_time: float  # in seconds
    end_time: float    # in seconds
    text: str
    style: Optional[Dict[str, Any]] = None


class SubtitleParser:
    """Parses various subtitle formats."""
    
    @staticmethod
    def parse_srt(content: str) -> List[SubtitleEntry]:
        """Parse SRT subtitle format."""
        entries = []
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            try:
                # Parse timing line (format: 00:00:00,000 --> 00:00:00,000)
                timing_line = lines[1]
                start_str, end_str = timing_line.split(' --> ')
                
                start_time = SubtitleParser._parse_srt_time(start_str)
                end_time = SubtitleParser._parse_srt_time(end_str)
                
                # Join text lines
                text = '\n'.join(lines[2:])
                
                entries.append(SubtitleEntry(
                    start_time=start_time,
                    end_time=end_time,
                    text=text
                ))
                
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse subtitle block: {e}")
                continue
                
        return entries
    
    @staticmethod
    def parse_vtt(content: str) -> List[SubtitleEntry]:
        """Parse WebVTT subtitle format."""
        entries = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip header and empty lines
            if line.startswith('WEBVTT') or not line:
                i += 1
                continue
                
            # Look for timing line (format: 00:00:00.000 --> 00:00:00.000)
            if '-->' in line:
                try:
                    start_str, end_str = line.split(' --> ')
                    start_time = SubtitleParser._parse_vtt_time(start_str)
                    end_time = SubtitleParser._parse_vtt_time(end_str)
                    
                    # Collect text lines until next timing or end
                    i += 1
                    text_lines = []
                    while i < len(lines) and '-->' not in lines[i] and lines[i].strip():
                        text_lines.append(lines[i])
                        i += 1
                    
                    text = '\n'.join(text_lines)
                    if text:
                        entries.append(SubtitleEntry(
                            start_time=start_time,
                            end_time=end_time,
                            text=text
                        ))
                        
                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not parse VTT timing: {e}")
                    i += 1
            else:
                i += 1
                
        return entries
    
    @staticmethod
    def _parse_srt_time(time_str: str) -> float:
        """Parse SRT time format (HH:MM:SS,mmm) to seconds."""
        time_str = time_str.strip()
        hours, minutes, seconds_ms = time_str.split(':')
        seconds, milliseconds = seconds_ms.split(',')
        
        total_seconds = (
            int(hours) * 3600 +
            int(minutes) * 60 +
            int(seconds) +
            int(milliseconds) / 1000
        )
        return total_seconds
    
    @staticmethod
    def _parse_vtt_time(time_str: str) -> float:
        """Parse VTT time format (HH:MM:SS.mmm) to seconds."""
        time_str = time_str.strip()
        parts = time_str.split(':')
        
        if len(parts) == 3:  # HH:MM:SS.mmm
            hours, minutes, seconds_ms = parts
            seconds, milliseconds = seconds_ms.split('.')
            total_seconds = (
                int(hours) * 3600 +
                int(minutes) * 60 +
                int(seconds) +
                int(milliseconds) / 1000
            )
        elif len(parts) == 2:  # MM:SS.mmm
            minutes, seconds_ms = parts
            seconds, milliseconds = seconds_ms.split('.')
            total_seconds = (
                int(minutes) * 60 +
                int(seconds) +
                int(milliseconds) / 1000
            )
        else:
            raise ValueError(f"Invalid time format: {time_str}")
            
        return total_seconds


class SubtitleManager(QObject):
    """Manages subtitle loading, parsing, and display."""
    
    # Signals
    subtitle_loaded = Signal(SubtitleTrack)
    subtitle_changed = Signal(str)  # subtitle_id
    subtitle_text_updated = Signal(str)  # current subtitle text
    subtitle_error = Signal(str)  # error message
    
    SUPPORTED_FORMATS = ['.srt', '.vtt', '.ass', '.ssa']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks: Dict[str, SubtitleTrack] = {}
        self.current_track: Optional[SubtitleTrack] = None
        self.current_entries: List[SubtitleEntry] = []
        self.current_position: float = 0.0
        self.is_enabled: bool = True
        
        # Timer for subtitle updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_current_subtitle)
        self.update_timer.start(100)  # Update every 100ms
    
    def load_subtitle_file(self, file_path: str, language: str = "Unknown") -> Optional[SubtitleTrack]:
        """Load subtitle file manually."""
        if not os.path.exists(file_path):
            self.subtitle_error.emit(f"Subtitle file not found: {file_path}")
            return None
            
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            self.subtitle_error.emit(f"Unsupported subtitle format: {file_ext}")
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                self.subtitle_error.emit(f"Could not read subtitle file: {e}")
                return None
        except Exception as e:
            self.subtitle_error.emit(f"Error loading subtitle file: {e}")
            return None
            
        # Parse subtitle content
        if file_ext == '.srt':
            entries = SubtitleParser.parse_srt(content)
        elif file_ext == '.vtt':
            entries = SubtitleParser.parse_vtt(content)
        else:
            self.subtitle_error.emit(f"Parser not implemented for {file_ext}")
            return None
            
        if not entries:
            self.subtitle_error.emit("No valid subtitle entries found")
            return None
            
        # Create subtitle track
        track_id = f"file_{len(self.tracks)}"
        track = SubtitleTrack(
            id=track_id,
            language=language,
            title=Path(file_path).stem,
            format=file_ext[1:],  # Remove the dot
            file_path=file_path,
            is_embedded=False
        )
        
        self.tracks[track_id] = track
        self.current_entries = entries
        
        self.subtitle_loaded.emit(track)
        return track
    
    def auto_detect_subtitles(self, video_path: str) -> List[SubtitleTrack]:
        """Automatically detect subtitle files for a video."""
        detected_tracks = []
        
        if not video_path:
            return detected_tracks
            
        video_dir = Path(video_path).parent
        video_name = Path(video_path).stem
        
        # Look for subtitle files with same name
        for ext in self.SUPPORTED_FORMATS:
            subtitle_path = video_dir / f"{video_name}{ext}"
            if subtitle_path.exists():
                track = self.load_subtitle_file(str(subtitle_path))
                if track:
                    detected_tracks.append(track)
                    
        return detected_tracks
    
    def select_subtitle_file(self, parent_widget=None) -> Optional[SubtitleTrack]:
        """Open file dialog to select subtitle file."""
        file_filter = "Subtitle Files (*.srt *.vtt *.ass *.ssa);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Select Subtitle File",
            "",
            file_filter
        )
        
        if file_path:
            return self.load_subtitle_file(file_path)
        return None
    
    def set_active_track(self, track_id: str) -> bool:
        """Set the active subtitle track."""
        if track_id not in self.tracks:
            return False
            
        # Deactivate current track
        if self.current_track:
            self.current_track.is_active = False
            
        # Activate new track
        track = self.tracks[track_id]
        track.is_active = True
        self.current_track = track
        
        # Load subtitle entries for this track
        if track.file_path:
            self.load_subtitle_file(track.file_path, track.language)
            
        self.subtitle_changed.emit(track_id)
        return True
    
    def disable_subtitles(self):
        """Disable subtitle display."""
        if self.current_track:
            self.current_track.is_active = False
            self.current_track = None
        self.is_enabled = False
        self.subtitle_text_updated.emit("")
    
    def enable_subtitles(self):
        """Enable subtitle display."""
        self.is_enabled = True
    
    def update_position(self, position_seconds: float):
        """Update current playback position for subtitle timing."""
        self.current_position = position_seconds
    
    def _update_current_subtitle(self):
        """Update current subtitle text based on position."""
        if not self.is_enabled or not self.current_track or not self.current_entries:
            return
            
        current_text = ""
        
        # Find subtitle entry for current position
        for entry in self.current_entries:
            if entry.start_time <= self.current_position <= entry.end_time:
                current_text = entry.text
                break
                
        self.subtitle_text_updated.emit(current_text)
    
    def get_available_tracks(self) -> List[SubtitleTrack]:
        """Get all available subtitle tracks."""
        return list(self.tracks.values())
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a subtitle track."""
        if track_id in self.tracks:
            track = self.tracks[track_id]
            if track == self.current_track:
                self.disable_subtitles()
            del self.tracks[track_id]
            return True
        return False
    
    def clear_all_tracks(self):
        """Clear all subtitle tracks."""
        self.tracks.clear()
        self.current_track = None
        self.current_entries.clear()
        self.subtitle_text_updated.emit("")

    def detect_embedded_tracks(self, media_url: str) -> List[SubtitleTrack]:
        """
        Detect embedded subtitle tracks in a media stream using ffprobe.

        Args:
            media_url: URL or path to the media file

        Returns:
            List of detected embedded subtitle tracks
        """
        import subprocess
        import json
        from .ffmpeg_manager import get_ffprobe_command

        embedded_tracks = []

        try:
            # Get the appropriate ffprobe command (system or bundled)
            ffprobe_cmd = get_ffprobe_command()

            # Use ffprobe to get stream information
            cmd = ffprobe_cmd + [
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "s",  # Select only subtitle streams
                media_url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])

                for stream in streams:
                    if stream.get("codec_type") == "subtitle":
                        # Extract language and other metadata
                        tags = stream.get("tags", {})
                        language = tags.get("language", "unknown")
                        title = tags.get("title", "")
                        codec_name = stream.get("codec_name", "unknown")
                        stream_index = stream.get("index", 0)

                        # Try to extract language from title if language tag is missing
                        if language == "unknown" and title:
                            title_lower = title.lower()
                            if "arabic" in title_lower or "عربي" in title_lower:
                                language = "ara"
                            elif "english" in title_lower:
                                language = "eng"
                            elif "polish" in title_lower:
                                language = "pol"
                            elif "croatian" in title_lower:
                                language = "hrv"
                            elif "hungarian" in title_lower:
                                language = "hun"
                            elif "italian" in title_lower:
                                language = "ita"
                            elif "spanish" in title_lower:
                                language = "spa"
                            elif "french" in title_lower:
                                language = "fra"
                            elif "german" in title_lower:
                                language = "deu"
                            elif "russian" in title_lower:
                                language = "rus"
                            elif "japanese" in title_lower:
                                language = "jpn"
                            elif "korean" in title_lower:
                                language = "kor"
                            elif "chinese" in title_lower:
                                language = "chi"

                        # Normalize language code to full name
                        language_name = self._normalize_language_code(language)

                        print(f"🔍 Detected subtitle: stream {stream_index}, lang='{language}' -> '{language_name}', title='{title}'")

                        # Create subtitle track
                        track_id = f"embedded_{stream_index}"
                        track = SubtitleTrack(
                            id=track_id,
                            language=language_name,
                            title=f"{language_name} (Embedded)",
                            format=codec_name,
                            is_embedded=True,
                            stream_index=stream_index,
                            codec=codec_name
                        )

                        embedded_tracks.append(track)
                        self.tracks[track_id] = track

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not detect embedded subtitles: {e}")

        return embedded_tracks

    def _normalize_language_code(self, lang_code: str) -> str:
        """
        Normalize language codes to full language names.

        Args:
            lang_code: Language code (e.g., 'eng', 'spa', 'fra')

        Returns:
            Full language name
        """
        language_map = {
            'eng': 'English',
            'spa': 'Spanish',
            'fra': 'French',
            'deu': 'German',
            'ita': 'Italian',
            'por': 'Portuguese',
            'rus': 'Russian',
            'ara': 'Arabic',
            'zho': 'Chinese',
            'chi': 'Chinese',
            'jpn': 'Japanese',
            'kor': 'Korean',
            'hin': 'Hindi',
            'tur': 'Turkish',
            'pol': 'Polish',
            'nld': 'Dutch',
            'dut': 'Dutch',
            'swe': 'Swedish',
            'nor': 'Norwegian',
            'nob': 'Norwegian',
            'dan': 'Danish',
            'fin': 'Finnish',
            'hun': 'Hungarian',
            'hrv': 'Croatian',
            'ind': 'Indonesian',
            'may': 'Malay',
            'tha': 'Thai',
            'vie': 'Vietnamese',
            'rum': 'Romanian',
            'ron': 'Romanian'
        }

        return language_map.get(lang_code.lower(), lang_code.capitalize())

    def set_embedded_track(self, track_id: str) -> bool:
        """
        Set an embedded subtitle track as active.
        This requires integration with the media player.

        Args:
            track_id: ID of the embedded track

        Returns:
            True if successful, False otherwise
        """
        if track_id not in self.tracks:
            return False

        track = self.tracks[track_id]
        if not track.is_embedded:
            return False

        # Deactivate current track
        if self.current_track:
            self.current_track.is_active = False

        # Activate new embedded track
        track.is_active = True
        self.current_track = track

        # Emit signal for media player integration
        self.subtitle_changed.emit(track_id)

        # Note: Actual subtitle display for embedded tracks
        # needs to be handled by the media player (QMediaPlayer)
        # This is just for track management

        return True
