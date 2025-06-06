"""
Unit tests for Playlist Manager functionality.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pyiptv.playlist_manager import PlaylistEntry, PlaylistManager


class TestPlaylistEntry:
    """Test cases for PlaylistEntry class."""

    def test_init_file_playlist(self):
        """Test PlaylistEntry initialization for file-based playlist."""
        entry = PlaylistEntry(
            name="Test Playlist", source="/path/to/playlist.m3u", source_type="file"
        )

        assert entry.name == "Test Playlist"
        assert entry.source == "/path/to/playlist.m3u"
        assert entry.source_type == "file"
        assert entry.id is not None
        assert entry.channel_count == 0
        assert entry.last_opened is None
        assert entry.cached_file_path is None

    def test_init_url_playlist(self):
        """Test PlaylistEntry initialization for URL-based playlist."""
        entry = PlaylistEntry(
            name="URL Playlist",
            source="http://example.com/playlist.m3u",
            source_type="url",
        )

        assert entry.name == "URL Playlist"
        assert entry.source == "http://example.com/playlist.m3u"
        assert entry.source_type == "url"

    def test_update_last_opened(self):
        """Test updating last opened timestamp."""
        entry = PlaylistEntry("Test", "/path", "file")

        before = datetime.now()
        entry.update_last_opened()
        after = datetime.now()

        # last_opened is stored as ISO string, so parse it back
        last_opened_dt = datetime.fromisoformat(entry.last_opened)
        assert before <= last_opened_dt <= after

    @patch("os.path.exists")
    def test_needs_refresh_no_last_opened(self, mock_exists):
        """Test needs_refresh when never opened."""
        mock_exists.return_value = True  # File exists
        entry = PlaylistEntry("Test", "/path", "file")
        assert entry.needs_refresh() is True

    def test_needs_refresh_file_not_exists(self):
        """Test needs_refresh when file doesn't exist."""
        entry = PlaylistEntry("Test", "/nonexistent/path", "file")
        entry.update_last_opened()
        assert entry.needs_refresh() is False

    @patch("os.path.getmtime")
    @patch("os.path.exists")
    def test_needs_refresh_file_newer(self, mock_exists, mock_getmtime):
        """Test needs_refresh when file is newer than last opened."""
        mock_exists.return_value = True
        mock_getmtime.return_value = 2000.0  # File modified time

        entry = PlaylistEntry("Test", "/path", "file")
        entry.last_opened = datetime.fromtimestamp(
            1000.0
        ).isoformat()  # Older than file

        assert entry.needs_refresh() is True

    @patch("os.path.getmtime")
    @patch("os.path.exists")
    def test_needs_refresh_file_older(self, mock_exists, mock_getmtime):
        """Test needs_refresh when file is older than last opened."""
        mock_exists.return_value = True
        mock_getmtime.return_value = 1000.0  # File modified time

        entry = PlaylistEntry("Test", "/path", "file")
        entry.last_opened = datetime.fromtimestamp(
            2000.0
        ).isoformat()  # Newer than file

        assert entry.needs_refresh() is False

    def test_to_dict(self):
        """Test converting PlaylistEntry to dictionary."""
        entry = PlaylistEntry("Test", "/path", "file")
        entry.channel_count = 100
        entry.update_last_opened()

        data = entry.to_dict()

        assert data["name"] == "Test"
        assert data["source"] == "/path"
        assert data["source_type"] == "file"
        assert data["channel_count"] == 100
        assert "last_opened" in data

    def test_from_dict(self):
        """Test creating PlaylistEntry from dictionary."""
        data = {
            "id": "test-id",
            "name": "Test",
            "source": "/path",
            "source_type": "file",
            "channel_count": 100,
            "last_opened": "2023-01-01T12:00:00",
            "cached_file_path": "/cache/path",
        }

        entry = PlaylistEntry.from_dict(data)

        assert entry.id == "test-id"
        assert entry.name == "Test"
        assert entry.source == "/path"
        assert entry.source_type == "file"
        assert entry.channel_count == 100
        assert entry.cached_file_path == "/cache/path"


class TestPlaylistManager:
    """Test cases for PlaylistManager class."""

    def _patch_playlist_manager(self, temp_dir):
        """Helper to patch PlaylistManager methods."""
        from contextlib import ExitStack

        playlists_file = temp_dir / "playlists.json"
        cache_dir = temp_dir / "cache"

        stack = ExitStack()
        stack.enter_context(
            patch.object(
                PlaylistManager,
                "_get_playlists_file_path",
                return_value=str(playlists_file),
            )
        )
        stack.enter_context(
            patch.object(
                PlaylistManager, "_get_cache_directory", return_value=str(cache_dir)
            )
        )
        return stack

    def test_init(self, mock_settings_manager, temp_dir):
        """Test PlaylistManager initialization."""
        with self._patch_playlist_manager(temp_dir):
            manager = PlaylistManager(mock_settings_manager)

            assert manager.settings_manager == mock_settings_manager
            assert len(manager.playlists) == 0

    def test_add_playlist_file(self, mock_settings_manager, temp_dir):
        """Test adding a file-based playlist."""
        playlists_file = temp_dir / "playlists.json"
        test_m3u_file = temp_dir / "test.m3u"
        test_m3u_file.write_text("#EXTM3U\n")  # Create a test file

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ), patch.object(
            PlaylistManager,
            "_get_cache_directory",
            return_value=str(temp_dir / "cache"),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist(
                name="Test Playlist", source=str(test_m3u_file), source_type="file"
            )

            assert playlist.name == "Test Playlist"
            assert playlist.source == str(test_m3u_file)
            assert playlist.source_type == "file"
            assert playlist.id in manager.playlists

    def test_add_playlist_url(self, mock_settings_manager, temp_dir):
        """Test adding a URL-based playlist."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ), patch.object(
            PlaylistManager,
            "_get_cache_directory",
            return_value=str(temp_dir / "cache"),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist(
                name="URL Playlist",
                source="http://example.com/playlist.m3u",
                source_type="url",
            )

            assert playlist.source_type == "url"
            assert playlist.cached_file_path is not None

    def test_remove_playlist(self, mock_settings_manager, temp_dir):
        """Test removing a playlist."""
        playlists_file = temp_dir / "playlists.json"
        test_m3u_file = temp_dir / "test.m3u"
        test_m3u_file.write_text("#EXTM3U\n")

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ), patch.object(
            PlaylistManager,
            "_get_cache_directory",
            return_value=str(temp_dir / "cache"),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist("Test", str(test_m3u_file), "file")
            playlist_id = playlist.id

            assert manager.remove_playlist(playlist_id) is True
            assert playlist_id not in manager.playlists

            # Try to remove non-existent playlist
            assert manager.remove_playlist("non-existent") is False

    def test_get_playlist(self, mock_settings_manager, temp_dir):
        """Test getting a playlist by ID."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist("Test", "/path", "file")

            retrieved = manager.get_playlist(playlist.id)
            assert retrieved == playlist

            # Test non-existent playlist
            assert manager.get_playlist("non-existent") is None

    def test_get_all_playlists(self, mock_settings_manager, temp_dir):
        """Test getting all playlists."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist1 = manager.add_playlist("Test 1", "/path1", "file")
            playlist2 = manager.add_playlist("Test 2", "/path2", "file")

            all_playlists = manager.get_all_playlists()

            assert len(all_playlists) == 2
            assert playlist1 in all_playlists
            assert playlist2 in all_playlists

    def test_save_and_load_playlists(self, mock_settings_manager, temp_dir):
        """Test saving and loading playlists."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ):
            # Create manager and add playlist
            manager1 = PlaylistManager(mock_settings_manager)
            playlist = manager1.add_playlist("Test", "/path", "file")
            playlist_id = playlist.id

            # Create new manager instance (should load saved data)
            manager2 = PlaylistManager(mock_settings_manager)

            assert len(manager2.playlists) == 1
            assert playlist_id in manager2.playlists
            assert manager2.playlists[playlist_id].name == "Test"

    def test_mark_playlist_opened(self, mock_settings_manager, temp_dir):
        """Test marking a playlist as opened."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist("Test", "/path", "file")
            assert playlist.last_opened is None

            manager.mark_playlist_opened(playlist.id)

            assert playlist.last_opened is not None

    def test_update_channel_count(self, mock_settings_manager, temp_dir):
        """Test updating channel count for a playlist."""
        playlists_file = temp_dir / "playlists.json"

        with patch.object(
            PlaylistManager,
            "_get_playlists_file_path",
            return_value=str(playlists_file),
        ):
            manager = PlaylistManager(mock_settings_manager)

            playlist = manager.add_playlist("Test", "/path", "file")
            assert playlist.channel_count == 0

            manager.update_channel_count(playlist.id, 150)

            assert playlist.channel_count == 150
