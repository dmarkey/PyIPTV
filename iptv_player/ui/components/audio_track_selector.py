from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                     QComboBox, QPushButton, QGroupBox)
from PySide6.QtCore import Signal, QTimer

class AudioTrackSelector(QWidget):
    """Widget for selecting audio tracks."""
    
    audio_track_changed = Signal(int)  # Emitted when audio track is changed
    
    def __init__(self, media_player=None):
        super().__init__()
        self.media_player = media_player
        self.setup_ui()
        
        # Timer to refresh track list when media changes
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_tracks)
        self.refresh_timer.setSingleShot(True)
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Group box for audio tracks
        group_box = QGroupBox("Audio Tracks")
        group_layout = QVBoxLayout(group_box)
        
        # Track selection
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Track:"))
        
        self.track_combo = QComboBox()
        self.track_combo.setMinimumWidth(200)
        self.track_combo.currentIndexChanged.connect(self.on_track_changed)
        track_layout.addWidget(self.track_combo)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_tracks)
        track_layout.addWidget(self.refresh_button)
        
        group_layout.addLayout(track_layout)
        
        # Status label
        self.status_label = QLabel("No media loaded")
        self.status_label.setStyleSheet("color: #888;")
        group_layout.addWidget(self.status_label)
        
        layout.addWidget(group_box)
        
    def set_media_player(self, media_player):
        """Set the media player instance."""
        self.media_player = media_player
        self.refresh_tracks()
        
    def refresh_tracks(self):
        """Refresh the list of available audio tracks."""
        if not self.media_player:
            self.track_combo.clear()
            self.status_label.setText("No media player available")
            return
            
        try:
            # Clear existing items
            self.track_combo.blockSignals(True)
            self.track_combo.clear()
            
            # Get available audio tracks
            audio_tracks = self.media_player.get_audio_tracks()
            
            if not audio_tracks:
                self.track_combo.addItem("No audio tracks detected")
                self.status_label.setText("No audio tracks available")
                self.track_combo.setEnabled(False)
            else:
                self.track_combo.setEnabled(True)
                
                # Add tracks to combo box
                for track in audio_tracks:
                    track_text = f"Track {track['index'] + 1}: {track['description']}"
                    if track['language'] and track['language'] != 'Unknown':
                        track_text += f" ({track['language']})"
                    self.track_combo.addItem(track_text, track['index'])
                
                # Try to select current track
                current_track = self.media_player.get_current_audio_track()
                if current_track >= 0:
                    self.track_combo.setCurrentIndex(current_track)
                    
                self.status_label.setText(f"{len(audio_tracks)} audio track(s) available")
                
        except Exception as e:
            self.status_label.setText(f"Error loading tracks: {e}")
            self.track_combo.setEnabled(False)
        finally:
            self.track_combo.blockSignals(False)
            
    def on_track_changed(self, index):
        """Handle track selection change."""
        if not self.media_player or not self.track_combo.isEnabled():
            return
            
        track_index = self.track_combo.itemData(index)
        if track_index is not None:
            success = self.media_player.set_audio_track(track_index)
            if success:
                self.status_label.setText(f"Switched to track {track_index + 1}")
                self.audio_track_changed.emit(track_index)
            else:
                self.status_label.setText("Failed to switch audio track")
                
    def on_media_loaded(self):
        """Call this when new media is loaded."""
        # Delay refresh to allow media to fully load
        self.refresh_timer.start(2000)  # 2 second delay
        
    def on_media_stopped(self):
        """Call this when media is stopped."""
        self.track_combo.clear()
        self.track_combo.setEnabled(False)
        self.status_label.setText("No media loaded")