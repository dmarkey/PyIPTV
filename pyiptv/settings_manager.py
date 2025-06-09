import json
import os


class SettingsManager:
    """
    Manages application settings, loading from and saving to a JSON file.
    """

    DEFAULT_SETTINGS = {
        "m3u_filepath": None,
        "last_played_url": None,
        "volume": 80,
        "buffering_ms": 1500,  # Default buffering time in milliseconds
        "hidden_categories": [],
        "window_geometry": None,  # To store window size and position
        "auto_play_last": False,
        "default_category": "All Channels",  # Or some other sensible default
        "splitter_sizes": None,
        # Theme settings
        "theme_mode": "system_auto",  # Auto-detect system theme (KDE-aware)
        # Performance settings for large files
        "large_file_threshold": 1000000,  # 1M channels threshold
        "search_delay_ms": 300,  # Search delay in milliseconds
        "render_buffer_size": 5,  # Extra items to render for smooth scrolling
        "progress_update_interval": 1000,  # Update progress every N channels
        # Enhanced features settings
        "auto_save_m3u": True,  # Auto-save edited M3U files
        "auto_update_playlists": True,  # Automatic playlist updates
        "auto_update_interval_hours": 24,  # Update interval in hours
        "dead_link_detection": True,  # Enable dead link detection
        "dead_link_check_interval_hours": 6,  # Check interval for dead links
        "dead_link_timeout_seconds": 10,  # Timeout for link checking
        "auto_remove_dead_links": False,  # Auto-remove dead links (default: false for safety)
        "recording_enabled": True,  # Enable recording functionality
        "recording_output_dir": None,  # Will be set to default recordings folder
        "recording_format": "mp4",  # Default recording format
        # Geolocation-based subtitle settings
        "geolocation_auto_detect": True,  # Enable automatic geolocation detection
        "geolocation_check_interval_hours": 24,  # How often to check location
        "geolocation_auto_subtitle": True,  # Auto-select subtitles based on location
        "manual_subtitle_languages": None,  # Manual override for subtitle languages
        "cached_geolocation": None,  # Cached location data
        "max_search_results": 50000,  # Limit search results for performance
        "enable_channel_icons": False,  # Disable icons for large files by default
    }

    def __init__(self, settings_filename="pyiptv_settings.json"):
        """
        Initializes the SettingsManager.

        Args:
            settings_filename (str): The name of the file to store settings.
                                     It will be created in the user's config directory.
        """
        self.settings_filepath = self._get_settings_filepath(settings_filename)
        self.settings = self.DEFAULT_SETTINGS.copy()  # Start with defaults
        self.load_settings()

    def _get_settings_filepath(self, filename):
        """
        Determines the appropriate path for the settings file.
        This typically places it in a user-specific config directory.
        """
        if os.name == "nt":  # Windows
            app_data_dir = os.getenv("APPDATA")
            if not app_data_dir:
                # Fallback if APPDATA is not set (unlikely for modern Windows)
                app_data_dir = os.path.expanduser("~")
            config_dir = os.path.join(app_data_dir, "PyIPTV")
        else:  # Linux, macOS
            xdg_config_home = os.getenv("XDG_CONFIG_HOME")
            if xdg_config_home:
                config_dir = os.path.join(xdg_config_home, "PyIPTV")
            else:
                # Fallback to ~/.config/PyIPTV
                config_dir = os.path.join(os.path.expanduser("~"), ".config", "PyIPTV")

        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError as e:
                print(f"Warning: Could not create config directory {config_dir}: {e}")
                # Fallback to current directory if config dir creation fails
                return os.path.join(os.getcwd(), filename)
        return os.path.join(config_dir, filename)

    def load_settings(self):
        """Loads settings from the JSON file."""
        if os.path.exists(self.settings_filepath):
            try:
                with open(self.settings_filepath, "r") as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys are present
                    # and new default settings are picked up if the file is old.
                    for key in self.DEFAULT_SETTINGS:
                        if key in loaded_settings:
                            self.settings[key] = loaded_settings[key]
                        else:
                            self.settings[key] = self.DEFAULT_SETTINGS[key]
                    # Also, add any keys from loaded_settings that are not in DEFAULT_SETTINGS
                    # (though this shouldn't happen if DEFAULT_SETTINGS is comprehensive)
                    for key in loaded_settings:
                        if key not in self.settings:
                            self.settings[key] = loaded_settings[key]

            except json.JSONDecodeError:
                print(
                    f"Warning: Could not decode JSON from {self.settings_filepath}. Using default settings."
                )
                # Create backup of corrupted file
                try:
                    import shutil

                    backup_path = f"{self.settings_filepath}.backup"
                    shutil.copy2(self.settings_filepath, backup_path)
                    print(f"Corrupted settings backed up to {backup_path}")
                except Exception as backup_error:
                    print(f"Could not backup corrupted settings: {backup_error}")

                self.settings = self.DEFAULT_SETTINGS.copy()
                # Try to save clean settings immediately
                try:
                    self.save_settings()
                    print(
                        f"Created new clean settings file at {self.settings_filepath}"
                    )
                except Exception as save_error:
                    print(f"Could not save clean settings: {save_error}")
            except Exception as e:
                print(
                    f"Error loading settings from {self.settings_filepath}: {e}. Using default settings."
                )
                self.settings = self.DEFAULT_SETTINGS.copy()
        else:
            print(
                f"Settings file not found at {self.settings_filepath}. Using default settings and creating a new one on save."
            )
            self.settings = (
                self.DEFAULT_SETTINGS.copy()
            )  # Ensure defaults are used if file doesn't exist
            # self.save_settings() # Optionally save defaults immediately

    def save_settings(self):
        """Saves the current settings to the JSON file."""
        try:
            # Ensure the directory exists before writing
            os.makedirs(os.path.dirname(self.settings_filepath), exist_ok=True)

            # Create a copy of settings with any bytes objects converted to strings
            safe_settings = self._make_json_safe(self.settings)

            with open(self.settings_filepath, "w") as f:
                json.dump(safe_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings to {self.settings_filepath}: {e}")

    def _make_json_safe(self, obj):
        """
        Recursively convert any bytes objects to base64 strings for JSON serialization.
        """
        import base64

        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        elif isinstance(obj, dict):
            return {key: self._make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_json_safe(item) for item in obj)
        else:
            return obj

    def get_setting(self, key, default=None):
        """
        Retrieves a specific setting.

        Args:
            key (str): The key of the setting to retrieve.
            default: The default value to return if the key doesn't exist.

        Returns:
            The value of the setting, or the default value if the key doesn't exist.
        """
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """
        Updates a specific setting and saves all settings.

        Args:
            key (str): The key of the setting to update.
            value: The new value for the setting.
        """
        self.settings[key] = value
        self.save_settings()

    def get_all_settings(self):
        """Returns a copy of all current settings."""
        return self.settings.copy()


# Example Usage
if __name__ == "__main__":
    manager = SettingsManager("test_settings.json")  # Use a test file name

    print(f"Settings will be saved to/loaded from: {manager.settings_filepath}")

    print("\nInitial (or loaded) settings:")
    for k, v in manager.get_all_settings().items():
        print(f"  {k}: {v}")

    # Modify some settings
    manager.set_setting("m3u_filepath", "/path/to/my/playlist.m3u")
    manager.set_setting("volume", 90)
    manager.set_setting("hidden_categories", ["Adult", "XXX"])
    manager.set_setting("new_setting_not_in_defaults", "test_value")

    print("\nUpdated settings:")
    for k, v in manager.get_all_settings().items():
        print(f"  {k}: {v}")

    print(f"\nRetrieved 'volume': {manager.get_setting('volume')}")
    print(f"Retrieved 'non_existent_key': {manager.get_setting('non_existent_key')}")

    # Simulate reloading by creating a new instance
    print("\n--- Simulating app restart ---")
    manager2 = SettingsManager("test_settings.json")
    print("Settings after reloading:")
    for k, v in manager2.get_all_settings().items():
        print(f"  {k}: {v}")

    # Clean up the test settings file
    try:
        if os.path.exists(
            manager.settings_filepath
        ):  # Use the path from the first manager
            os.remove(manager.settings_filepath)
            print(f"\nCleaned up {manager.settings_filepath}")
            # Also remove the directory if it was created by this test and is empty
            config_dir = os.path.dirname(manager.settings_filepath)
            if (
                "PyIPTV" in config_dir
                and os.path.exists(config_dir)
                and not os.listdir(config_dir)
            ):
                os.rmdir(config_dir)
                print(f"Cleaned up directory {config_dir}")

    except Exception as e:
        print(f"Error during cleanup: {e}")
