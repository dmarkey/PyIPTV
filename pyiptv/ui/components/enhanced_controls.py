from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class EnhancedControlBar(QWidget):
    """
    Enhanced control bar with volume control, seek bar, and improved styling.
    """

    # Signals
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    fullscreen_clicked = Signal()
    volume_changed = Signal(int)
    seek_requested = Signal(float)  # 0.0 to 1.0
    audio_track_changed = Signal(int)  # Track index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.duration = 0
        self.position = 0
        self._is_seeking = False

        # Media player reference
        self.media_player = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the control bar UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 10)
        main_layout.setSpacing(8)

        # Seek bar (top)
        self.seek_frame = QFrame()
        seek_layout = QVBoxLayout(self.seek_frame)
        seek_layout.setContentsMargins(0, 0, 0, 0)
        seek_layout.setSpacing(2)

        # Time labels
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.duration_label = QLabel("00:00")

        # Add metadata summary label
        self.metadata_summary_label = QLabel("")
        # Use a slightly smaller font but inherit colors from theme
        font = self.metadata_summary_label.font()
        font.setPointSize(max(8, font.pointSize() - 2))
        self.metadata_summary_label.setFont(font)
        self.metadata_summary_label.hide()  # Hidden by default

        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.metadata_summary_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)

        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(1000)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(self._on_seek_move)
        self.seek_slider.valueChanged.connect(self._on_value_changed)

        seek_layout.addLayout(time_layout)
        seek_layout.addWidget(self.seek_slider)
        main_layout.addWidget(self.seek_frame)

        # Main controls (bottom)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Playback controls
        self.play_pause_btn = QPushButton()
        self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_pause_btn.setToolTip("Play/Pause (Space)")
        self.play_pause_btn.clicked.connect(self.play_pause_clicked)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self.stop_clicked)

        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.stop_btn)

        # Spacer
        controls_layout.addStretch()

        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)

        self.volume_icon = QLabel("🔊")
        self.volume_icon.setToolTip("Volume")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        self.volume_label = QLabel("80%")
        self.volume_label.setMinimumWidth(35)

        volume_layout.addWidget(self.volume_icon)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)

        controls_layout.addLayout(volume_layout)

        # Audio track selector (compact)
        audio_layout = QHBoxLayout()
        audio_layout.setSpacing(5)

        self.audio_icon = QLabel("🎵")
        self.audio_icon.setToolTip("Audio Track")

        self.audio_track_combo = QComboBox()
        self.audio_track_combo.setMaximumWidth(120)
        self.audio_track_combo.setToolTip("Select audio track")
        self.audio_track_combo.addItem("No tracks")
        self.audio_track_combo.setEnabled(False)
        self.audio_track_combo.currentIndexChanged.connect(self._on_audio_track_changed)

        audio_layout.addWidget(self.audio_icon)
        audio_layout.addWidget(self.audio_track_combo)

        controls_layout.addLayout(audio_layout)

        # Fullscreen button
        self.fullscreen_btn = QPushButton()
        self.fullscreen_btn.setIcon(QIcon.fromTheme("view-fullscreen"))
        self.fullscreen_btn.setToolTip("Fullscreen (F11)")
        self.fullscreen_btn.clicked.connect(self.fullscreen_clicked)

        controls_layout.addWidget(self.fullscreen_btn)
        main_layout.addLayout(controls_layout)

        # Removed custom styling - now inherits from system theme
        # Only add minimal styling if absolutely necessary for functionality
        pass

    def setup_animations(self):
        """Setup control animations."""
        # Removed custom animations - using system theme
        pass

    def update_play_state(self, is_playing):
        """Update the play/pause button state."""
        self.is_playing = is_playing
        if is_playing:
            self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
            self.play_pause_btn.setToolTip("Pause (Space)")
        else:
            self.play_pause_btn.setIcon(QIcon.fromTheme("media-playback-start"))
            self.play_pause_btn.setToolTip("Play (Space)")

    def update_fullscreen_state(self, is_fullscreen):
        """Update the fullscreen button state."""
        if is_fullscreen:
            self.fullscreen_btn.setIcon(QIcon.fromTheme("view-restore"))
            self.fullscreen_btn.setToolTip("Exit Fullscreen (F11 or ESC)")
        else:
            self.fullscreen_btn.setIcon(QIcon.fromTheme("view-fullscreen"))
            self.fullscreen_btn.setToolTip("Fullscreen (F11)")

    def update_time(self, position, duration):
        """Update time display and seek bar."""
        self.position = position
        self.duration = duration

        # Update time labels
        self.current_time_label.setText(self._format_time(position))
        self.duration_label.setText(self._format_time(duration))

        # Update seek bar (only if not currently seeking)
        if not self._is_seeking and duration > 0:
            progress = int((position / duration) * 1000)
            self.seek_slider.setValue(progress)

    def set_volume(self, volume):
        """Set the volume slider value."""
        self.volume_slider.setValue(volume)
        self._update_volume_display(volume)

    def _format_time(self, ms):
        """Format time in milliseconds to HH:MM:SS or MM:SS."""
        if ms <= 0:
            return "00:00"

        # Convert to int to ensure we're working with integers
        total_seconds = int(ms // 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _on_volume_changed(self, value):
        """Handle volume slider changes."""
        self._update_volume_display(value)
        self.volume_changed.emit(value)

    def _update_volume_display(self, volume):
        """Update volume icon and label."""
        self.volume_label.setText(f"{volume}%")

        # Update volume icon based on level
        if volume == 0:
            self.volume_icon.setText("🔇")
        elif volume < 30:
            self.volume_icon.setText("🔈")
        elif volume < 70:
            self.volume_icon.setText("🔉")
        else:
            self.volume_icon.setText("🔊")

    def _on_seek_start(self):
        """Handle start of seeking."""
        self._is_seeking = True

    def _on_seek_end(self):
        """Handle end of seeking."""
        self._is_seeking = False
        position = self.seek_slider.value() / 1000.0  # Convert to 0.0-1.0
        self.seek_requested.emit(position)

    def _on_seek_move(self, value):
        """Handle seek slider movement."""
        if self.duration > 0:
            position = (value / 1000.0) * self.duration
            self.current_time_label.setText(self._format_time(position))

    def _on_value_changed(self, value):
        """Handle slider value changes (including direct clicks on track)."""
        # Only process value changes from user interaction
        # Skip if we're currently seeking (dragging) - that's handled by _on_seek_move
        # Skip if we're programmatically updating during playback
        if self._is_seeking:
            return

        # Check if this is a user-initiated change by comparing with current position
        if self.duration > 0:
            current_progress = int((self.position / self.duration) * 1000)
            # If the value differs significantly from current position, it's likely a user click
            if abs(value - current_progress) > 5:  # Allow small tolerance for rounding
                # This is a direct click/jump - seek immediately
                position = value / 1000.0  # Convert to 0.0-1.0
                self.seek_requested.emit(position)

                # Update time display immediately
                time_position = (value / 1000.0) * self.duration
                self.current_time_label.setText(self._format_time(time_position))

    def fade_in(self):
        """Fade in the controls."""
        # Removed custom fade animation - using system theme
        pass

    def fade_out(self):
        """Fade out the controls."""
        # Removed custom fade animation - using system theme
        pass

    def update_metadata_summary(self, summary_text):
        """Update the metadata summary display in controls."""
        if summary_text and summary_text != "No stream info":
            self.metadata_summary_label.setText(f" • {summary_text}")
            self.metadata_summary_label.show()
        else:
            self.metadata_summary_label.hide()

    def set_media_player(self, media_player):
        """Set the media player instance."""
        self.media_player = media_player

    def _on_audio_track_changed(self, index):
        """Handle audio track selection change."""
        if not self.media_player or not self.audio_track_combo.isEnabled():
            return

        track_index = self.audio_track_combo.itemData(index)
        if track_index is not None:
            success = self.media_player.set_audio_track(track_index)
            if success:
                self.audio_track_changed.emit(track_index)

    def refresh_audio_tracks(self):
        """Refresh the list of available audio tracks."""
        if not self.media_player:
            self.audio_track_combo.clear()
            self.audio_track_combo.addItem("No tracks")
            self.audio_track_combo.setEnabled(False)
            return

        try:
            # Clear existing items
            self.audio_track_combo.blockSignals(True)
            self.audio_track_combo.clear()

            # Get available audio tracks
            audio_tracks = self.media_player.get_audio_tracks()

            if not audio_tracks:
                self.audio_track_combo.addItem("No tracks")
                self.audio_track_combo.setEnabled(False)
            else:
                self.audio_track_combo.setEnabled(True)

                # Add tracks to combo box with raw information
                for track in audio_tracks:
                    # Build track display text from raw values
                    track_text = f"Track {track['index'] + 1}"

                    # Add description if available
                    if track["description"]:
                        track_text += f": {track['description']}"
                    elif track["title"]:
                        track_text += f": {track['title']}"

                    # Add language if available
                    if track["language"]:
                        track_text += f" ({track['language']})"

                    self.audio_track_combo.addItem(track_text, track["index"])

                # Try to select current track
                current_track = self.media_player.get_current_audio_track()
                if current_track >= 0:
                    for i in range(self.audio_track_combo.count()):
                        if self.audio_track_combo.itemData(i) == current_track:
                            self.audio_track_combo.setCurrentIndex(i)
                            break

        except Exception as e:
            print(f"Error refreshing audio tracks: {e}")
            self.audio_track_combo.clear()
            self.audio_track_combo.addItem("Error")
            self.audio_track_combo.setEnabled(False)
        finally:
            self.audio_track_combo.blockSignals(False)

    def on_media_loaded(self):
        """Call this when new media is loaded."""
        # Immediately reset the dropdown
        self.audio_track_combo.clear()
        self.audio_track_combo.addItem("Loading tracks...")
        self.audio_track_combo.setEnabled(False)

        # Delay refresh to allow media to fully load
        QTimer.singleShot(2000, self.refresh_audio_tracks)

    def on_media_stopped(self):
        """Call this when media is stopped."""
        self.audio_track_combo.clear()
        self.audio_track_combo.addItem("No tracks")
        self.audio_track_combo.setEnabled(False)
