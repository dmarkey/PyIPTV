import os
import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QFrame,
    QListWidgetItem,
    QStyledItemDelegate,
    QApplication,
    QMenu,
    QGroupBox,
    QFormLayout,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QInputDialog,
    QStyle,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import QRect, QByteArray
from PySide6.QtGui import QIcon
from urllib.parse import urlparse

from pyptv.playlist_manager import PlaylistManager, PlaylistEntry
from pyptv.settings_manager import SettingsManager
from pyptv.ui.url_download_worker import URLDownloadWorker


class PlaylistListItemDelegate(QStyledItemDelegate):
    """Custom delegate for playlist list items with enhanced display."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        """Custom paint method for playlist items with proper spacing."""
        playlist = index.data(Qt.ItemDataRole.UserRole)
        if not playlist:
            super().paint(painter, option, index)
            return

        # Draw everything manually to prevent overlapping
        painter.save()

        # Add the missing QRect import at method level

        # Handle selection highlighting
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            title_color = option.palette.color(QPalette.ColorRole.HighlightedText)
            info_color = option.palette.color(QPalette.ColorRole.HighlightedText)
        else:
            painter.fillRect(option.rect, option.palette.base())
            title_color = option.palette.color(QPalette.ColorRole.Text)
            info_color = option.palette.color(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text
            )

        # Set up fonts with clear size differences
        normal_font = painter.font()
        title_font = QFont(normal_font)
        title_font.setWeight(QFont.Weight.Bold)
        title_font.setPointSize(normal_font.pointSize() + 1)

        info_font = QFont(normal_font)
        info_font.setPointSize(max(8, normal_font.pointSize() - 2))

        # Calculate layout with generous spacing
        margin = 15
        content_rect = option.rect.adjusted(margin, margin, -margin, -margin)

        # Draw title in top area
        painter.setFont(title_font)
        painter.setPen(title_color)

        title_text = playlist.name
        if playlist.source_type == "url":
            title_text = f"🌐 {title_text}"
        else:
            title_text = f"📁 {title_text}"

        # Title takes top 30px of content area
        title_rect = QRect(
            content_rect.left(), content_rect.top(), content_rect.width(), 30
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title_text,
        )

        # Draw info in bottom area with significant spacing
        painter.setFont(info_font)
        painter.setPen(info_color)

        info_parts = []
        if playlist.channel_count > 0:
            info_parts.append(f"{playlist.channel_count:,} channels")

        if playlist.last_opened:
            try:
                last_opened = datetime.fromisoformat(
                    playlist.last_opened.replace("Z", "+00:00")
                )
                time_diff = datetime.now() - last_opened.replace(tzinfo=None)
                if time_diff.days > 0:
                    info_parts.append(f"opened {time_diff.days} days ago")
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    info_parts.append(f"opened {hours}h ago")
                else:
                    info_parts.append("recently opened")
            except (ValueError, TypeError, OSError):
                pass

        if not playlist.is_available():
            info_parts.append("⚠ Not available")
        elif playlist.source_type == "file" and playlist.needs_refresh():
            file_mtime = playlist.get_file_modification_time()
            if file_mtime:
                info_parts.append(
                    f"🔄 File modified {file_mtime.strftime('%m/%d %H:%M')}"
                )
            else:
                info_parts.append("🔄 Needs refresh")

        if info_parts:
            info_text = " • ".join(info_parts)
            # Info starts 40px from top, well below title
            info_rect = QRect(
                content_rect.left(), content_rect.top() + 40, content_rect.width(), 25
            )
            painter.drawText(
                info_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                info_text,
            )

        painter.restore()

    def sizeHint(self, option, index):
        """Return size hint for playlist items."""
        size = super().sizeHint(option, index)
        size.setHeight(
            max(size.height(), 80)
        )  # Increased height for two distinct lines
        return size


class AddPlaylistDialog(QDialog):
    """Dialog for adding new playlists."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Playlist")
        self.setModal(True)
        self.setMinimumSize(500, 300)

        self.init_ui()
        self.source_type_changed()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Playlist name
        name_group = QGroupBox("Playlist Details")
        name_layout = QFormLayout(name_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter playlist name...")
        name_layout.addRow("Name:", self.name_input)

        layout.addWidget(name_group)

        # Source type selection
        source_group = QGroupBox("Source Type")
        source_layout = QVBoxLayout(source_group)

        self.source_type_group = QButtonGroup()
        self.file_radio = QRadioButton("Local File")
        self.url_radio = QRadioButton("URL")
        self.file_radio.setChecked(True)

        self.source_type_group.addButton(self.file_radio, 0)
        self.source_type_group.addButton(self.url_radio, 1)

        source_layout.addWidget(self.file_radio)
        source_layout.addWidget(self.url_radio)

        layout.addWidget(source_group)

        # Source input
        input_group = QGroupBox("Source")
        input_layout = QVBoxLayout(input_group)

        # File input
        self.file_widget = QWidget()
        file_layout = QHBoxLayout(self.file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)

        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Select M3U file...")
        self.file_input.setReadOnly(True)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.browse_button)

        # URL input
        self.url_widget = QWidget()
        url_layout = QVBoxLayout(self.url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter M3U URL (http:// or https://)")

        self.test_url_button = QPushButton("Test URL")
        self.test_url_button.clicked.connect(self.test_url)

        url_input_layout = QHBoxLayout()
        url_input_layout.addWidget(self.url_input)
        url_input_layout.addWidget(self.test_url_button)

        url_layout.addLayout(url_input_layout)

        # Add URL validation info
        url_info = QLabel("Note: URL playlists will be downloaded and cached locally")
        url_info.setStyleSheet("color: gray; font-size: 10px;")
        url_layout.addWidget(url_info)

        input_layout.addWidget(self.file_widget)
        input_layout.addWidget(self.url_widget)

        layout.addWidget(input_group)

        # Auto-naming option
        self.auto_name_check = QCheckBox("Auto-generate name from source")
        self.auto_name_check.setChecked(True)
        self.auto_name_check.toggled.connect(self.auto_name_toggled)
        layout.addWidget(self.auto_name_check)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Add Playlist")

        layout.addWidget(button_box)

        # Connect signals
        self.source_type_group.buttonToggled.connect(self.source_type_changed)
        self.file_input.textChanged.connect(self.update_auto_name)
        self.url_input.textChanged.connect(self.update_auto_name)

    def source_type_changed(self):
        """Handle source type radio button changes."""
        is_file = self.file_radio.isChecked()
        self.file_widget.setVisible(is_file)
        self.url_widget.setVisible(not is_file)
        self.update_auto_name()

    def browse_file(self):
        """Open file browser for M3U files."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select M3U Playlist",
            "",
            "M3U Playlists (*.m3u *.m3u8);;All Files (*)",
        )
        if file_path:
            self.file_input.setText(file_path)

    def test_url(self):
        """Test if the URL is accessible."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL first.")
            return

        try:
            import requests

            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                QMessageBox.information(self, "URL Test", "URL is accessible!")
            else:
                QMessageBox.warning(
                    self,
                    "URL Test",
                    f"URL returned status code: {response.status_code}",
                )
        except Exception as e:
            QMessageBox.critical(
                self, "URL Test Failed", f"Cannot access URL:\n{str(e)}"
            )

    def auto_name_toggled(self, checked):
        """Handle auto-name checkbox toggle."""
        self.name_input.setEnabled(not checked)
        if checked:
            self.update_auto_name()
        else:
            self.name_input.clear()

    def update_auto_name(self):
        """Auto-generate playlist name from source."""
        if not self.auto_name_check.isChecked():
            return

        if self.file_radio.isChecked():
            file_path = self.file_input.text().strip()
            if file_path:
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.name_input.setText(name)
        else:
            url = self.url_input.text().strip()
            if url:
                try:

                    parsed = urlparse(url)
                    if parsed.path:
                        name = os.path.splitext(os.path.basename(parsed.path))[0]
                        if not name:
                            name = parsed.netloc or "URL Playlist"
                    else:
                        name = parsed.netloc or "URL Playlist"
                    self.name_input.setText(name)
                except (ValueError, TypeError, AttributeError):
                    self.name_input.setText("URL Playlist")

    def get_playlist_data(self):
        """Get the playlist data from the dialog."""
        name = self.name_input.text().strip()
        if not name:
            raise ValueError("Playlist name is required")

        if self.file_radio.isChecked():
            source = self.file_input.text().strip()
            if not source:
                raise ValueError("Please select a file")
            if not os.path.exists(source):
                raise ValueError("Selected file does not exist")
            source_type = "file"
        else:
            source = self.url_input.text().strip()
            if not source:
                raise ValueError("Please enter a URL")
            if not source.startswith(("http://", "https://")):
                raise ValueError("URL must start with http:// or https://")
            source_type = "url"

        return {"name": name, "source": source, "source_type": source_type}

    def accept(self):
        """Override accept to handle URL downloads."""
        try:
            data = self.get_playlist_data()

            if data["source_type"] == "url":
                # Show download dialog for URL playlists
                self.download_url_playlist(data)
            else:
                # For file playlists, proceed normally
                super().accept()

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))

    def download_url_playlist(self, playlist_data):
        """Download URL playlist and add it."""
        # Create progress dialog
        progress_dialog = QProgressDialog(
            "Downloading playlist...", "Cancel", 0, 100, self
        )
        progress_dialog.setWindowFlags(
            progress_dialog.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.show()

        # Ensure dialog is visible and on top
        progress_dialog.raise_()
        progress_dialog.activateWindow()

        # Create download worker
        # Create a temporary playlist manager instance for downloading

        temp_settings = SettingsManager()
        temp_playlist_manager = PlaylistManager(temp_settings)

        self.download_worker = URLDownloadWorker(
            playlist_data["source"], temp_playlist_manager
        )

        # Connect signals
        self.download_worker.progress_updated.connect(progress_dialog.setValue)
        self.download_worker.status_updated.connect(progress_dialog.setLabelText)
        self.download_worker.download_completed.connect(
            lambda path: self.on_download_completed(path, playlist_data)
        )
        self.download_worker.download_failed.connect(
            lambda error: self.on_download_failed(error, progress_dialog)
        )

        # Connect cancel
        progress_dialog.canceled.connect(self.download_worker.cancel_download)

        # Start download
        self.download_worker.start()

    def on_download_completed(self, temp_file_path, playlist_data):
        """Handle successful download."""
        try:
            # Update playlist data with the temporary file path
            self.temp_downloaded_file = temp_file_path
            playlist_data["source"] = temp_file_path
            playlist_data["source_type"] = "file"  # Treat as file now

            # Store the original URL for reference
            self.original_url = self.url_input.text().strip()

            QMessageBox.information(
                self, "Download Complete", "Playlist downloaded successfully!"
            )

            # Accept the dialog
            super().accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to process downloaded playlist:\n{str(e)}"
            )

    def on_download_failed(self, error, progress_dialog):
        """Handle download failure."""
        progress_dialog.close()
        QMessageBox.critical(
            self, "Download Failed", f"Failed to download playlist:\n{error}"
        )


class PlaylistManagerWindow(QMainWindow):
    """Main playlist manager window."""

    # Signals
    playlist_selected = Signal(str)  # Emits playlist source path/URL

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyPTV Playlist Manager")
        self.setMinimumSize(800, 600)

        # Set window icon using robust path resolution

        current_dir = Path(__file__).parent
        logo_path = str(current_dir / "images" / "logo.png")
        self.setWindowIcon(QIcon(logo_path))

        # Initialize managers
        self.settings_manager = SettingsManager()
        self.playlist_manager = PlaylistManager(self.settings_manager)

        # UI setup
        self.init_ui()
        self.setup_connections()
        self.load_playlists()

        # Load window geometry
        self.restore_geometry()

    def init_ui(self):
        """Initialize the UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with proper margins
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Header
        header_label = QLabel("PyPTV Playlist Manager")
        header_font = header_label.font()
        header_font.setPointSize(header_font.pointSize() + 6)
        header_font.setWeight(QFont.Weight.Bold)
        header_label.setFont(header_font)
        main_layout.addWidget(header_label)

        # Main content - just the playlist panel (no splitter needed)
        playlist_panel = self.create_playlist_panel()
        main_layout.addWidget(playlist_panel)

        # Bottom panel - Main actions
        bottom_panel = self.create_bottom_panel()
        main_layout.addWidget(bottom_panel)

        # Status bar
        self.statusBar().showMessage(
            "Ready. Double-click or right-click playlists to access options."
        )

    def create_playlist_panel(self):
        """Create the playlist list panel."""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # Playlist list header
        header_layout = QHBoxLayout()
        playlists_label = QLabel("Playlists")
        label_font = playlists_label.font()
        label_font.setPointSize(label_font.pointSize() + 2)
        label_font.setWeight(QFont.Weight.Bold)
        playlists_label.setFont(label_font)

        # Add playlist button
        add_button = QPushButton("+ Add Playlist")
        add_button.clicked.connect(self.add_playlist)

        header_layout.addWidget(playlists_label)
        header_layout.addStretch()
        header_layout.addWidget(add_button)

        layout.addLayout(header_layout)

        # Playlist list
        self.playlist_list = QListWidget()
        self.playlist_list.setItemDelegate(PlaylistListItemDelegate())
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(
            self.show_playlist_context_menu
        )
        self.playlist_list.itemSelectionChanged.connect(
            self.on_playlist_selection_changed
        )
        self.playlist_list.itemDoubleClicked.connect(self.launch_selected_playlist)

        layout.addWidget(self.playlist_list)

        return panel

    def create_bottom_panel(self):
        """Create the bottom action panel."""
        panel = QFrame()
        layout = QHBoxLayout(panel)

        # Import/Export buttons
        import_button = QPushButton("Import Playlists...")
        import_button.clicked.connect(self.import_playlists)

        export_button = QPushButton("Export Playlists...")
        export_button.clicked.connect(self.export_playlists)

        layout.addWidget(import_button)
        layout.addWidget(export_button)
        layout.addStretch()

        # Exit button
        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self.close)

        layout.addWidget(exit_button)

        return panel

    def setup_connections(self):
        """Set up signal connections."""
        self.playlist_manager.playlist_added.connect(self.on_playlist_added)
        self.playlist_manager.playlist_removed.connect(self.on_playlist_removed)
        self.playlist_manager.playlist_updated.connect(self.on_playlist_updated)

    def load_playlists(self):
        """Load and display playlists."""
        self.playlist_list.clear()

        playlists = self.playlist_manager.get_all_playlists()
        auto_refreshed_count = 0

        for playlist in playlists:
            # Check if file-based playlists need auto-refresh
            if playlist.source_type == "file" and playlist.needs_refresh():
                if self.playlist_manager.auto_refresh_file_playlist(playlist):
                    auto_refreshed_count += 1

            self.add_playlist_to_list(playlist)

        if playlists:
            self.playlist_list.setCurrentRow(0)

        status_msg = f"Loaded {len(playlists)} playlists"
        if auto_refreshed_count > 0:
            status_msg += f" ({auto_refreshed_count} auto-refreshed)"
        self.statusBar().showMessage(status_msg)

    def add_playlist_to_list(self, playlist: PlaylistEntry):
        """Add a playlist to the list widget."""
        item = QListWidgetItem()
        item.setText(playlist.name)
        item.setData(Qt.ItemDataRole.UserRole, playlist)

        # Set icon based on source type
        if playlist.source_type == "url":
            item.setText(f"🌐 {playlist.name}")
        else:
            item.setText(f"📁 {playlist.name}")

        # Disable if not available
        if not playlist.is_available():
            item.setForeground(QColor("gray"))

        self.playlist_list.addItem(item)

    def on_playlist_selection_changed(self):
        """Handle playlist selection changes."""
        # No longer needed since we removed the info panel
        # All functionality is now in the context menu
        pass

    def add_playlist(self):
        """Show add playlist dialog."""
        dialog = AddPlaylistDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_playlist_data()

                # Handle URL playlists that were downloaded
                if hasattr(dialog, "temp_downloaded_file") and hasattr(
                    dialog, "original_url"
                ):
                    # For URL playlists, add the playlist with the original URL
                    playlist = self.playlist_manager.add_playlist(
                        data["name"],
                        dialog.original_url,  # Store original URL as source
                        "url",  # Keep as URL type
                    )

                    # Read the downloaded content and cache it
                    try:
                        with open(
                            dialog.temp_downloaded_file, "r", encoding="utf-8"
                        ) as f:
                            content = f.read()

                        # Save to cache file
                        if playlist.cached_file_path:
                            with open(
                                playlist.cached_file_path, "w", encoding="utf-8"
                            ) as f:
                                f.write(content)
                            self.playlist_manager.save_playlists()

                        # Clean up temporary file
                        os.remove(dialog.temp_downloaded_file)
                    except Exception as e:
                        print(f"Warning: Could not cache playlist: {e}")
                        try:
                            os.remove(dialog.temp_downloaded_file)
                        except OSError:
                            pass
                else:
                    # Regular file playlist
                    playlist = self.playlist_manager.add_playlist(
                        data["name"], data["source"], data["source_type"]
                    )

                self.statusBar().showMessage(f"Added playlist: {playlist.name}")
            except Exception as e:
                QMessageBox.critical(self, "Error Adding Playlist", str(e))

    def rename_selected_playlist(self):
        """Rename the selected playlist."""
        current_item = self.playlist_list.currentItem()
        if not current_item:
            return

        playlist = current_item.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Playlist",
            "Enter new name:",
            QLineEdit.EchoMode.Normal,
            playlist.name,
        )

        if ok and new_name.strip():
            try:
                self.playlist_manager.rename_playlist(playlist.id, new_name.strip())
                self.statusBar().showMessage(f"Renamed playlist to: {new_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error Renaming Playlist", str(e))

    def delete_selected_playlist(self):
        """Delete the selected playlist."""
        current_item = self.playlist_list.currentItem()
        if not current_item:
            return

        playlist = current_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Are you sure you want to delete '{playlist.name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.playlist_manager.remove_playlist(playlist.id):
                self.statusBar().showMessage(f"Deleted playlist: {playlist.name}")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete playlist")

    def refresh_url_playlist(self):
        """Refresh a URL-based playlist by re-downloading it."""
        current_item = self.playlist_list.currentItem()
        if not current_item:
            return

        playlist = current_item.data(Qt.ItemDataRole.UserRole)

        if playlist.source_type != "url":
            QMessageBox.warning(
                self,
                "Invalid Operation",
                "This action is only available for URL-based playlists.",
            )
            return

        # Confirm the refresh operation
        reply = QMessageBox.question(
            self,
            "Refresh Playlist",
            f"This will re-download the playlist '{playlist.name}' from its URL and update the cached version.\n\n"
            f"URL: {playlist.source}\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create progress dialog
        progress_dialog = QProgressDialog(
            "Refreshing playlist...", "Cancel", 0, 100, self
        )
        progress_dialog.setWindowFlags(
            progress_dialog.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.show()

        # Ensure dialog is visible and on top
        progress_dialog.raise_()
        progress_dialog.activateWindow()

        # Create download worker
        self.refresh_worker = URLDownloadWorker(playlist.source, self.playlist_manager)

        # Connect signals
        self.refresh_worker.progress_updated.connect(progress_dialog.setValue)
        self.refresh_worker.status_updated.connect(progress_dialog.setLabelText)
        self.refresh_worker.download_completed.connect(
            lambda path: self.on_refresh_completed(path, playlist, progress_dialog)
        )
        self.refresh_worker.download_failed.connect(
            lambda error: self.on_refresh_failed(error, progress_dialog)
        )

        # Connect cancel
        progress_dialog.canceled.connect(self.refresh_worker.cancel_download)

        # Start download
        self.refresh_worker.start()

    def on_refresh_completed(self, temp_file_path, playlist, progress_dialog):
        """Handle successful refresh download."""
        try:
            progress_dialog.setLabelText("Updating cache...")
            progress_dialog.setValue(95)

            # Read the downloaded content
            with open(temp_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Update the cache with the new content
            if playlist.cached_file_path:
                # Remove old cache file if it exists
                if os.path.exists(playlist.cached_file_path):
                    os.remove(playlist.cached_file_path)

                # Save the new content to cache
                with open(playlist.cached_file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Update playlist metadata
                playlist.update_last_opened()
                self.playlist_manager.save_playlists()

                # Emit update signal
                self.playlist_manager.playlist_updated.emit(playlist)

            # Clean up temporary file
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

            progress_dialog.setValue(100)
            progress_dialog.close()

            QMessageBox.information(
                self,
                "Refresh Complete",
                f"Playlist '{playlist.name}' has been successfully refreshed and cached.",
            )

            self.statusBar().showMessage(f"Refreshed playlist: {playlist.name}")

            # Update the list item to reflect any changes
            self.load_playlists()

        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(
                self, "Refresh Error", f"Failed to update cached playlist:\n{str(e)}"
            )

            # Clean up temporary file
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception:
                pass

    def on_refresh_failed(self, error, progress_dialog):
        """Handle refresh failure."""
        progress_dialog.close()
        QMessageBox.critical(
            self, "Refresh Failed", f"Failed to refresh playlist:\n{error}"
        )

    def launch_selected_playlist(self):
        """Launch the PyPTV player with the selected playlist."""
        current_item = self.playlist_list.currentItem()
        if not current_item:
            return

        playlist = current_item.data(Qt.ItemDataRole.UserRole)

        if not playlist.is_available():
            QMessageBox.warning(
                self,
                "Playlist Not Available",
                f"The playlist '{playlist.name}' is not currently available.\n\n"
                "Please check the source path/URL and try again.",
            )
            return

        # Check if file-based playlist needs auto-refresh
        if playlist.source_type == "file" and playlist.needs_refresh():
            file_mtime = playlist.get_file_modification_time()
            if file_mtime:
                self.statusBar().showMessage(
                    f"Auto-refreshing '{playlist.name}' - file was modified on {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                self.statusBar().showMessage(
                    f"Auto-refreshing '{playlist.name}' - file has been modified"
                )

        # Mark as opened (this will trigger auto-refresh if needed)
        self.playlist_manager.mark_playlist_opened(playlist.id)

        # Emit signal with playlist source
        self.playlist_selected.emit(playlist.source)

        # Close the manager window
        self.close()

    def show_playlist_context_menu(self, position):
        """Show context menu for playlist list."""
        item = self.playlist_list.itemAt(position)
        if not item:
            return

        playlist = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        launch_action = menu.addAction("Launch Player")
        launch_action.triggered.connect(self.launch_selected_playlist)

        menu.addSeparator()

        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(self.rename_selected_playlist)

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected_playlist)

        menu.addSeparator()

        # Add refresh playlist action for URL playlists only
        if playlist.source_type == "url":
            refresh_playlist_action = menu.addAction("Refresh Playlist")
            refresh_playlist_action.triggered.connect(self.refresh_url_playlist)

        menu.exec(self.playlist_list.mapToGlobal(position))

    def import_playlists(self):
        """Import playlists from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Playlists", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                imported, skipped = self.playlist_manager.import_playlists(file_path)
                QMessageBox.information(
                    self,
                    "Import Complete",
                    f"Successfully imported {imported} playlists.\n"
                    f"{skipped} playlists were skipped (duplicates or errors).",
                )
                if imported > 0:
                    self.load_playlists()
            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error", f"Failed to import playlists:\n{str(e)}"
                )

    def export_playlists(self):
        """Export playlists to a file."""
        if not self.playlist_manager.playlists:
            QMessageBox.information(self, "No Playlists", "No playlists to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Playlists",
            "pyptv_playlists_export.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            try:
                if self.playlist_manager.export_playlists(file_path):
                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Successfully exported {len(self.playlist_manager.playlists)} playlists to:\n{file_path}",
                    )
                else:
                    QMessageBox.critical(
                        self, "Export Error", "Failed to export playlists."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error", f"Failed to export playlists:\n{str(e)}"
                )

    def on_playlist_added(self, playlist: PlaylistEntry):
        """Handle playlist added signal."""
        self.add_playlist_to_list(playlist)

    def on_playlist_removed(self, playlist_id: str):
        """Handle playlist removed signal."""
        # Find and remove the item from the list
        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            playlist = item.data(Qt.ItemDataRole.UserRole)
            if playlist.id == playlist_id:
                self.playlist_list.takeItem(i)
                break

    def on_playlist_updated(self, playlist: PlaylistEntry):
        """Handle playlist updated signal."""
        # Find and update the item in the list
        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            item_playlist = item.data(Qt.ItemDataRole.UserRole)
            if item_playlist.id == playlist.id:
                item.setData(Qt.ItemDataRole.UserRole, playlist)
                item.setText(playlist.name)
                if playlist.source_type == "url":
                    item.setText(f"🌐 {playlist.name}")
                else:
                    item.setText(f"📁 {playlist.name}")
                break

        # Update status bar instead of showing info panel
        self.statusBar().showMessage(f"Updated playlist: {playlist.name}")

    def save_geometry(self):
        """Save window geometry."""
        self.settings_manager.set_setting(
            "playlist_manager_geometry", self.saveGeometry().data()
        )

    def restore_geometry(self):
        """Restore window geometry."""
        geometry_data = self.settings_manager.get_setting("playlist_manager_geometry")
        if geometry_data:
            try:

                # Convert bytes data back to QByteArray for restoration
                if isinstance(geometry_data, bytes):
                    geometry_qbytearray = QByteArray(geometry_data)
                else:
                    # Handle case where it might be stored as string (legacy)
                    geometry_qbytearray = QByteArray(geometry_data)
                self.restoreGeometry(geometry_qbytearray)
            except Exception as e:
                print(
                    f"Warning: Could not restore playlist manager window geometry: {e}"
                )

    def closeEvent(self, event):
        """Handle window close event."""
        self.save_geometry()
        super().closeEvent(event)


if __name__ == "__main__":
    # Test the playlist manager window
    app = QApplication(sys.argv)

    window = PlaylistManagerWindow()
    window.show()

    sys.exit(app.exec())
