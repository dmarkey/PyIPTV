"""
Unit tests for Subtitle Manager functionality.
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from pyiptv.subtitle_manager import SubtitleManager, SubtitleParser, SubtitleTrack, SubtitleEntry


class TestSubtitleParser:
    """Test cases for SubtitleParser class."""

    def test_parse_srt_basic(self):
        """Test parsing basic SRT content."""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,500 --> 00:00:06,500
This is a test subtitle.
"""
        entries = SubtitleParser.parse_srt(srt_content)
        
        assert len(entries) == 2
        
        # Check first entry
        assert entries[0].start_time == 1.0
        assert entries[0].end_time == 3.0
        assert entries[0].text == "Hello, world!"
        
        # Check second entry
        assert entries[1].start_time == 4.5
        assert entries[1].end_time == 6.5
        assert entries[1].text == "This is a test subtitle."

    def test_parse_srt_multiline(self):
        """Test parsing SRT with multiline text."""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Line 1
Line 2
Line 3
"""
        entries = SubtitleParser.parse_srt(srt_content)
        
        assert len(entries) == 1
        assert entries[0].text == "Line 1\nLine 2\nLine 3"

    def test_parse_vtt_basic(self):
        """Test parsing basic WebVTT content."""
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello, world!

00:00:04.500 --> 00:00:06.500
This is a test subtitle.
"""
        entries = SubtitleParser.parse_vtt(vtt_content)
        
        assert len(entries) == 2
        
        # Check first entry
        assert entries[0].start_time == 1.0
        assert entries[0].end_time == 3.0
        assert entries[0].text == "Hello, world!"
        
        # Check second entry
        assert entries[1].start_time == 4.5
        assert entries[1].end_time == 6.5
        assert entries[1].text == "This is a test subtitle."

    def test_parse_srt_time_conversion(self):
        """Test SRT time format conversion."""
        # Test various time formats
        assert SubtitleParser._parse_srt_time("00:00:01,000") == 1.0
        assert SubtitleParser._parse_srt_time("00:01:30,500") == 90.5
        assert SubtitleParser._parse_srt_time("01:23:45,123") == 5025.123

    def test_parse_vtt_time_conversion(self):
        """Test VTT time format conversion."""
        # Test various time formats
        assert SubtitleParser._parse_vtt_time("00:00:01.000") == 1.0
        assert SubtitleParser._parse_vtt_time("01:30.500") == 90.5
        assert SubtitleParser._parse_vtt_time("01:23:45.123") == 5025.123

    def test_parse_srt_malformed(self):
        """Test parsing malformed SRT content."""
        malformed_content = """1
Invalid timing line
Hello, world!

2
00:00:04,500 --> 00:00:06,500
Valid subtitle.
"""
        entries = SubtitleParser.parse_srt(malformed_content)
        
        # Should only parse the valid entry
        assert len(entries) == 1
        assert entries[0].text == "Valid subtitle."


class TestSubtitleManager:
    """Test cases for SubtitleManager class."""

    def test_init(self, qt_app):
        """Test SubtitleManager initialization."""
        manager = SubtitleManager()
        
        assert len(manager.tracks) == 0
        assert manager.current_track is None
        assert manager.is_enabled is True
        assert manager.current_position == 0.0

    def test_load_subtitle_file_srt(self, qt_app, temp_dir):
        """Test loading SRT subtitle file."""
        manager = SubtitleManager()
        
        # Create test SRT file
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Test subtitle
"""
        srt_file = temp_dir / "test.srt"
        srt_file.write_text(srt_content, encoding='utf-8')
        
        track = manager.load_subtitle_file(str(srt_file), "English")
        
        assert track is not None
        assert track.language == "English"
        assert track.format == "srt"
        assert track.file_path == str(srt_file)
        assert not track.is_embedded
        assert len(manager.current_entries) == 1

    def test_load_subtitle_file_not_found(self, qt_app):
        """Test loading non-existent subtitle file."""
        manager = SubtitleManager()
        
        track = manager.load_subtitle_file("non_existent.srt")
        
        assert track is None

    def test_load_subtitle_file_unsupported_format(self, qt_app, temp_dir):
        """Test loading unsupported subtitle format."""
        manager = SubtitleManager()
        
        # Create test file with unsupported extension
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("Some text")
        
        track = manager.load_subtitle_file(str(txt_file))
        
        assert track is None

    def test_auto_detect_subtitles(self, qt_app, temp_dir):
        """Test automatic subtitle detection."""
        manager = SubtitleManager()
        
        # Create video file and matching subtitle files
        video_file = temp_dir / "movie.mp4"
        video_file.write_text("fake video content")
        
        srt_file = temp_dir / "movie.srt"
        srt_file.write_text("""1
00:00:01,000 --> 00:00:03,000
Test subtitle
""")
        
        vtt_file = temp_dir / "movie.vtt"
        vtt_file.write_text("""WEBVTT

00:00:01.000 --> 00:00:03.000
Test subtitle
""")
        
        tracks = manager.auto_detect_subtitles(str(video_file))
        
        assert len(tracks) == 2
        formats = [track.format for track in tracks]
        assert "srt" in formats
        assert "vtt" in formats

    def test_set_active_track(self, qt_app, temp_dir):
        """Test setting active subtitle track."""
        manager = SubtitleManager()
        
        # Load a subtitle file
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Test subtitle
"""
        srt_file = temp_dir / "test.srt"
        srt_file.write_text(srt_content)
        
        track = manager.load_subtitle_file(str(srt_file))
        
        # Set as active track
        success = manager.set_active_track(track.id)
        
        assert success is True
        assert manager.current_track == track
        assert track.is_active is True

    def test_set_active_track_invalid(self, qt_app):
        """Test setting invalid track as active."""
        manager = SubtitleManager()
        
        success = manager.set_active_track("invalid_id")
        
        assert success is False
        assert manager.current_track is None

    def test_disable_enable_subtitles(self, qt_app):
        """Test disabling and enabling subtitles."""
        manager = SubtitleManager()
        
        # Disable subtitles
        manager.disable_subtitles()
        assert manager.is_enabled is False
        assert manager.current_track is None
        
        # Enable subtitles
        manager.enable_subtitles()
        assert manager.is_enabled is True

    def test_update_position(self, qt_app):
        """Test updating playback position."""
        manager = SubtitleManager()
        
        manager.update_position(123.45)
        
        assert manager.current_position == 123.45

    def test_remove_track(self, qt_app, temp_dir):
        """Test removing subtitle track."""
        manager = SubtitleManager()
        
        # Load a subtitle file
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Test subtitle
"""
        srt_file = temp_dir / "test.srt"
        srt_file.write_text(srt_content)
        
        track = manager.load_subtitle_file(str(srt_file))
        track_id = track.id
        
        # Remove track
        success = manager.remove_track(track_id)
        
        assert success is True
        assert track_id not in manager.tracks

    def test_clear_all_tracks(self, qt_app, temp_dir):
        """Test clearing all subtitle tracks."""
        manager = SubtitleManager()
        
        # Load multiple subtitle files
        for i in range(3):
            srt_content = f"""1
00:00:0{i+1},000 --> 00:00:0{i+3},000
Test subtitle {i+1}
"""
            srt_file = temp_dir / f"test{i}.srt"
            srt_file.write_text(srt_content)
            manager.load_subtitle_file(str(srt_file))
        
        assert len(manager.tracks) == 3
        
        # Clear all tracks
        manager.clear_all_tracks()
        
        assert len(manager.tracks) == 0
        assert manager.current_track is None
        assert len(manager.current_entries) == 0

    def test_subtitle_timing(self, qt_app, temp_dir):
        """Test subtitle timing and text updates."""
        manager = SubtitleManager()
        
        # Create subtitle with specific timing
        srt_content = """1
00:00:01,000 --> 00:00:03,000
First subtitle

2
00:00:05,000 --> 00:00:07,000
Second subtitle
"""
        srt_file = temp_dir / "test.srt"
        srt_file.write_text(srt_content)
        
        track = manager.load_subtitle_file(str(srt_file))
        manager.set_active_track(track.id)
        
        # Test different positions
        manager.update_position(0.5)  # Before first subtitle
        manager._update_current_subtitle()
        
        manager.update_position(2.0)  # During first subtitle
        manager._update_current_subtitle()
        
        manager.update_position(4.0)  # Between subtitles
        manager._update_current_subtitle()
        
        manager.update_position(6.0)  # During second subtitle
        manager._update_current_subtitle()
        
        # Verify timing logic works (actual text verification would need signal testing)
