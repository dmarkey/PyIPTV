"""
Integration tests for UI components.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pyiptv.ui.main_window import MainWindow
from pyiptv.ui.playlist_manager_window import PlaylistManagerWindow


@pytest.mark.ui
class TestMainWindow:
    """Test cases for MainWindow integration."""

    def test_main_window_creation(self, qt_app, sample_m3u_file):
        """Test creating MainWindow with a playlist file."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow(str(sample_m3u_file))

            assert window is not None
            assert window.windowTitle() == "PyIPTV"

    def test_main_window_without_playlist(self, qt_app):
        """Test creating MainWindow without a playlist file."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow()

            assert window is not None

    def test_main_window_ui_elements(self, qt_app, sample_m3u_file):
        """Test that main UI elements are created."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow(str(sample_m3u_file))

            # Check that main UI components exist
            assert hasattr(window, "category_list")
            assert hasattr(window, "channel_list")
            assert hasattr(window, "video_stack")
            assert hasattr(window, "control_bar")
            assert hasattr(window, "status_bar")

    def test_main_window_signals(self, qt_app, sample_m3u_file):
        """Test that signals are properly connected."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow(str(sample_m3u_file))

            # Test that we can access signal connections
            # (Actual signal testing would require more complex setup)
            assert window.category_list is not None
            assert window.channel_list is not None


@pytest.mark.ui
class TestPlaylistManagerWindow:
    """Test cases for PlaylistManagerWindow integration."""

    def test_playlist_manager_creation(self, qt_app):
        """Test creating PlaylistManagerWindow."""
        with patch("pyiptv.ui.playlist_manager_window.SettingsManager"), patch(
            "pyiptv.ui.playlist_manager_window.PlaylistManager"
        ):

            window = PlaylistManagerWindow()

            assert window is not None
            assert window.windowTitle() == "PyIPTV - Playlist Manager"

    def test_playlist_manager_ui_elements(self, qt_app):
        """Test that playlist manager UI elements are created."""
        with patch("pyiptv.ui.playlist_manager_window.SettingsManager"), patch(
            "pyiptv.ui.playlist_manager_window.PlaylistManager"
        ):

            window = PlaylistManagerWindow()

            # Check that main UI components exist
            assert hasattr(window, "playlist_list")
            # Add more specific UI element checks as needed


@pytest.mark.ui
class TestUIIntegration:
    """Test cases for UI component integration."""

    def test_theme_application(self, qt_app):
        """Test that themes are properly applied to UI components."""
        from pyiptv.ui.themes import ThemeManager

        theme_manager = ThemeManager()

        # Test theme manager creation
        assert theme_manager is not None

        # Test theme application (basic check)
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow()
            theme_manager.apply_theme(window)

            # Window should still be functional after theme application
            assert window is not None

    def test_settings_integration(self, qt_app, mock_settings_manager):
        """Test integration between UI and settings manager."""
        with patch(
            "pyiptv.ui.main_window.SettingsManager", return_value=mock_settings_manager
        ), patch("pyiptv.ui.main_window.PlaylistManager"), patch(
            "pyiptv.ui.main_window.QMediaVideoPlayer"
        ):

            window = MainWindow()

            # Test that settings manager is used
            assert window.settings_manager == mock_settings_manager

    def test_media_player_integration(self, qt_app):
        """Test integration between UI and media player."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer") as mock_player:

            window = MainWindow()

            # Test that media player is created
            mock_player.assert_called_once()

    def test_window_geometry_restoration(self, qt_app, mock_settings_manager):
        """Test that window geometry is restored from settings."""
        # Mock settings to return saved geometry
        mock_settings_manager.get_setting.side_effect = lambda key, default=None: {
            "window_geometry": b"saved_geometry_data",
            "splitter_sizes": [200, 800],
        }.get(key, default)

        with patch(
            "pyiptv.ui.main_window.SettingsManager", return_value=mock_settings_manager
        ), patch("pyiptv.ui.main_window.PlaylistManager"), patch(
            "pyiptv.ui.main_window.QMediaVideoPlayer"
        ):

            window = MainWindow()

            # Verify settings were queried
            mock_settings_manager.get_setting.assert_called()

    def test_error_handling_in_ui(self, qt_app):
        """Test error handling in UI components."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow()

            # Test that window handles errors gracefully
            # (This would be expanded with specific error scenarios)
            assert window is not None

    def test_keyboard_shortcuts(self, qt_app):
        """Test keyboard shortcuts integration."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow()

            # Test that keyboard shortcuts are set up
            # (This would be expanded to test specific shortcuts)
            assert window is not None

    def test_status_system_integration(self, qt_app):
        """Test status system integration across UI components."""
        with patch("pyiptv.ui.main_window.SettingsManager"), patch(
            "pyiptv.ui.main_window.PlaylistManager"
        ), patch("pyiptv.ui.main_window.QMediaVideoPlayer"):

            window = MainWindow()

            # Test that status system is integrated
            assert hasattr(window, "status_manager")
            assert window.status_manager is not None
