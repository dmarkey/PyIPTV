"""
Unit tests for Settings Manager functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from pyiptv.settings_manager import SettingsManager


class TestSettingsManager:
    """Test cases for SettingsManager class."""

    def test_init_default_settings(self, temp_dir):
        """Test SettingsManager initialization with default settings."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            # Should have default settings
            assert manager.get_setting("volume") == 80
            assert manager.get_setting("buffering_ms") == 1500
            assert manager.get_setting("theme_mode") == "system_auto"

    def test_init_existing_settings_file(self, temp_dir):
        """Test SettingsManager initialization with existing settings file."""
        settings_file = temp_dir / "test_settings.json"

        # Create existing settings file
        existing_settings = {
            "volume": 50,
            "buffering_ms": 2000,
            "custom_setting": "test_value",
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            # Should load existing settings
            assert manager.get_setting("volume") == 50
            assert manager.get_setting("buffering_ms") == 2000
            assert manager.get_setting("custom_setting") == "test_value"

            # Should still have defaults for missing keys
            assert manager.get_setting("theme_mode") == "system_auto"

    def test_get_setting_existing(self, temp_dir):
        """Test getting an existing setting."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            assert manager.get_setting("volume") == 80
            assert manager.get_setting("buffering_ms") == 1500

    def test_get_setting_non_existing(self, temp_dir):
        """Test getting a non-existing setting."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            assert manager.get_setting("non_existing_key") is None

    def test_get_setting_with_default(self, temp_dir):
        """Test getting a setting with a default value."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            assert (
                manager.get_setting("non_existing_key", "default_value")
                == "default_value"
            )

    def test_set_setting(self, temp_dir):
        """Test setting a value."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            manager.set_setting("volume", 90)
            assert manager.get_setting("volume") == 90

            manager.set_setting("new_setting", "new_value")
            assert manager.get_setting("new_setting") == "new_value"

    def test_save_settings(self, temp_dir):
        """Test saving settings to file."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            manager.set_setting("volume", 90)
            manager.save_settings()

            # Verify file was created and contains correct data
            assert settings_file.exists()
            saved_data = json.loads(settings_file.read_text())
            assert saved_data["volume"] == 90

    def test_load_settings_corrupted_file(self, temp_dir):
        """Test loading settings from corrupted JSON file."""
        settings_file = temp_dir / "test_settings.json"

        # Create corrupted JSON file
        settings_file.write_text("invalid json content")

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            # Should fall back to defaults
            assert manager.get_setting("volume") == 80

    def test_get_settings_file_path_linux(self):
        """Test settings file path on Linux."""
        with patch("platform.system", return_value="Linux"), patch(
            "os.path.expanduser", return_value="/home/user"
        ):

            manager = SettingsManager()
            path = manager._get_settings_filepath("test.json")

            assert "/home/user/.config/PyIPTV/test.json" in path

    def test_get_settings_file_path_windows(self):
        """Test settings file path on Windows."""
        with patch("platform.system", return_value="Windows"), patch(
            "os.environ.get", return_value="C:\\Users\\User\\AppData\\Roaming"
        ):

            manager = SettingsManager()
            path = manager._get_settings_filepath("test.json")

            assert "PyIPTV\\test.json" in path

    def test_get_settings_file_path_macos(self):
        """Test settings file path on macOS."""
        with patch("platform.system", return_value="Darwin"), patch(
            "os.path.expanduser", return_value="/Users/user"
        ):

            manager = SettingsManager()
            path = manager._get_settings_filepath("test.json")

            assert "/Users/user/.config/PyIPTV/test.json" in path

    def test_directory_creation(self, temp_dir):
        """Test that settings directory is created if it doesn't exist."""
        settings_dir = temp_dir / "new_config_dir"
        settings_file = settings_dir / "pyiptv_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()
            manager.save_settings()

            # Directory should be created
            assert settings_dir.exists()
            assert settings_file.exists()

    def test_reset_to_defaults(self, temp_dir):
        """Test resetting settings to defaults."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            manager = SettingsManager()

            # Change some settings
            manager.set_setting("volume", 90)
            manager.set_setting("custom_setting", "custom_value")

            # Reset to defaults
            manager.settings = manager.DEFAULT_SETTINGS.copy()

            assert manager.get_setting("volume") == 80
            assert manager.get_setting("custom_setting") is None

    def test_settings_persistence(self, temp_dir):
        """Test that settings persist across instances."""
        settings_file = temp_dir / "test_settings.json"

        with patch(
            "pyiptv.settings_manager.SettingsManager._get_settings_filepath",
            return_value=str(settings_file),
        ):
            # First instance
            manager1 = SettingsManager()
            manager1.set_setting("volume", 95)
            manager1.save_settings()

            # Second instance should load the saved settings
            manager2 = SettingsManager()
            assert manager2.get_setting("volume") == 95

    def test_default_settings_completeness(self):
        """Test that all expected default settings are present."""
        expected_keys = [
            "m3u_filepath",
            "last_played_url",
            "volume",
            "buffering_ms",
            "hidden_categories",
            "window_geometry",
            "auto_play_last",
            "default_category",
            "splitter_sizes",
            "theme_mode",
            "large_file_threshold",
            "search_delay_ms",
            "render_buffer_size",
            "progress_update_interval",
        ]

        for key in expected_keys:
            assert key in SettingsManager.DEFAULT_SETTINGS
