"""
Unit tests for M3U parser functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pyiptv.m3u_parser import M3UParser


class TestM3UParser:
    """Test cases for M3UParser class."""

    def test_init(self, mock_cache_manager):
        """Test M3UParser initialization."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        assert parser.cache_manager == mock_cache_manager

    def test_parse_m3u_from_content_basic(self, sample_m3u_content, mock_cache_manager):
        """Test parsing M3U content with basic channels."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = sample_m3u_content.splitlines()

        channels, categories = parser.parse_m3u_from_content(content_lines)

        assert len(channels) == 3
        assert len(categories) == 3  # News, Sports, Movies

        # Check first channel
        first_channel = channels[0]
        assert first_channel["name"] == "Test Channel 1"
        assert first_channel["url"] == "http://example.com/stream1.m3u8"
        assert first_channel["tvg-id"] == "channel1"  # Note: hyphen, not underscore
        assert first_channel["group-title"] == "News"  # Note: hyphen, not underscore
        assert first_channel["tvg-logo"] == "logo1.png"  # Note: hyphen, not underscore

    def test_parse_m3u_from_content_empty(self, mock_cache_manager):
        """Test parsing empty M3U content."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = []

        channels, categories = parser.parse_m3u_from_content(content_lines)

        assert len(channels) == 0
        assert len(categories) == 0

    def test_parse_m3u_from_content_no_extinf(self, mock_cache_manager):
        """Test parsing M3U content without EXTINF lines."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = [
            "#EXTM3U",
            "http://example.com/stream1.m3u8",
            "http://example.com/stream2.m3u8",
        ]

        channels, _ = parser.parse_m3u_from_content(content_lines)

        # Without EXTINF lines, URLs alone won't create channels in this implementation
        assert len(channels) == 0

    def test_parse_m3u_from_content_malformed_extinf(self, mock_cache_manager):
        """Test parsing M3U content with malformed EXTINF lines."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = [
            "#EXTM3U",
            "#EXTINF:-1,Channel Name",  # Missing attributes
            "http://example.com/stream1.m3u8",
            "#EXTINF:invalid",  # Invalid format
            "http://example.com/stream2.m3u8",
        ]

        channels, _ = parser.parse_m3u_from_content(content_lines)

        assert len(channels) == 1  # Only the valid one should be parsed
        assert channels[0]["name"] == "Channel Name"

    def test_parse_m3u_from_content_with_categories(self, mock_cache_manager):
        """Test parsing M3U content and category organization."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = [
            "#EXTM3U",
            '#EXTINF:-1 group-title="News",Channel 1',
            "http://example.com/stream1.m3u8",
            '#EXTINF:-1 group-title="News",Channel 2',
            "http://example.com/stream2.m3u8",
            '#EXTINF:-1 group-title="Sports",Channel 3',
            "http://example.com/stream3.m3u8",
        ]

        channels, categories = parser.parse_m3u_from_content(content_lines)

        assert len(channels) == 3
        assert len(categories) == 2
        assert len(categories["News"]) == 2
        assert len(categories["Sports"]) == 1

    def test_parse_m3u_file_not_found(self, mock_cache_manager):
        """Test parsing non-existent M3U file."""
        parser = M3UParser(cache_manager=mock_cache_manager)

        # The method returns empty lists instead of raising an exception
        channels, categories = parser.parse_m3u_from_file("non_existent_file.m3u")
        assert len(channels) == 0
        assert len(categories) == 0

    def test_parse_m3u_file_success(self, sample_m3u_file, mock_cache_manager):
        """Test successful parsing of M3U file."""
        parser = M3UParser(cache_manager=mock_cache_manager)

        channels, categories = parser.parse_m3u_from_file(str(sample_m3u_file))

        assert len(channels) == 3
        assert len(categories) == 3

    def test_parse_m3u_file_with_cache(self, sample_m3u_file, mock_cache_manager):
        """Test M3U file parsing with cache."""
        # Mock cache hit
        mock_cache_manager.load_cache.return_value = (
            [{"name": "Cached Channel", "url": "http://cached.com"}],
            {"Cached": [{"name": "Cached Channel"}]},
        )

        parser = M3UParser(cache_manager=mock_cache_manager)
        channels, _ = parser.parse_m3u_from_file(str(sample_m3u_file))

        assert len(channels) == 1
        assert channels[0]["name"] == "Cached Channel"
        mock_cache_manager.load_cache.assert_called_once()

    def test_extract_extinf_attributes(self, mock_cache_manager):
        """Test extraction of EXTINF attributes."""
        parser = M3UParser(cache_manager=mock_cache_manager)

        extinf_line = '#EXTINF:-1 tvg-id="test" tvg-name="Test" tvg-logo="logo.png" group-title="Category",Display Name'

        # Access the private method for testing
        attributes = parser._parse_extinf_line(extinf_line)

        assert attributes["tvg-id"] == "test"
        assert attributes["tvg-name"] == "Test"
        assert attributes["tvg-logo"] == "logo.png"
        assert attributes["group-title"] == "Category"
        assert attributes["name"] == "Display Name"

    def test_extract_extinf_attributes_minimal(self, mock_cache_manager):
        """Test extraction of minimal EXTINF attributes."""
        parser = M3UParser(cache_manager=mock_cache_manager)

        extinf_line = "#EXTINF:-1,Simple Channel"

        attributes = parser._parse_extinf_line(extinf_line)

        assert attributes["name"] == "Simple Channel"
        assert attributes["tvg-id"] == ""
        assert attributes["group-title"] == "Uncategorized"

    @patch("pyiptv.m3u_parser.time.time")
    def test_progress_reporting(self, mock_time, mock_cache_manager):
        """Test progress reporting during parsing."""
        mock_time.return_value = 1000.0

        progress_callback = Mock()
        parser = M3UParser(cache_manager=mock_cache_manager)

        # Create content with many channels to trigger progress updates
        content_lines = ["#EXTM3U"]
        for i in range(2000):  # More than progress_update_interval
            content_lines.extend(
                [f"#EXTINF:-1,Channel {i}", f"http://example.com/stream{i}.m3u8"]
            )

        parser.parse_m3u_from_content(
            content_lines, progress_callback=progress_callback
        )

        # Should have called progress callback multiple times
        assert progress_callback.call_count > 1

    def test_unicode_handling(self, mock_cache_manager):
        """Test handling of Unicode characters in M3U content."""
        parser = M3UParser(cache_manager=mock_cache_manager)
        content_lines = [
            "#EXTM3U",
            "#EXTINF:-1,Chaîne Française 🇫🇷",
            "http://example.com/french.m3u8",
            "#EXTINF:-1,канал русский 🇷🇺",
            "http://example.com/russian.m3u8",
        ]

        channels, _ = parser.parse_m3u_from_content(content_lines)

        assert len(channels) == 2
        assert channels[0]["name"] == "Chaîne Française 🇫🇷"
        assert channels[1]["name"] == "канал русский 🇷🇺"
