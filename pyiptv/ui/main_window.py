import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyiptv.playlist_manager import PlaylistManager
from pyiptv.qmedia_player import QMediaVideoPlayer
from pyiptv.settings_manager import SettingsManager
from pyiptv.ui.components.enhanced_controls import EnhancedControlBar
from pyiptv.ui.components.simplified_operations import SimplifiedOperationManager
from pyiptv.ui.components.unified_status_system import StatusManager, UnifiedStatusBar
from pyiptv.ui.components.video_placeholder import VideoPlaceholder
from pyiptv.ui.components.enhanced_channel_list import EnhancedChannelList
from pyiptv.ui.components.channel_info_display import ChannelInfoDisplay, SimpleChannelInfoBar
from pyiptv.ui.components.subtitle_widget import SubtitleDisplayWidget, SubtitleControlWidget
from pyiptv.ui.playlist_manager_window import PlaylistManagerWindow
from pyiptv.ui.themes import ModernDarkTheme, ThemeManager
from pyiptv.subtitle_manager import SubtitleManager

# Get the directory containing this file
_CURRENT_DIR = Path(__file__).parent
_LOGO_PATH = str(_CURRENT_DIR / "images" / "logo.png")

# Placeholder for icons - replace with actual paths or resource system
ICON_PLAY = "play.png"
ICON_PAUSE = "pause.png"
ICON_STOP = "stop.png"
ICON_SETTINGS = "settings.png"
ICON_OPEN_FILE = "open_file.png"
ICON_APP = _LOGO_PATH  # Application icon
ICON_FULLSCREEN = "fullscreen.png"
ICON_EXIT_FULLSCREEN = "exit_fullscreen.png"


class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.main_layout = QVBoxLayout(self)

        # Theme selection

        self.theme_manager = ThemeManager(settings_manager)

        self.theme_label = QLabel("Application Theme:")
        self.theme_combo = QComboBox()

        # Populate theme options
        available_themes = self.theme_manager.get_available_themes()
        current_theme = settings_manager.get_setting("theme_mode") or "system_auto"

        for theme_id, theme_name in available_themes:
            self.theme_combo.addItem(theme_name, theme_id)
            if theme_id == current_theme:
                self.theme_combo.setCurrentIndex(self.theme_combo.count() - 1)

        self.theme_combo.setToolTip(
            "Choose application theme. 'System Default' automatically uses KDE themes on KDE systems."
        )
        self.main_layout.addWidget(self.theme_label)
        self.main_layout.addWidget(self.theme_combo)

        # Buffering
        self.buffering_label = QLabel("Network Buffering (ms):")
        self.buffering_input = QLineEdit(
            str(self.settings_manager.get_setting("buffering_ms"))
        )
        self.buffering_input.setToolTip(
            "Time in milliseconds for network caching/buffering. Higher values for unstable connections."
        )
        self.main_layout.addWidget(self.buffering_label)
        self.main_layout.addWidget(self.buffering_input)

        # Auto-play last channel
        self.auto_play_checkbox = QCheckBox(
            "Automatically play last channel on startup"
        )
        self.auto_play_checkbox.setChecked(
            self.settings_manager.get_setting("auto_play_last")
        )
        self.main_layout.addWidget(self.auto_play_checkbox)

        # Hidden Categories (placeholder - more complex UI needed for managing this)
        self.hidden_cat_label = QLabel("Hidden Categories (comma-separated):")
        hidden_cats_list = self.settings_manager.get_setting("hidden_categories")
        self.hidden_cat_input = QLineEdit(
            ", ".join(hidden_cats_list) if hidden_cats_list else ""
        )
        self.main_layout.addWidget(self.hidden_cat_label)
        self.main_layout.addWidget(self.hidden_cat_input)

        # Show environment info for KDE users
        if self.theme_manager.is_kde_environment():
            kde_info_label = QLabel(
                "🎨 KDE Environment Detected: System theme will automatically inherit KDE colors and styles."
            )
            kde_info_label.setStyleSheet(
                "color: #28a745; font-style: italic; padding: 8px;"
            )
            kde_info_label.setWordWrap(True)
            self.main_layout.addWidget(kde_info_label)

        # Save/Cancel buttons
        self.button_box = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.button_box.addStretch()
        self.button_box.addWidget(self.save_button)
        self.button_box.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.button_box)

    def accept(self):
        try:
            buffering_ms = int(self.buffering_input.text())
            if buffering_ms < 0:
                raise ValueError("Buffering must be non-negative.")
            self.settings_manager.set_setting("buffering_ms", buffering_ms)
        except ValueError:
            QMessageBox.warning(
                self, "Invalid Input", "Buffering value must be a valid integer."
            )
            return

        self.settings_manager.set_setting(
            "auto_play_last", self.auto_play_checkbox.isChecked()
        )

        hidden_cats_str = self.hidden_cat_input.text()
        hidden_cats_list = [
            cat.strip() for cat in hidden_cats_str.split(",") if cat.strip()
        ]
        self.settings_manager.set_setting("hidden_categories", hidden_cats_list)

        # Handle theme change
        selected_theme = self.theme_combo.currentData()
        current_theme = self.settings_manager.get_setting("theme_mode")

        if selected_theme != current_theme:
            self.settings_manager.set_setting("theme_mode", selected_theme)
            # Apply the new theme
            app = QApplication.instance()
            if app:
                self.theme_manager.apply_theme(app, selected_theme)

        self.settings_manager.save_settings()  # Ensure save
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, playlist_path=None):
        super().__init__()
        self.setWindowTitle("PyIPTV")
        self.settings_manager = SettingsManager()
        self.playlist_manager = PlaylistManager(self.settings_manager)
        self.all_channels_data = []
        self.categories_data = {}

        # Use provided playlist path or fall back to settings
        if playlist_path:
            self.current_m3u_path = playlist_path
            # Update settings with the new path
            self.settings_manager.set_setting("m3u_filepath", playlist_path)
        else:
            self.current_m3u_path = self.settings_manager.get_setting("m3u_filepath")

        hidden_cats = self.settings_manager.get_setting("hidden_categories")
        self.hidden_categories = set(hidden_cats if hidden_cats is not None else [])
        self.last_played_url_to_auto_play = None

        # Category filtering
        self.category_search_term = ""

        # Fullscreen state
        self.is_fullscreen = False
        self.original_parent = None
        self.original_layout = None

        self.init_ui()
        self.init_player()
        self.init_subtitles()
        self.setup_shortcuts()

        self.load_initial_m3u()
        self.restore_geometry()

        # Connect to application quit signal for cleanup
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.cleanup_on_quit)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Initialize simplified UX system
        self.init_simplified_ux_system()

        # --- Menu Bar ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        open_action = QAction(
            QIcon.fromTheme("document-open", QIcon(ICON_OPEN_FILE)),
            "&Open M3U File...",
            self,
        )
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_m3u_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        playlist_manager_action = QAction("&Playlist Manager...", self)
        playlist_manager_action.setShortcut("Ctrl+P")
        playlist_manager_action.triggered.connect(self.open_playlist_manager)
        file_menu.addAction(playlist_manager_action)

        file_menu.addSeparator()

        settings_action = QAction(
            QIcon.fromTheme("preferences-system", QIcon(ICON_SETTINGS)),
            "&Settings...",
            self,
        )
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction(QIcon.fromTheme("application-exit"), "&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- View Menu ---
        view_menu = menubar.addMenu("&View")

        subtitle_panel_action = QAction("&Subtitle Controls...", self)
        subtitle_panel_action.setShortcut("Ctrl+T")
        subtitle_panel_action.triggered.connect(self.toggle_subtitle_panel)
        view_menu.addAction(subtitle_panel_action)

        # --- Help Menu ---
        help_menu = menubar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_keyboard_shortcuts_help)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        about_action = QAction("&About PyIPTV", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # --- Main Content Area (Splitter) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # Left Pane (Categories and Channels)
        self.left_pane = QWidget()
        self.left_layout = QVBoxLayout(self.left_pane)
        self.splitter.addWidget(self.left_pane)

        # Category List with search
        self.category_label = QLabel("Categories:")

        # Category search layout
        category_search_layout = QHBoxLayout()
        self.category_search_input = QLineEdit()
        self.category_search_input.setPlaceholderText("Search categories...")
        self.category_search_input.textChanged.connect(self.on_category_search_changed)

        self.category_clear_btn = QPushButton("×")
        self.category_clear_btn.setMaximumWidth(30)
        self.category_clear_btn.clicked.connect(self.clear_category_search)
        self.category_clear_btn.setToolTip("Clear category search")

        category_search_layout.addWidget(self.category_search_input)
        category_search_layout.addWidget(self.category_clear_btn)

        self.category_list_widget = QListWidget()
        self.category_list_widget.itemClicked.connect(self.on_category_selected)

        self.left_layout.addWidget(self.category_label)
        self.left_layout.addLayout(category_search_layout)
        self.left_layout.addWidget(self.category_list_widget)

        # Channel List - Using enhanced widget with logo support
        self.channel_label = QLabel("Channels:")
        self.channel_list_widget = EnhancedChannelList()
        self.channel_list_widget.channel_selected.connect(self.on_channel_selected)
        self.channel_list_widget.channel_activated.connect(self.on_channel_activated)
        self.left_layout.addWidget(self.channel_label)
        self.left_layout.addWidget(self.channel_list_widget)

        # Right Pane (Video Player and Controls)
        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout(self.right_pane)
        self.splitter.addWidget(self.right_pane)

        # Video area with placeholder
        self.video_stack = QStackedWidget()
        self.video_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_stack.setMinimumSize(320, 240)

        # Video Widget - Native Qt video display with rendering fixes
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setMouseTracking(True)

        # Add double-click support for entering fullscreen
        self.video_widget.mouseDoubleClickEvent = self.on_video_double_click_docked

        # Basic video widget setup without problematic attributes
        pass

        # Video placeholder
        self.video_placeholder = VideoPlaceholder()

        # Add both to stack
        self.video_stack.addWidget(self.video_placeholder)  # Index 0
        self.video_stack.addWidget(self.video_widget)  # Index 1
        self.video_stack.setCurrentIndex(0)  # Start with placeholder

        self.right_layout.addWidget(self.video_stack, stretch=1)

        # Enhanced Control Bar with integrated audio track selector
        self.control_bar = EnhancedControlBar()
        self.control_bar.play_pause_clicked.connect(self.toggle_play_pause)
        self.control_bar.stop_clicked.connect(self.stop_playback)
        self.control_bar.fullscreen_clicked.connect(self.toggle_fullscreen)
        self.control_bar.volume_changed.connect(self.on_volume_changed)
        self.control_bar.seek_requested.connect(self.on_seek_requested)
        self.control_bar.audio_track_changed.connect(self.on_audio_track_changed)

        self.right_layout.addWidget(self.control_bar)

        # Set initial splitter sizes (e.g., 30% for left, 70% for right)
        self.splitter.setSizes([self.width() // 4, 3 * self.width() // 4])

        # Simple Status Bar at bottom
        self.status_bar = UnifiedStatusBar()
        self.main_layout.addWidget(self.status_bar)

        # Connect status manager
        self.status_manager.set_status_bar(self.status_bar)
        self.status_manager.show_info("Ready. Open an M3U file to begin.")

        # Application Icon
        self.setWindowIcon(QIcon(ICON_APP))

    def init_player(self):
        # Initialize QMediaPlayer with video widget
        self.player = QMediaVideoPlayer(self.video_widget)

        # Connect control bar audio track selector to player
        self.control_bar.set_media_player(self.player)

        # Connect to player error signal
        if hasattr(self.player, "playback_error_occurred"):
            self.player.playback_error_occurred.connect(self._on_playback_error)

        # Connect to metadata updates
        if hasattr(self.player, "metadata_updated"):
            self.player.metadata_updated.connect(self._on_metadata_updated)

        # Timer to update UI based on player state (e.g., play/pause icon)
        self.player_state_timer = QTimer(self)
        self.player_state_timer.timeout.connect(self.update_player_ui_state)
        self.player_state_timer.start(
            250
        )  # More frequent updates for smoother progress

        # Set initial volume from settings
        initial_volume = self.settings_manager.get_setting("volume")
        self.player.set_volume(initial_volume)
        self.control_bar.set_volume(initial_volume)

        print("QMediaPlayer initialized successfully")

    def init_subtitles(self):
        """Initialize subtitle management system."""
        # Create subtitle manager
        self.subtitle_manager = SubtitleManager(self)

        # Create subtitle display widget
        self.subtitle_display = SubtitleDisplayWidget(self)
        self.subtitle_display.hide()  # Initially hidden

        # Create subtitle control widget
        self.subtitle_control = SubtitleControlWidget(self.subtitle_manager, self)
        self.subtitle_control.hide()  # Initially hidden

        # Connect subtitle control signals
        self.subtitle_control.track_changed.connect(self._on_subtitle_track_changed)

        # Add subtitle control to the right layout (after control bar)
        # We'll add it dynamically when toggled

        # Create channel info display components
        self.channel_info_overlay = ChannelInfoDisplay(self)
        self.channel_info_bar = SimpleChannelInfoBar(self)

        # Add channel info bar to the right layout (after control bar)
        self.right_layout.addWidget(self.channel_info_bar)

        # Connect subtitle manager signals
        self.subtitle_manager.subtitle_text_updated.connect(
            self.subtitle_display.update_subtitle_text
        )

        # Connect to player position updates for subtitle timing
        if hasattr(self.player, 'position_changed'):
            self.player.position_changed.connect(self._on_position_changed_for_subtitles)

        print("Subtitle system initialized successfully")

    def init_simplified_ux_system(self):
        """Initialize the simplified UX system with just status bar."""
        # Create status manager
        self.status_manager = StatusManager()

        # Create simplified operation manager (status only)
        self.operation_manager = SimplifiedOperationManager(self.status_manager)

        # Connect operation results
        self.operation_manager.operation_result.connect(self.on_operation_result)

        # Connect to operation start/end for obvious UI busy state
        self.operation_manager.operation_started.connect(self.set_busy_state)
        self.operation_manager.operation_finished.connect(self.clear_busy_state)

        # Busy state tracking
        self.is_busy = False

    def setup_shortcuts(self):
        """Setup comprehensive keyboard shortcuts for the application."""
        # Playback controls
        self.space_shortcut = QShortcut(QKeySequence("Space"), self)
        self.space_shortcut.activated.connect(self.toggle_play_pause)

        self.play_shortcut = QShortcut(QKeySequence("P"), self)
        self.play_shortcut.activated.connect(self.toggle_play_pause)

        self.stop_shortcut = QShortcut(QKeySequence("S"), self)
        self.stop_shortcut.activated.connect(self.stop_playback)

        # Volume controls
        self.volume_up_shortcut = QShortcut(QKeySequence("Up"), self)
        self.volume_up_shortcut.activated.connect(self.volume_up)

        self.volume_down_shortcut = QShortcut(QKeySequence("Down"), self)
        self.volume_down_shortcut.activated.connect(self.volume_down)

        self.mute_shortcut = QShortcut(QKeySequence("M"), self)
        self.mute_shortcut.activated.connect(self.toggle_mute)

        # Channel navigation
        self.next_channel_shortcut = QShortcut(QKeySequence("Right"), self)
        self.next_channel_shortcut.activated.connect(self.next_channel)

        self.prev_channel_shortcut = QShortcut(QKeySequence("Left"), self)
        self.prev_channel_shortcut.activated.connect(self.previous_channel)

        self.page_down_shortcut = QShortcut(QKeySequence("Page_Down"), self)
        self.page_down_shortcut.activated.connect(self.channel_page_down)

        self.page_up_shortcut = QShortcut(QKeySequence("Page_Up"), self)
        self.page_up_shortcut.activated.connect(self.channel_page_up)

        # Fullscreen controls
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        self.fullscreen_shortcut_f = QShortcut(QKeySequence("F"), self)
        self.fullscreen_shortcut_f.activated.connect(self.toggle_fullscreen)

        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)

        # Search and navigation
        self.channel_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.channel_search_shortcut.activated.connect(self.focus_channel_search)

        self.category_search_shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        self.category_search_shortcut.activated.connect(self.focus_category_search)

        # Quick category selection (1-9)
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(str(i)), self)
            shortcut.activated.connect(
                lambda idx=i - 1: self.select_category_by_index(idx)
            )

        # Application controls
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self.refresh_playlist)

        self.settings_shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        self.settings_shortcut.activated.connect(self.open_settings_dialog)

        self.help_shortcut = QShortcut(QKeySequence("F1"), self)
        self.help_shortcut.activated.connect(self.show_keyboard_shortcuts_help)

        self.help_shortcut_ctrl = QShortcut(QKeySequence("Ctrl+H"), self)
        self.help_shortcut_ctrl.activated.connect(self.show_keyboard_shortcuts_help)

        # Subtitle controls
        self.subtitle_toggle_shortcut = QShortcut(QKeySequence("C"), self)
        self.subtitle_toggle_shortcut.activated.connect(self.toggle_subtitles)

        self.subtitle_load_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.subtitle_load_shortcut.activated.connect(self.load_subtitle_file)

        self.subtitle_detect_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.subtitle_detect_shortcut.activated.connect(self.detect_embedded_subtitles)

        self.subtitle_panel_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.subtitle_panel_shortcut.activated.connect(self.toggle_subtitle_panel)

    def _on_playback_error(self, error_message):
        """Handles playback errors signaled by the media player."""
        self.status_manager.show_error(f"Playback Error: {error_message}")
        self.control_bar.update_play_state(
            False
        )  # Update button to "Play" as playback likely stopped
        self.video_stack.setCurrentIndex(0)  # Show placeholder on error

    def load_initial_m3u(self):
        if self.current_m3u_path:
            # Check if this is a URL playlist by looking up in playlist manager
            playlist_entry = self.playlist_manager.get_playlist_by_source(
                self.current_m3u_path
            )

            if playlist_entry and playlist_entry.source_type == "url":
                # Check if we have a cached file
                if playlist_entry.has_cached_file():
                    # Use cached file directly
                    self.status_manager.show_info(
                        f"Loading cached playlist: {playlist_entry.name}"
                    )
                    self.parse_m3u_file(playlist_entry.cached_file_path)
                else:
                    # Download and cache the playlist
                    self.download_and_cache_url_playlist(playlist_entry)
            elif os.path.exists(self.current_m3u_path):
                # Handle local file playlist
                self.parse_m3u_file(self.current_m3u_path)
            else:
                self.status_manager.show_warning(
                    f"Playlist file not found: {os.path.basename(self.current_m3u_path)}"
                )
                return

            if self.settings_manager.get_setting("auto_play_last"):
                # Store the last played URL to be played once channels are loaded
                self.last_played_url_to_auto_play = self.settings_manager.get_setting(
                    "last_played_url"
                )
        else:
            self.status_manager.show_info(
                "No M3U file loaded. Use File > Open to load a playlist."
            )

    def _handle_auto_play(self):
        """Handle auto-play once channels are loaded."""
        if self.last_played_url_to_auto_play and self.all_channels_data:
            # Find the channel by URL and play it
            for channel_info in self.all_channels_data:
                if channel_info.get("url") == self.last_played_url_to_auto_play:
                    self.play_channel(channel_info)
                    # Optionally select it in the list
                    break
            # Clear the auto-play URL so it doesn't repeat
            self.last_played_url_to_auto_play = None

    def open_m3u_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open M3U File", "", "M3U Playlists (*.m3u *.m3u8);;All Files (*)"
        )
        if filepath:
            self.current_m3u_path = filepath
            self.settings_manager.set_setting("m3u_filepath", filepath)
            self.parse_m3u_file(filepath)

    def download_and_cache_url_playlist(self, playlist_entry):
        """Download URL playlist, cache it, and parse it."""
        self.status_manager.show_info(f"Downloading playlist: {playlist_entry.name}")

        # Store playlist entry for later use
        self.current_playlist_entry = playlist_entry

        # Start download operation
        self.current_download_operation_id = self.operation_manager.start_url_download(
            playlist_entry.source, self.playlist_manager
        )

    def on_url_download_success(self, temp_file_path):
        """Handle successful URL playlist download."""
        try:
            # Get the playlist entry we're working with
            playlist_entry = getattr(self, "current_playlist_entry", None)
            if not playlist_entry:
                raise ValueError("No playlist entry found for caching")

            # Read the downloaded content
            with open(temp_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Cache the playlist using the playlist manager
            if not playlist_entry.cached_file_path:
                playlist_entry.cached_file_path = (
                    self.playlist_manager._get_cached_file_path(playlist_entry.id)
                )

            # Save content to cache file
            with open(playlist_entry.cached_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Update playlist manager
            self.playlist_manager.save_playlists()

            # Parse the cached file
            self.parse_m3u_file(playlist_entry.cached_file_path)

            # Clean up the temporary file
            QTimer.singleShot(1000, lambda: self.cleanup_temp_file(temp_file_path))

        except Exception as e:
            self.status_manager.show_error(f"Failed to cache playlist: {str(e)}")

    def on_url_download_error(self, error_message):
        """Handle URL playlist download failure."""
        self.status_manager.show_error(f"Download failed: {error_message}")

    def cleanup_temp_file(self, file_path):
        """Clean up temporary downloaded file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary file {file_path}: {e}")

    def parse_m3u_file(self, filepath):
        """Parse M3U file using the new background operation system."""
        filename = os.path.basename(filepath)

        # Check file size for user info
        try:
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)
            if size_mb > 50:
                self.status_manager.show_info(
                    f"Parsing large file ({size_mb:.1f} MB) - {filename}"
                )
            else:
                self.status_manager.show_info(f"Parsing {filename}")
        except OSError:
            self.status_manager.show_info(f"Parsing {filename}")

        # Start parsing operation
        self.current_parse_operation_id = self.operation_manager.start_m3u_parsing(
            filepath, enable_cache=True
        )

    def on_operation_result(
        self, operation_type: str, success: bool, message: str, result
    ):
        """Handle operation results from the operation manager."""
        if operation_type == "m3u_parse":
            if success and result:
                self.on_m3u_parsed_success(result[0], result[1])  # channels, categories
            else:
                self.on_m3u_parsed_error(message)
        elif operation_type == "url_download":
            if success and result:
                self.on_url_download_success(result)  # temp_file_path
            else:
                self.on_url_download_error(message)

    def on_m3u_parsed_success(self, all_channels, categories):
        """Handle successful M3U parsing."""
        if not all_channels and not categories:
            self.status_manager.show_warning(
                "M3U file is empty or no valid channels were found."
            )
            return

        self.all_channels_data = all_channels
        self.categories_data = categories
        hidden_cats = self.settings_manager.get_setting("hidden_categories")
        self.hidden_categories = set(hidden_cats if hidden_cats is not None else [])

        self.populate_categories_list()
        # Select the default or first category
        default_cat_name = self.settings_manager.get_setting("default_category")
        if self.category_list_widget.count() > 0:
            default_cat_name = default_cat_name or "All Channels"
            items = self.category_list_widget.findItems(
                default_cat_name, Qt.MatchFlag.MatchExactly
            )
            if items:
                self.category_list_widget.setCurrentItem(items[0])
                self.on_category_selected(items[0])
            else:
                self.category_list_widget.setCurrentRow(0)
                self.on_category_selected(self.category_list_widget.item(0))

        # Update channel count in playlist manager if this playlist is managed
        if self.current_m3u_path:
            playlist_entry = self.playlist_manager.get_playlist_by_source(
                self.current_m3u_path
            )
            if playlist_entry:
                self.playlist_manager.update_channel_count(
                    playlist_entry.id, len(all_channels)
                )

        # Handle auto-play if enabled
        self._handle_auto_play()

    def on_m3u_parsed_error(self, error_message):
        """Handle M3U parsing error."""
        self.status_manager.show_error(f"Parsing failed: {error_message}")

    def populate_categories_list(self):
        self.category_list_widget.clear()

        # Get search term
        search_term = self.category_search_term.lower()

        # Add "All Channels" category first (always visible)
        all_channels_item = QListWidgetItem("All Channels")
        all_channels_item.setData(
            Qt.ItemDataRole.UserRole, "ALL_CHANNELS_KEY"
        )  # Special key
        self.category_list_widget.addItem(all_channels_item)

        # Filter and sort categories
        filtered_categories = []
        for cat in self.categories_data.keys():
            if cat not in self.hidden_categories:
                if not search_term or search_term in cat.lower():
                    filtered_categories.append(cat)

        sorted_categories = sorted(filtered_categories)
        for category_name in sorted_categories:
            item = QListWidgetItem(category_name)
            item.setData(
                Qt.ItemDataRole.UserRole, category_name
            )  # Store original name for lookup
            self.category_list_widget.addItem(item)

    def on_category_selected(self, item):
        if not item:
            self.channel_list_widget.set_channels([])
            return

        category_key = item.data(Qt.ItemDataRole.UserRole)
        self.current_selected_category_key = category_key  # Store for filtering
        self.update_channel_list()  # This will populate based on category

    def on_category_search_changed(self, text):
        """Handle category search text changes."""
        self.category_search_term = text.strip()
        self.populate_categories_list()

        # If there are categories visible and none selected, select first one
        if (
            self.category_list_widget.count() > 0
            and not self.category_list_widget.currentItem()
        ):
            self.category_list_widget.setCurrentRow(0)
            self.on_category_selected(self.category_list_widget.item(0))

    def clear_category_search(self):
        """Clear the category search filter."""
        self.category_search_input.clear()

    def focus_channel_search(self):
        """Focus the channel search input."""
        self.channel_list_widget.search_input.setFocus()
        self.channel_list_widget.search_input.selectAll()

    def focus_category_search(self):
        """Focus the category search input."""
        self.category_search_input.setFocus()
        self.category_search_input.selectAll()

    def update_channel_list(self):
        """Update the channel list based on current category selection."""
        category_key = getattr(
            self, "current_selected_category_key", "ALL_CHANNELS_KEY"
        )

        channels_to_display = []
        if category_key == "ALL_CHANNELS_KEY":
            channels_to_display = self.all_channels_data
        elif category_key in self.categories_data:
            channels_to_display = self.categories_data[category_key]

        # Update the virtualized channel list
        self.channel_list_widget.set_channels(channels_to_display)

    def on_channel_selected(self, channel_info):
        """Handle channel selection in the enhanced list."""
        # This is called when a channel is selected (single click)
        # Update the channel info bar
        self.channel_info_bar.update_channel_info(channel_info)

        # Show additional info in status bar
        channel_name = channel_info.get("name", "Unknown Channel")
        self.status_manager.show_info(f"Selected: {channel_name}", timeout=3000)

    def on_channel_activated(self, channel_info):
        """Handle channel activation (double-click or Enter)."""
        if channel_info:
            self.play_channel(channel_info)

    def play_channel(self, channel_info):
        url = channel_info.get("url")
        if url:
            self.status_manager.show_info(f"Playing: {channel_info.get('name', url)}")
            buffering_ms = self.settings_manager.get_setting("buffering_ms")

            # Switch to video widget and show loading state
            self.video_stack.setCurrentIndex(1)
            self.show_loading_state(True)

            buffering_ms = buffering_ms or 1500  # Default fallback
            self.player.play_media(url, buffering_ms=buffering_ms)
            self.settings_manager.set_setting("last_played_url", url)

            # Notify control bar audio track selector that new media is loaded
            self.control_bar.on_media_loaded()

            # Update UI
            self.control_bar.update_play_state(True)

            # Show channel info overlay
            if hasattr(self, 'channel_info_overlay'):
                self.channel_info_overlay.show_channel_info(channel_info, duration_ms=5000)

            # Update channel info bar
            if hasattr(self, 'channel_info_bar'):
                self.channel_info_bar.update_channel_info(channel_info)

            # Detect embedded subtitle tracks for the new media
            if hasattr(self, 'subtitle_manager'):
                try:
                    embedded_tracks = self.subtitle_manager.detect_embedded_tracks(url)
                    if embedded_tracks:
                        self.status_manager.show_info(
                            f"Detected {len(embedded_tracks)} embedded subtitle tracks",
                            timeout=3000
                        )
                except Exception as e:
                    print(f"Error detecting embedded tracks: {e}")

            # Hide loading state after a short delay
            QTimer.singleShot(2000, lambda: self.show_loading_state(False))
        else:
            self.status_manager.show_error("Channel URL not found")

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.control_bar.update_play_state(False)
            self.status_manager.show_info("Paused", timeout=2000)
        else:
            # Check if there's media loaded
            if self.player.current_url:
                self.player.play()
                self.control_bar.update_play_state(True)
                self.video_stack.setCurrentIndex(1)  # Ensure video widget is shown
                self.status_manager.show_info("Playing...", timeout=2000)
            else:
                # If no media is loaded, try to play the currently selected channel
                selected_channel = self.channel_list_widget.get_selected_channel()
                if selected_channel:
                    self.play_channel(selected_channel)
                else:
                    # Show friendly message
                    self.status_manager.show_info(
                        "Select a channel from the list to start playing"
                    )

    def stop_playback(self):
        self.player.stop()
        self.control_bar.update_play_state(False)
        self.video_stack.setCurrentIndex(0)  # Show placeholder

        # Notify control bar audio track selector that media is stopped
        self.control_bar.on_media_stopped()

        self.status_manager.show_info("Stopped", timeout=2000)

    def volume_up(self):
        """Increase volume by 5%."""
        current_volume = self.control_bar.volume_slider.value()
        new_volume = min(100, current_volume + 5)
        self.control_bar.set_volume(new_volume)
        self.on_volume_changed(new_volume)
        self.status_manager.show_info(f"Volume: {new_volume}%", timeout=1500)

    def volume_down(self):
        """Decrease volume by 5%."""
        current_volume = self.control_bar.volume_slider.value()
        new_volume = max(0, current_volume - 5)
        self.control_bar.set_volume(new_volume)
        self.on_volume_changed(new_volume)
        self.status_manager.show_info(f"Volume: {new_volume}%", timeout=1500)

    def toggle_mute(self):
        """Toggle mute state."""
        if not hasattr(self, "_pre_mute_volume"):
            self._pre_mute_volume = 80

        current_volume = self.control_bar.volume_slider.value()
        if current_volume > 0:
            # Mute
            self._pre_mute_volume = current_volume
            self.control_bar.set_volume(0)
            self.on_volume_changed(0)
            self.status_manager.show_info("Muted", timeout=1500)
        else:
            # Unmute
            self.control_bar.set_volume(self._pre_mute_volume)
            self.on_volume_changed(self._pre_mute_volume)
            self.status_manager.show_info(
                f"Volume: {self._pre_mute_volume}%", timeout=1500
            )

    def next_channel(self):
        """Select and play the next channel in the list."""
        if hasattr(self.channel_list_widget, "select_next_channel"):
            next_channel = self.channel_list_widget.select_next_channel()
            if next_channel:
                self.play_channel(next_channel)
        else:
            self.status_manager.show_info(
                "Channel navigation not available", timeout=2000
            )

    def previous_channel(self):
        """Select and play the previous channel in the list."""
        if hasattr(self.channel_list_widget, "select_previous_channel"):
            prev_channel = self.channel_list_widget.select_previous_channel()
            if prev_channel:
                self.play_channel(prev_channel)
        else:
            self.status_manager.show_info(
                "Channel navigation not available", timeout=2000
            )

    def channel_page_down(self):
        """Move down one page in the channel list."""
        if hasattr(self.channel_list_widget, "page_down"):
            self.channel_list_widget.page_down()
        else:
            self.status_manager.show_info("Page navigation not available", timeout=2000)

    def channel_page_up(self):
        """Move up one page in the channel list."""
        if hasattr(self.channel_list_widget, "page_up"):
            self.channel_list_widget.page_up()
        else:
            self.status_manager.show_info("Page navigation not available", timeout=2000)

    def select_category_by_index(self, index):
        """Select a category by its index (0-8 for categories 1-9)."""
        if index < self.category_list_widget.count():
            item = self.category_list_widget.item(index)
            if item:
                self.category_list_widget.setCurrentItem(item)
                self.on_category_selected(item)
                category_name = item.text()
                self.status_manager.show_info(
                    f"Selected category: {category_name}", timeout=2000
                )
        else:
            self.status_manager.show_info(
                f"Category {index + 1} not available", timeout=2000
            )

    def refresh_playlist(self):
        """Refresh the current playlist."""
        if self.current_m3u_path:
            self.status_manager.show_info("Refreshing playlist...", timeout=0)
            self.parse_m3u_file(self.current_m3u_path)
        else:
            self.status_manager.show_info("No playlist to refresh", timeout=2000)

    def toggle_subtitles(self):
        """Toggle subtitle display on/off."""
        if hasattr(self, 'subtitle_manager'):
            if self.subtitle_manager.is_enabled:
                self.subtitle_manager.disable_subtitles()
                self.status_manager.show_info("Subtitles disabled", timeout=1500)
            else:
                self.subtitle_manager.enable_subtitles()
                self.status_manager.show_info("Subtitles enabled", timeout=1500)
        else:
            self.status_manager.show_info("Subtitle system not available", timeout=2000)

    def load_subtitle_file(self):
        """Load a subtitle file manually."""
        if hasattr(self, 'subtitle_manager'):
            track = self.subtitle_manager.select_subtitle_file(self)
            if track:
                self.subtitle_manager.set_active_track(track.id)
                self.status_manager.show_info(f"Loaded subtitle: {track.title}", timeout=2000)
        else:
            self.status_manager.show_info("Subtitle system not available", timeout=2000)

    def detect_embedded_subtitles(self):
        """Manually detect embedded subtitle tracks in current media."""
        if hasattr(self, 'subtitle_manager') and self.player.current_url:
            try:
                embedded_tracks = self.subtitle_manager.detect_embedded_tracks(self.player.current_url)
                if embedded_tracks:
                    self.status_manager.show_info(
                        f"Found {len(embedded_tracks)} embedded subtitle tracks",
                        timeout=3000
                    )
                    # Show available tracks
                    track_names = [track.display_name for track in embedded_tracks]
                    print(f"Available embedded tracks: {', '.join(track_names)}")
                else:
                    self.status_manager.show_info("No embedded subtitle tracks found", timeout=2000)
            except Exception as e:
                self.status_manager.show_error(f"Error detecting subtitles: {str(e)}")
        else:
            self.status_manager.show_info("No media loaded or subtitle system unavailable", timeout=2000)

    def toggle_subtitle_panel(self):
        """Toggle the subtitle control panel visibility."""
        if hasattr(self, 'subtitle_control'):
            if self.subtitle_control.isVisible():
                # Hide the panel
                self.subtitle_control.hide()
                self.right_layout.removeWidget(self.subtitle_control)
                self.status_manager.show_info("Subtitle panel hidden", timeout=1500)
            else:
                # Show the panel
                self.right_layout.addWidget(self.subtitle_control)
                self.subtitle_control.show()
                self.status_manager.show_info("Subtitle panel shown", timeout=1500)

                # Auto-detect embedded tracks when panel is opened
                if self.player.current_url:
                    self.detect_embedded_subtitles()
        else:
            self.status_manager.show_info("Subtitle system not available", timeout=2000)

    def _on_subtitle_track_changed(self, track_id: str):
        """Handle subtitle track selection change."""
        if not track_id:
            # "None" selected - disable subtitles
            if hasattr(self, 'subtitle_manager'):
                self.subtitle_manager.disable_subtitles()
                self.status_manager.show_info("Subtitles disabled", timeout=1500)
            return

        if hasattr(self, 'subtitle_manager'):
            track = self.subtitle_manager.tracks.get(track_id)
            if track:
                if track.is_embedded:
                    # Handle embedded track
                    success = self.subtitle_manager.set_embedded_track(track_id)
                    if success:
                        self.status_manager.show_info(f"Activated: {track.display_name}", timeout=2000)
                        # For embedded tracks, we need to tell the media player to use this subtitle stream
                        self._activate_embedded_subtitle_in_player(track)
                    else:
                        self.status_manager.show_error("Failed to activate embedded subtitle track")
                else:
                    # Handle external track
                    success = self.subtitle_manager.set_active_track(track_id)
                    if success:
                        self.status_manager.show_info(f"Loaded: {track.display_name}", timeout=2000)
                    else:
                        self.status_manager.show_error("Failed to load subtitle track")
            else:
                self.status_manager.show_error("Subtitle track not found")
        else:
            self.status_manager.show_info("Subtitle system not available", timeout=2000)

    def _activate_embedded_subtitle_in_player(self, track):
        """Activate embedded subtitle track in the media player."""
        if hasattr(self.player, 'set_subtitle_track') and track.stream_index is not None:
            # If the player supports subtitle track selection
            try:
                self.player.set_subtitle_track(track.stream_index)
                print(f"Activated embedded subtitle track {track.stream_index} ({track.language})")
            except Exception as e:
                print(f"Error activating embedded subtitle track: {e}")
                self.status_manager.show_warning("Player doesn't support embedded subtitle switching")
        else:
            # Fallback: show info about the limitation
            self.status_manager.show_info(
                f"Selected {track.display_name} - Note: Embedded subtitle switching requires player support",
                timeout=4000
            )

    def _on_position_changed_for_subtitles(self, position_ms):
        """Handle position changes for subtitle timing."""
        if hasattr(self, 'subtitle_manager'):
            # Convert milliseconds to seconds
            position_seconds = position_ms / 1000.0
            self.subtitle_manager.update_position(position_seconds)

    def _update_subtitle_position(self):
        """Update subtitle display position relative to video widget."""
        if hasattr(self, 'subtitle_display') and self.subtitle_display.isVisible():
            # Position subtitle over the video widget
            video_geometry = self.video_widget.geometry()
            if self.is_fullscreen:
                # In fullscreen, position relative to the screen
                screen_geometry = self.screen().geometry()
                self.subtitle_display.position_subtitle(screen_geometry, "bottom")
            else:
                # In windowed mode, position relative to video widget
                global_geometry = self.video_widget.mapToGlobal(video_geometry.topLeft())
                video_geometry.moveTo(global_geometry)
                self.subtitle_display.position_subtitle(video_geometry, "bottom")

    def show_keyboard_shortcuts_help(self):
        """Show keyboard shortcuts help dialog."""
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts - PyIPTV")
        dialog.setModal(True)
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # Create text widget with shortcuts
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        shortcuts_text = """
<h2>PyIPTV Keyboard Shortcuts</h2>

<h3>🎮 Playback Controls</h3>
<table>
<tr><td><b>Space / P</b></td><td>Play/Pause</td></tr>
<tr><td><b>S</b></td><td>Stop playback</td></tr>
</table>

<h3>🔊 Volume Controls</h3>
<table>
<tr><td><b>Up Arrow</b></td><td>Volume up (+5%)</td></tr>
<tr><td><b>Down Arrow</b></td><td>Volume down (-5%)</td></tr>
<tr><td><b>M</b></td><td>Toggle mute</td></tr>
</table>

<h3>📺 Channel Navigation</h3>
<table>
<tr><td><b>Right Arrow</b></td><td>Next channel</td></tr>
<tr><td><b>Left Arrow</b></td><td>Previous channel</td></tr>
<tr><td><b>Page Down</b></td><td>Page down in channel list</td></tr>
<tr><td><b>Page Up</b></td><td>Page up in channel list</td></tr>
<tr><td><b>1-9</b></td><td>Select category by number</td></tr>
</table>

<h3>🖥️ Display Controls</h3>
<table>
<tr><td><b>F11 / F</b></td><td>Toggle fullscreen</td></tr>
<tr><td><b>Escape</b></td><td>Exit fullscreen</td></tr>
</table>

<h3>🔍 Search & Navigation</h3>
<table>
<tr><td><b>Ctrl+F</b></td><td>Focus channel search</td></tr>
<tr><td><b>Ctrl+Shift+F</b></td><td>Focus category search</td></tr>
</table>

<h3>📝 Subtitle Controls</h3>
<table>
<tr><td><b>C</b></td><td>Toggle subtitles on/off</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Load subtitle file</td></tr>
<tr><td><b>Ctrl+D</b></td><td>Detect embedded subtitles</td></tr>
<tr><td><b>Ctrl+T</b></td><td>Toggle subtitle control panel</td></tr>
</table>

<h3>📁 File & Application</h3>
<table>
<tr><td><b>Ctrl+O</b></td><td>Open M3U file</td></tr>
<tr><td><b>Ctrl+P</b></td><td>Playlist manager</td></tr>
<tr><td><b>F5</b></td><td>Refresh playlist</td></tr>
<tr><td><b>Ctrl+,</b></td><td>Settings</td></tr>
<tr><td><b>F1 / Ctrl+H</b></td><td>Show this help</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Quit application</td></tr>
</table>

<p><i>Tip: Most shortcuts work in both windowed and fullscreen modes.</i></p>
        """

        text_edit.setHtml(shortcuts_text)
        layout.addWidget(text_edit)

        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        dialog.exec()

    def show_about_dialog(self):
        """Show about dialog."""
        from PySide6.QtWidgets import QMessageBox

        about_text = """
<h2>PyIPTV</h2>
<p><b>Version:</b> 1.0.0</p>
<p><b>A Modern IPTV Player</b></p>

<p>PyIPTV is a feature-rich IPTV player built with PySide6/Qt6, designed for
streaming live television content from M3U playlists.</p>

<p><b>Features:</b></p>
<ul>
<li>📺 M3U Playlist Support</li>
<li>🎨 Modern Qt6 Interface</li>
<li>📂 Category Organization</li>
<li>🔍 Search & Filtering</li>
<li>🌓 Theme Support</li>
<li>⚡ Performance Optimized</li>
</ul>

<p><b>Author:</b> David Markey</p>
<p><b>License:</b> MIT</p>
<p><b>Website:</b> <a href="https://github.com/dmarkey/PyIPTV">https://github.com/dmarkey/PyIPTV</a></p>
        """

        QMessageBox.about(self, "About PyIPTV", about_text)

    def update_player_ui_state(self):
        """Periodically updates UI elements based on player state."""
        if self.player:
            is_playing = self.player.is_playing()

            # Update control bar
            self.control_bar.update_play_state(is_playing)

            # Update time and seek bar
            if self.player.current_url:
                position = self.player.get_current_time()
                duration = self.player.get_duration()
                self.control_bar.update_time(position, duration)

                # Show video widget if playing
                if is_playing and self.video_stack.currentIndex() != 1:
                    self.video_stack.setCurrentIndex(1)
            else:
                # No media loaded, show placeholder
                if self.video_stack.currentIndex() != 0:
                    self.video_stack.setCurrentIndex(0)

    def on_volume_changed(self, volume):
        """Handle volume changes from control bar."""
        self.player.set_volume(volume)
        self.settings_manager.set_setting("volume", volume)

    def on_seek_requested(self, position):
        """Handle seek requests from control bar."""
        if self.player.current_url:
            self.player.set_position(position)

    def on_audio_track_changed(self, track_index):
        """Handle audio track changes from the audio track selector."""
        self.status_manager.show_info(
            f"Switched to audio track {track_index + 1}", timeout=3000
        )

    def show_loading_state(self, show):
        """Show/hide loading state (can be enhanced with spinner)."""
        if show:
            self.status_manager.show_info("Loading stream...", timeout=0)
        # Could add a loading spinner overlay here

    def _on_metadata_updated(self, metadata):
        """Handle metadata updates from the player."""
        # Create metadata summary directly from the metadata
        summary = self._get_metadata_summary(metadata)
        self.control_bar.update_metadata_summary(summary)

        # Show metadata info as a temporary status update
        if summary and summary != "No stream info":
            self.status_manager.show_info(f"Stream: {summary}", timeout=5000)

    def _get_metadata_summary(self, metadata):
        """Get a summary string of key metadata."""
        if not metadata:
            return "No stream info"

        parts = []

        # Resolution
        resolution = metadata.get("resolution")
        if resolution and resolution != "N/A":
            parts.append(resolution)

        # FPS
        fps = metadata.get("fps")
        if fps and fps != "N/A" and fps != "Unknown":
            parts.append(f"{fps} fps")

        # Video codec
        video_codec = metadata.get("video_codec")
        if video_codec and video_codec != "N/A":
            parts.append(video_codec)

        return " • ".join(parts) if parts else "Stream info available"

    def open_playlist_manager(self):
        """Open the playlist manager window."""

        def on_playlist_selected(selected_playlist_path):
            # Load the selected playlist
            self.current_m3u_path = selected_playlist_path
            self.settings_manager.set_setting("m3u_filepath", selected_playlist_path)

            # Use load_initial_m3u to properly handle both file and URL playlists
            self.load_initial_m3u()

        playlist_manager_window = PlaylistManagerWindow()
        playlist_manager_window.playlist_selected.connect(on_playlist_selected)

        # Show the playlist manager window
        playlist_manager_window.show()
        playlist_manager_window.raise_()
        playlist_manager_window.activateWindow()

        # Store reference to prevent garbage collection
        self._playlist_manager_window = playlist_manager_window

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            # Settings were saved by the dialog
            self.status_manager.show_success("Settings updated")
            # Re-filter or reload data if hidden categories changed
            hidden_cats = self.settings_manager.get_setting("hidden_categories")
            self.hidden_categories = set(hidden_cats if hidden_cats is not None else [])
            self.populate_categories_list()  # Repopulate categories
            # Re-select current category or default
            if self.category_list_widget.count() > 0:
                current_cat_item = self.category_list_widget.currentItem()
                if current_cat_item:
                    self.on_category_selected(current_cat_item)
                else:
                    self.category_list_widget.setCurrentRow(0)
                    self.on_category_selected(self.category_list_widget.item(0))

    def save_geometry(self):
        import base64

        # Convert QByteArray to base64 string for JSON serialization
        geometry_bytes = self.saveGeometry().data()
        geometry_b64 = base64.b64encode(geometry_bytes).decode("utf-8")
        self.settings_manager.set_setting("window_geometry", geometry_b64)
        self.settings_manager.set_setting("splitter_sizes", self.splitter.sizes())

    def restore_geometry(self):
        import base64

        geometry_data = self.settings_manager.get_setting("window_geometry")
        if geometry_data:
            try:
                # Convert base64 string back to bytes, then to QByteArray
                from PySide6.QtCore import QByteArray

                geometry_bytes = base64.b64decode(geometry_data.encode("utf-8"))
                geometry_qbytearray = QByteArray(geometry_bytes)
                self.restoreGeometry(geometry_qbytearray)
            except Exception as e:
                print(f"Warning: Could not restore window geometry: {e}")
                # If restore fails, just use default geometry

        splitter_sizes = self.settings_manager.get_setting("splitter_sizes")
        if splitter_sizes and len(splitter_sizes) == self.splitter.count():
            self.splitter.setSizes(splitter_sizes)
        else:
            # Default splitter sizes if not saved or mismatched
            self.splitter.setSizes([self.width() // 4, 3 * self.width() // 4])

    def toggle_fullscreen(self):
        """Toggle fullscreen mode for the video widget."""
        if not self.is_fullscreen:
            self.enter_fullscreen()
        else:
            self.exit_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode."""
        if self.is_fullscreen:
            return

        # Store the original parent and remove from layout
        self.original_parent = self.video_stack.parent()
        self.right_layout.removeWidget(self.video_stack)

        # Set video stack as a standalone fullscreen window
        self.video_stack.setParent(None)
        self.video_stack.showFullScreen()
        self.video_stack.setFocus()

        # Update state
        self.is_fullscreen = True
        self.control_bar.update_fullscreen_state(True)

        # Store original event handlers and set fullscreen ones
        self.original_mouse_double_click = getattr(
            self.video_widget, "mouseDoubleClickEvent", None
        )
        self.original_key_press = getattr(self.video_widget, "keyPressEvent", None)

        # Set fullscreen event handlers
        self.video_widget.mouseDoubleClickEvent = self.on_video_double_click
        self.video_widget.keyPressEvent = self.on_video_key_press

        # Enable focus and key events for the video widget
        self.video_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        print("Entered fullscreen mode")

    def exit_fullscreen(self):
        """Exit fullscreen mode."""
        if not self.is_fullscreen:
            return

        # Remove the video stack from fullscreen
        self.video_stack.showNormal()

        # Put it back in the original layout
        if self.original_parent:
            # Cast to QWidget since we know it's a QWidget
            from PySide6.QtWidgets import QWidget

            if isinstance(self.original_parent, QWidget):
                self.video_stack.setParent(self.original_parent)
        self.right_layout.insertWidget(0, self.video_stack, stretch=1)

        # Restore original event handlers
        if (
            hasattr(self, "original_mouse_double_click")
            and self.original_mouse_double_click
        ):
            self.video_widget.mouseDoubleClickEvent = self.original_mouse_double_click
        else:
            # Restore docked mode double-click handler
            self.video_widget.mouseDoubleClickEvent = self.on_video_double_click_docked

        if hasattr(self, "original_key_press") and self.original_key_press:
            self.video_widget.keyPressEvent = self.original_key_press
        else:
            # Reset to default behavior
            if hasattr(self.video_widget, "keyPressEvent"):
                delattr(self.video_widget, "keyPressEvent")

        # Update state
        self.is_fullscreen = False
        self.control_bar.update_fullscreen_state(False)

        print("Exited fullscreen mode")

    def on_video_double_click_docked(self, event):
        """Handle double-click on video widget in docked mode."""
        _ = event  # Unused parameter
        if not self.is_fullscreen:
            self.enter_fullscreen()

    def on_video_double_click(self, event):
        """Handle double-click on video widget in fullscreen mode."""
        _ = event  # Unused parameter
        self.exit_fullscreen()

    def on_video_key_press(self, event):
        """Handle key press events on video widget in fullscreen mode."""
        if event.key() == Qt.Key.Key_Escape or event.key() == Qt.Key.Key_F11:
            self.exit_fullscreen()
        elif event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            # Allow spacebar to toggle play/pause in fullscreen
            self.toggle_play_pause()
        else:
            # Let the original handler deal with other keys if it exists
            if hasattr(self, "original_key_press") and self.original_key_press:
                self.original_key_press(event)

    def cleanup_on_quit(self):
        """Cleanup resources when application is quitting."""
        print("Cleaning up resources...")

        # Exit fullscreen if active
        if self.is_fullscreen:
            self.exit_fullscreen()

        # Stop and cleanup player
        if hasattr(self, "player") and self.player:
            self.player.stop()
            self.player.release_player()

        # Cancel all active operations
        if hasattr(self, "operation_manager"):
            self.operation_manager.cancel_all_operations()

        # Save settings
        self.save_geometry()

    def closeEvent(self, event):
        """Handle window close event."""
        self.cleanup_on_quit()
        super().closeEvent(event)

    def set_busy_state(self):
        """Set obvious visual feedback that the application is busy."""
        self.is_busy = True

        # Change cursor to waiting
        self.setCursor(Qt.CursorShape.WaitCursor)

        # Dim the main content area
        if not hasattr(self, "busy_effect"):
            self.busy_effect = QGraphicsOpacityEffect()
            self.splitter.setGraphicsEffect(self.busy_effect)
        self.busy_effect.setOpacity(0.6)  # 60% opacity = dimmed

        # Make status bar more prominent with busy styling
        self.status_bar.setStyleSheet(
            """
            UnifiedStatusBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ffeaa7, stop: 1 #fdcb6e);
                border: 2px solid #e17055;
                border-radius: 4px;
                font-weight: bold;
            }
        """
        )

        # Update window title to show busy state
        original_title = self.windowTitle()
        if not original_title.endswith(" - Working..."):
            self.setWindowTitle(f"{original_title} - Working...")

    def clear_busy_state(self):
        """Clear busy visual feedback."""
        self.is_busy = False

        # Restore normal cursor
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # Restore normal opacity
        if hasattr(self, "busy_effect"):
            self.busy_effect.setOpacity(1.0)  # Full opacity = normal

        # Restore normal status bar styling
        self.status_bar.setStyleSheet("")

        # Explicitly repaint the lists to ensure they redraw correctly after opacity change
        self.category_list_widget.repaint()
        self.channel_list_widget.repaint()

        # Restore normal window title
        title = self.windowTitle()
        if title.endswith(" - Working..."):
            self.setWindowTitle(title.replace(" - Working...", ""))

    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)

        # Update channel info overlay position
        if hasattr(self, 'channel_info_overlay'):
            self.channel_info_overlay.update_position()


if __name__ == "__main__":
    # This is for testing the UI standalone.
    # In the actual application, pyiptv.main will run this.

    app = QApplication(sys.argv)

    # Enable high DPI support
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Apply modern theme
    ModernDarkTheme.apply(app)

    main_win = MainWindow()
    main_win.setGeometry(100, 100, 1200, 800)  # Larger default size
    main_win.show()
    sys.exit(app.exec())
