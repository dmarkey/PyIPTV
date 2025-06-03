import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QListWidget, QLabel, QSplitter,
                             QFileDialog, QMenuBar, QFrame, QSizePolicy,
                             QMessageBox, QProgressDialog, QDialog, QCheckBox,
                             QScrollArea, QSpacerItem, QListWidgetItem, QStyledItemDelegate,
                             QStyle, QApplication, QHeaderView, QStyleFactory,
                             QStackedWidget, QGraphicsOpacityEffect)
from PySide6.QtGui import QPixmap, QIcon, QStandardItemModel, QStandardItem, QPainter, QFontMetrics, QPalette, QColor, QBrush, QKeySequence, QAction, QShortcut
from PySide6.QtCore import Qt, QSize, QUrl, QThread, Signal, QTimer, QSettings, QPropertyAnimation, QEasingCurve

from ..m3u_parser import M3UParser
from ..qmedia_player import QMediaVideoPlayer
from ..settings_manager import SettingsManager
from .components.virtualized_channel_list import VirtualizedChannelList
from .components.enhanced_progress_dialog import EnhancedProgressDialog
from .components.video_placeholder import VideoPlaceholder
from .components.enhanced_controls import EnhancedControlBar
from PySide6.QtMultimediaWidgets import QVideoWidget
import os

# Placeholder for icons - replace with actual paths or resource system
ICON_PLAY = "play.png"
ICON_PAUSE = "pause.png"
ICON_STOP = "stop.png"
ICON_SETTINGS = "settings.png"
ICON_OPEN_FILE = "open_file.png"
ICON_APP = "app_icon.png" # Application icon
ICON_FULLSCREEN = "fullscreen.png"
ICON_EXIT_FULLSCREEN = "exit_fullscreen.png"

# --- Custom Delegate for Icon Display in QListWidget ---
class ChannelListItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_cache = {} # Cache for loaded QPixmaps
        self.default_icon_size = QSize(32, 32) # Default size for icons

    def paint(self, painter, option, index):
        super().paint(painter, option, index) # Draw default item painting first

        icon_url = index.data(Qt.ItemDataRole.UserRole + 1) # tvg-logo URL
        if icon_url:
            icon = self.get_icon(icon_url)
            if icon:
                # Calculate position to draw the icon (e.g., to the left of text)
                # This is a simplified positioning. More complex layout might be needed.
                icon_rect = option.rect
                icon_rect.setWidth(self.default_icon_size.width())
                icon_rect.setHeight(self.default_icon_size.height())
                # Center icon vertically if item is taller
                if option.rect.height() > self.default_icon_size.height():
                    icon_rect.moveTop(option.rect.top() + (option.rect.height() - self.default_icon_size.height()) // 2)

                # Adjust text position to make space for the icon
                # This part is tricky with QStyledItemDelegate as it doesn't directly expose text layout.
                # A more robust way might involve a custom QListWidgetItem or a QTreeView.
                # For now, we'll draw the icon and assume the default text rendering makes some space.
                # A common approach is to add padding to the text or use a layout within the item.

                # painter.drawPixmap(icon_rect.topLeft(), icon)
                # Let's try to draw it within the decoration area if possible
                # This might conflict if the style already draws something there.
                decoration_align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                decoration_rect = QApplication.style().subElementRect(QStyle.SubElement.SE_ItemViewItemDecoration, option, None)
                painter.drawPixmap(decoration_rect, icon)


    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        # icon_url = index.data(Qt.UserRole + 1)
        # if icon_url:
            # Increase hint slightly if there's an icon, to ensure space
            # size.setWidth(size.width() + self.default_icon_size.width() + 5) # 5px padding
        size.setHeight(max(size.height(), self.default_icon_size.height() + 4)) # Ensure min height for icon
        return size

    def get_icon(self, url):
        if url in self.icon_cache:
            return self.icon_cache[url]
        # This is a placeholder for actual icon fetching and loading
        # In a real app, this would involve network requests and error handling
        try:
            # For now, let's assume local files for simplicity or a very basic fetch
            # In a real app, use QNetworkAccessManager for async download
            # For this example, we'll just return a placeholder if it's a URL
            if url.startswith("http"):
                # Placeholder: In a real app, download and cache this image
                # For now, we'll skip network loading in the delegate for simplicity
                # and assume icons are pre-loaded or handled differently.
                # Returning None means no icon will be drawn by this custom part.
                # print(f"Delegate: Would fetch {url}")
                return None # Or a default placeholder icon
            else: # Assume local path
                pixmap = QPixmap(url)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(self.default_icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.icon_cache[url] = pixmap
                    return pixmap
        except Exception as e:
            print(f"Error loading icon {url}: {e}")
        return None


# --- Worker thread for M3U parsing ---
class M3UParseThread(QThread):
    finished = Signal(list, dict) # (all_channels, categories)
    progress = Signal(int, int) # (percentage, channels_processed)
    status_update = Signal(str) # Status message
    error = Signal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.parser = None
        self._should_cancel = False

    def cancel_parsing(self):
        """Cancel the parsing operation."""
        self._should_cancel = True
        if self.parser:
            self.parser.cancel_parsing()

    def run(self):
        try:
            self.status_update.emit("Initializing parser...")
            
            # Create parser with progress callback
            def progress_callback(progress_percent, channels_processed):
                if not self._should_cancel:
                    self.progress.emit(progress_percent, channels_processed)
                    
            self.parser = M3UParser(progress_callback=progress_callback)
            
            # Set up Qt event processing to keep UI responsive
            def process_events():
                if hasattr(self, 'parent') and self.parent():
                    from PySide6.QtWidgets import QApplication
                    QApplication.processEvents()
                    
            self.parser.set_process_events_callback(process_events)
            
            self.status_update.emit("Reading file...")
            
            # Check if file exists
            if not os.path.exists(self.filepath):
                self.error.emit(f"File not found: {self.filepath}")
                return
                
            # Get file size for user info
            file_size = os.path.getsize(self.filepath)
            size_mb = file_size / (1024 * 1024)
            self.status_update.emit(f"Parsing {size_mb:.1f} MB file...")
            
            all_channels, categories = self.parser.parse_m3u_from_file(self.filepath)
            
            if self._should_cancel:
                self.status_update.emit("Parsing cancelled")
                return
                
            if not all_channels and not categories:
                self.status_update.emit("File appears to be empty or malformed")
                
            self.status_update.emit("Parsing completed successfully")
            self.finished.emit(all_channels, categories)
            
        except Exception as e:
            if not self._should_cancel:
                self.error.emit(f"Error parsing M3U file: {str(e)}")


class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.main_layout = QVBoxLayout(self)

        # Buffering
        self.buffering_label = QLabel("Network Buffering (ms):")
        self.buffering_input = QLineEdit(str(self.settings_manager.get_setting("buffering_ms")))
        self.buffering_input.setToolTip("Time in milliseconds for network caching/buffering. Higher values for unstable connections.")
        self.main_layout.addWidget(self.buffering_label)
        self.main_layout.addWidget(self.buffering_input)

        # Auto-play last channel
        self.auto_play_checkbox = QCheckBox("Automatically play last channel on startup")
        self.auto_play_checkbox.setChecked(self.settings_manager.get_setting("auto_play_last"))
        self.main_layout.addWidget(self.auto_play_checkbox)

        # Hidden Categories (placeholder - more complex UI needed for managing this)
        self.hidden_cat_label = QLabel("Hidden Categories (comma-separated):")
        hidden_cats_list = self.settings_manager.get_setting("hidden_categories")
        self.hidden_cat_input = QLineEdit(", ".join(hidden_cats_list) if hidden_cats_list else "")
        self.main_layout.addWidget(self.hidden_cat_label)
        self.main_layout.addWidget(self.hidden_cat_input)


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
            QMessageBox.warning(self, "Invalid Input", "Buffering value must be a valid integer.")
            return

        self.settings_manager.set_setting("auto_play_last", self.auto_play_checkbox.isChecked())

        hidden_cats_str = self.hidden_cat_input.text()
        hidden_cats_list = [cat.strip() for cat in hidden_cats_str.split(',') if cat.strip()]
        self.settings_manager.set_setting("hidden_categories", hidden_cats_list)

        self.settings_manager.save_settings() # Ensure save
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python IPTV Player")
        self.settings_manager = SettingsManager()
        self.all_channels_data = []
        self.categories_data = {}
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

        # --- Menu Bar ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')

        open_action = QAction(QIcon.fromTheme("document-open", QIcon(ICON_OPEN_FILE)), '&Open M3U File...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_m3u_file_dialog)
        file_menu.addAction(open_action)

        settings_action = QAction(QIcon.fromTheme("preferences-system", QIcon(ICON_SETTINGS)), '&Settings...', self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)

        exit_action = QAction(QIcon.fromTheme("application-exit"), '&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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

        # Channel List - Using virtualized widget for performance
        self.channel_label = QLabel("Channels:")
        self.channel_list_widget = VirtualizedChannelList()
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
        self.video_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_stack.setMinimumSize(320, 240)
        
        # Video Widget - Native Qt video display with rendering fixes
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setMouseTracking(True)
        
        # Basic video widget setup without problematic attributes
        pass
        
        # Video placeholder
        self.video_placeholder = VideoPlaceholder()
        
        # Add both to stack
        self.video_stack.addWidget(self.video_placeholder)  # Index 0
        self.video_stack.addWidget(self.video_widget)       # Index 1
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

        # Status Bar (optional)
        self.statusBar().showMessage("Ready. Open an M3U file to begin.")

        # Application Icon
        self.setWindowIcon(QIcon(ICON_APP))


    def init_player(self):
        # Initialize QMediaPlayer with video widget
        self.player = QMediaVideoPlayer(self.video_widget)
        
        # Connect control bar audio track selector to player
        self.control_bar.set_media_player(self.player)
        
        # Connect to player error signal
        if hasattr(self.player, 'playback_error_occurred'):
            self.player.playback_error_occurred.connect(self._on_playback_error)
        
        # Connect to metadata updates
        if hasattr(self.player, 'metadata_updated'):
            self.player.metadata_updated.connect(self._on_metadata_updated)
        
        # Timer to update UI based on player state (e.g., play/pause icon)
        self.player_state_timer = QTimer(self)
        self.player_state_timer.timeout.connect(self.update_player_ui_state)
        self.player_state_timer.start(250)  # More frequent updates for smoother progress
        
        # Set initial volume from settings
        initial_volume = self.settings_manager.get_setting("volume")
        self.player.set_volume(initial_volume)
        self.control_bar.set_volume(initial_volume)
        
        print("QMediaPlayer initialized successfully")

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for the application."""
        # F11 or F for fullscreen toggle
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        self.fullscreen_shortcut_f = QShortcut(QKeySequence("F"), self)
        self.fullscreen_shortcut_f.activated.connect(self.toggle_fullscreen)
        
        # ESC to exit fullscreen
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)
        
        # Ctrl+F to focus channel search
        self.channel_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.channel_search_shortcut.activated.connect(self.focus_channel_search)
        
        # Ctrl+Shift+F to focus category search
        self.category_search_shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        self.category_search_shortcut.activated.connect(self.focus_category_search)
        
        # Space bar for play/pause
        self.space_shortcut = QShortcut(QKeySequence("Space"), self)
        self.space_shortcut.activated.connect(self.toggle_play_pause)
        

    def _on_playback_error(self, error_message):
        """Handles playback errors signaled by the media player."""
        self.statusBar().showMessage(f"Playback Error: {error_message}")
        self.control_bar.update_play_state(False)  # Update button to "Play" as playback likely stopped
        self.video_stack.setCurrentIndex(0)  # Show placeholder on error

    def load_initial_m3u(self):
        if self.current_m3u_path and os.path.exists(self.current_m3u_path):
            self.parse_m3u_file(self.current_m3u_path)
            if self.settings_manager.get_setting("auto_play_last"):
                # Store the last played URL to be played once channels are loaded
                self.last_played_url_to_auto_play = self.settings_manager.get_setting("last_played_url")
        else:
            self.statusBar().showMessage("No M3U file loaded. Use File > Open to load a playlist.")

    def _handle_auto_play(self):
        """Handle auto-play once channels are loaded."""
        if self.last_played_url_to_auto_play and self.all_channels_data:
            # Find the channel by URL and play it
            for channel_info in self.all_channels_data:
                if channel_info.get('url') == self.last_played_url_to_auto_play:
                    self.play_channel(channel_info)
                    # Optionally select it in the list
                    break
            # Clear the auto-play URL so it doesn't repeat
            self.last_played_url_to_auto_play = None


    def open_m3u_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open M3U File", "", "M3U Playlists (*.m3u *.m3u8);;All Files (*)")
        if filepath:
            self.current_m3u_path = filepath
            self.settings_manager.set_setting("m3u_filepath", filepath)
            self.parse_m3u_file(filepath)

    def parse_m3u_file(self, filepath):
        filename = os.path.basename(filepath)
        
        # Check file size and show appropriate message
        try:
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)
            if size_mb > 50:  # Large file warning
                self.statusBar().showMessage(f"Parsing large file ({size_mb:.1f} MB) - {filename}...")
            else:
                self.statusBar().showMessage(f"Parsing {filename}...")
        except OSError:
            self.statusBar().showMessage(f"Parsing {filename}...")
        
        # Store start time for completion message
        import time
        self.parse_start_time = time.time()
        
        # Enhanced progress dialog with better configuration for large files
        self.progress_dialog = EnhancedProgressDialog("Parsing M3U file...", "Cancel", self)
        self.progress_dialog.setWindowFlags(self.progress_dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.progress_dialog.setMinimumWidth(450)  # Wider for better stats display
        self.progress_dialog.show()
        
        # Force immediate display and process events
        QApplication.processEvents()

        self.parse_thread = M3UParseThread(filepath)
        self.parse_thread.finished.connect(self.on_m3u_parsed)
        self.parse_thread.error.connect(self.on_m3u_parse_error)
        self.parse_thread.progress.connect(self.on_parse_progress)
        self.parse_thread.status_update.connect(self.on_parse_status_update)
        self.progress_dialog.canceled.connect(self.cancel_parsing)
        self.parse_thread.start()

    def on_m3u_parsed(self, all_channels, categories):
        # Show completion message before closing dialog
        if self.progress_dialog:
            import time
            elapsed = time.time() - getattr(self, 'parse_start_time', time.time())
            self.progress_dialog.show_completion(len(all_channels), elapsed)

        if not all_channels and not categories:
            self.statusBar().showMessage("M3U file is empty or could not be parsed correctly.")
            QMessageBox.information(self, "Parsing Info", "The M3U file is empty or no valid channels were found.")
            return

        self.all_channels_data = all_channels
        self.categories_data = categories
        hidden_cats = self.settings_manager.get_setting("hidden_categories")
        self.hidden_categories = set(hidden_cats if hidden_cats is not None else [])  # Refresh hidden

        self.populate_categories_list()
        # Select the default or first category
        default_cat_name = self.settings_manager.get_setting("default_category")
        if self.category_list_widget.count() > 0:
            default_cat_name = default_cat_name or "All Channels"
            items = self.category_list_widget.findItems(default_cat_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.category_list_widget.setCurrentItem(items[0])
                self.on_category_selected(items[0])
            else:
                self.category_list_widget.setCurrentRow(0)
                self.on_category_selected(self.category_list_widget.item(0))

        filename = os.path.basename(self.current_m3u_path) if self.current_m3u_path else "Unknown"
        self.statusBar().showMessage(f"Loaded {len(all_channels):,} channels from {filename}.")
        
        # Handle auto-play if enabled
        self._handle_auto_play()

    def on_parse_progress(self, progress_percent, channels_processed):
        """Handle parsing progress updates."""
        if self.progress_dialog:
            self.progress_dialog.update_progress(progress_percent, channels_processed)

    def on_parse_status_update(self, status):
        """Handle parsing status updates."""
        if self.progress_dialog:
            self.progress_dialog.update_progress(self.progress_dialog.value(), status_text=status)

    def cancel_parsing(self):
        """Cancel the current parsing operation."""
        if hasattr(self, 'parse_thread') and self.parse_thread.isRunning():
            self.parse_thread.cancel_parsing()
            self.statusBar().showMessage("Parsing cancelled.")

    def on_m3u_parse_error(self, error_message):
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self, "M3U Parse Error", error_message)
        self.statusBar().showMessage(f"Error parsing M3U: {error_message}")

    def populate_categories_list(self):
        self.category_list_widget.clear()
        
        # Get search term
        search_term = self.category_search_term.lower()
        
        # Add "All Channels" category first (always visible)
        all_channels_item = QListWidgetItem("All Channels")
        all_channels_item.setData(Qt.ItemDataRole.UserRole, "ALL_CHANNELS_KEY") # Special key
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
            item.setData(Qt.ItemDataRole.UserRole, category_name) # Store original name for lookup
            self.category_list_widget.addItem(item)

    def on_category_selected(self, item):
        if not item:
            self.channel_list_widget.set_channels([])
            return

        category_key = item.data(Qt.ItemDataRole.UserRole)
        self.current_selected_category_key = category_key # Store for filtering
        self.update_channel_list() # This will populate based on category

    def on_category_search_changed(self, text):
        """Handle category search text changes."""
        self.category_search_term = text.strip()
        self.populate_categories_list()
        
        # If there are categories visible and none selected, select first one
        if self.category_list_widget.count() > 0 and not self.category_list_widget.currentItem():
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
        category_key = getattr(self, 'current_selected_category_key', "ALL_CHANNELS_KEY")

        channels_to_display = []
        if category_key == "ALL_CHANNELS_KEY":
            channels_to_display = self.all_channels_data
        elif category_key in self.categories_data:
            channels_to_display = self.categories_data[category_key]

        # Update the virtualized channel list
        self.channel_list_widget.set_channels(channels_to_display)

    def on_channel_selected(self, channel_info):
        """Handle channel selection in the virtualized list."""
        # This is called when a channel is selected (single click)
        # We can show additional info in status bar or elsewhere
        channel_name = channel_info.get('name', 'Unknown Channel')
        self.statusBar().showMessage(f"Selected: {channel_name}")

    def on_channel_activated(self, channel_info):
        """Handle channel activation (double-click or Enter)."""
        if channel_info:
            self.play_channel(channel_info)

    def play_channel(self, channel_info):
        url = channel_info.get('url')
        if url:
            self.statusBar().showMessage(f"Playing: {channel_info.get('name', url)}")
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
            
            # Hide loading state after a short delay
            QTimer.singleShot(2000, lambda: self.show_loading_state(False))
        else:
            self.statusBar().showMessage("Error: Channel URL not found.")

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.control_bar.update_play_state(False)
            self.statusBar().showMessage("Paused.")
        else:
            # Check if there's media loaded
            if self.player.current_url:
                self.player.play()
                self.control_bar.update_play_state(True)
                self.video_stack.setCurrentIndex(1)  # Ensure video widget is shown
                self.statusBar().showMessage("Playing...")
            else:
                # If no media is loaded, try to play the currently selected channel
                selected_channel = self.channel_list_widget.get_selected_channel()
                if selected_channel:
                    self.play_channel(selected_channel)
                else:
                    # Show friendly message
                    self.statusBar().showMessage("Select a channel from the list to start playing.")


    def stop_playback(self):
        self.player.stop()
        self.control_bar.update_play_state(False)
        self.video_stack.setCurrentIndex(0)  # Show placeholder
        
        # Notify control bar audio track selector that media is stopped
        self.control_bar.on_media_stopped()
        
        self.statusBar().showMessage("Stopped.")

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
        self.statusBar().showMessage(f"Switched to audio track {track_index + 1}")
            
    def show_loading_state(self, show):
        """Show/hide loading state (can be enhanced with spinner)."""
        if show:
            self.statusBar().showMessage("Loading stream...")
        # Could add a loading spinner overlay here
        
    def _on_metadata_updated(self, metadata):
        """Handle metadata updates from the player."""
        # Create metadata summary directly from the metadata
        summary = self._get_metadata_summary(metadata)
        self.control_bar.update_metadata_summary(summary)
        
        # Update status bar with key info
        if summary and summary != "No stream info":
            current_status = self.statusBar().currentMessage()
            if "Playing:" in current_status:
                # Append metadata to current status
                base_status = current_status.split(" •")[0]  # Remove any existing metadata
                self.statusBar().showMessage(f"{base_status} • {summary}")
    
    def _get_metadata_summary(self, metadata):
        """Get a summary string of key metadata."""
        if not metadata:
            return "No stream info"
            
        parts = []
        
        # Resolution
        resolution = metadata.get('resolution')
        if resolution and resolution != "N/A":
            parts.append(resolution)
            
        # FPS
        fps = metadata.get('fps')
        if fps and fps != "N/A" and fps != "Unknown":
            parts.append(f"{fps} fps")
            
        # Video codec
        video_codec = metadata.get('video_codec')
        if video_codec and video_codec != "N/A":
            parts.append(video_codec)
            
        return " • ".join(parts) if parts else "Stream info available"


    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            # Settings were saved by the dialog
            self.statusBar().showMessage("Settings updated.")
            # Re-filter or reload data if hidden categories changed
            hidden_cats = self.settings_manager.get_setting("hidden_categories")
            self.hidden_categories = set(hidden_cats if hidden_cats is not None else [])
            self.populate_categories_list() # Repopulate categories
            # Re-select current category or default
            if self.category_list_widget.count() > 0:
                current_cat_item = self.category_list_widget.currentItem()
                if current_cat_item:
                    self.on_category_selected(current_cat_item)
                else:
                    self.category_list_widget.setCurrentRow(0)
                    self.on_category_selected(self.category_list_widget.item(0))

    def save_geometry(self):
        self.settings_manager.set_setting("window_geometry", self.saveGeometry().data())
        self.settings_manager.set_setting("splitter_sizes", self.splitter.sizes())


    def restore_geometry(self):
        geometry_data = self.settings_manager.get_setting("window_geometry")
        if geometry_data:
            self.restoreGeometry(geometry_data)

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
        
        # Store original event handlers and set new ones
        self.original_mouse_double_click = getattr(self.video_widget, 'mouseDoubleClickEvent', None)
        self.original_key_press = getattr(self.video_widget, 'keyPressEvent', None)
        
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
        if hasattr(self, 'original_mouse_double_click') and self.original_mouse_double_click:
            self.video_widget.mouseDoubleClickEvent = self.original_mouse_double_click
        else:
            # Reset to default behavior
            delattr(self.video_widget, 'mouseDoubleClickEvent')
            
        if hasattr(self, 'original_key_press') and self.original_key_press:
            self.video_widget.keyPressEvent = self.original_key_press
        else:
            # Reset to default behavior
            delattr(self.video_widget, 'keyPressEvent')
        
        # Update state
        self.is_fullscreen = False
        self.control_bar.update_fullscreen_state(False)
        
        print("Exited fullscreen mode")

    def on_video_double_click(self, event):
        """Handle double-click on video widget in fullscreen mode."""
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
            if hasattr(self, 'original_key_press') and self.original_key_press:
                self.original_key_press(event)

    def cleanup_on_quit(self):
        """Cleanup resources when application is quitting."""
        print("Cleaning up resources...")
        
        # Exit fullscreen if active
        if self.is_fullscreen:
            self.exit_fullscreen()
            
        # Stop and cleanup player
        if hasattr(self, 'player') and self.player:
            self.player.stop()
            self.player.release_player()
            
        # Cancel any running parsing operations
        if hasattr(self, 'parse_thread') and self.parse_thread.isRunning():
            self.parse_thread.cancel_parsing()
            self.parse_thread.wait(1000)  # Wait up to 1 second
            
        # Close progress dialog if open
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            
        # Save settings
        self.save_geometry()

    def closeEvent(self, event):
        """Handle window close event."""
        self.cleanup_on_quit()
        super().closeEvent(event)



if __name__ == '__main__':
    # This is for testing the UI standalone.
    # In the actual application, iptv_player.main will run this.
    from .themes import ModernDarkTheme
    
    app = QApplication(sys.argv)
    
    # Enable high DPI support
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    # Apply modern theme
    ModernDarkTheme.apply(app)

    main_win = MainWindow()
    main_win.setGeometry(100, 100, 1200, 800)  # Larger default size
    main_win.show()
    sys.exit(app.exec())