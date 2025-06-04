from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class MetadataDisplay(QWidget):
    """
    Widget to display stream metadata information like resolution, FPS, codecs, etc.
    """

    # Signal emitted when user wants to toggle visibility
    visibility_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metadata = {}
        self.is_collapsed = True  # Start collapsed by default

        self.setup_ui()
        self.setup_styling()
        self.clear_metadata()

        # Set initial collapsed state
        self.content_frame.hide()
        self.status_label.hide()
        self.collapse_btn.setText("▶")
        self.setMaximumHeight(40)

    def setup_ui(self):
        """Setup the metadata display UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # Header with title and collapse button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel("Stream Info")
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))

        self.collapse_btn = QLabel("▼")
        self.collapse_btn.setMaximumWidth(20)
        self.collapse_btn.setAlignment(Qt.AlignCenter)
        self.collapse_btn.setToolTip("Click to collapse/expand")
        self.collapse_btn.mousePressEvent = self.toggle_collapse

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        main_layout.addLayout(header_layout)

        # Metadata content area
        self.content_frame = QFrame()
        self.content_layout = QGridLayout(self.content_frame)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(6)

        # Create metadata labels
        self.metadata_labels = {}
        self.create_metadata_row("Resolution:", "resolution", 0)
        self.create_metadata_row("Frame Rate:", "fps", 1)
        self.create_metadata_row("Video Codec:", "video_codec", 2)
        self.create_metadata_row("Audio Codec:", "audio_codec", 3)
        self.create_metadata_row("Video Bitrate:", "video_bitrate", 4)
        self.create_metadata_row("Audio Bitrate:", "audio_bitrate", 5)
        self.create_metadata_row("Sample Rate:", "sample_rate", 6)
        self.create_metadata_row("Duration:", "duration", 7)

        main_layout.addWidget(self.content_frame)

        # Status label for when no stream is playing
        self.status_label = QLabel("No stream playing")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: rgba(255, 255, 255, 128); font-style: italic;"
        )
        main_layout.addWidget(self.status_label)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    def create_metadata_row(self, label_text, key, row):
        """Create a metadata row with label and value."""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9, QFont.Bold))
        label.setMinimumWidth(100)

        value_label = QLabel("N/A")
        value_label.setFont(QFont("Arial", 9))
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.content_layout.addWidget(label, row, 0, Qt.AlignTop)
        self.content_layout.addWidget(value_label, row, 1, Qt.AlignTop)

        self.metadata_labels[key] = value_label

    def setup_styling(self):
        """Apply styling to the metadata display."""
        self.setStyleSheet(
            """
            MetadataDisplay {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 40, 40, 200),
                    stop:1 rgba(25, 25, 25, 220));
                border: 1px solid rgba(80, 80, 80, 150);
                border-radius: 8px;
            }
            
            QLabel {
                color: rgba(255, 255, 255, 220);
                background: transparent;
            }
            
            QFrame {
                background: transparent;
                border: none;
            }
        """
        )

    def update_metadata(self, metadata_dict):
        """Update the metadata display with new information."""
        self.metadata = metadata_dict.copy()

        # Update individual metadata fields
        for key, label in self.metadata_labels.items():
            value = metadata_dict.get(key, "N/A")
            if value and value != "N/A":
                label.setText(str(value))
                label.setStyleSheet("color: rgba(255, 255, 255, 255);")
            else:
                label.setText("N/A")
                label.setStyleSheet("color: rgba(255, 255, 255, 128);")

        # Hide status label when we have metadata
        if metadata_dict:
            self.status_label.hide()
            self.content_frame.show()
        else:
            self.status_label.show()
            self.content_frame.hide()

    def clear_metadata(self):
        """Clear all metadata information."""
        self.metadata = {}
        for label in self.metadata_labels.values():
            label.setText("N/A")
            label.setStyleSheet("color: rgba(255, 255, 255, 128);")

        self.status_label.show()
        self.content_frame.hide()

    def toggle_collapse(self, event):
        """Toggle the collapsed state of the metadata display."""
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.content_frame.hide()
            self.status_label.hide()
            self.collapse_btn.setText("▶")
            self.setMaximumHeight(40)
        else:
            if self.metadata:
                self.content_frame.show()
                self.status_label.hide()
            else:
                self.content_frame.hide()
                self.status_label.show()
            self.collapse_btn.setText("▼")
            self.setMaximumHeight(16777215)  # Remove height restriction

    def get_metadata_summary(self):
        """Get a summary string of key metadata."""
        if not self.metadata:
            return "No stream info"

        parts = []

        # Resolution
        resolution = self.metadata.get("resolution")
        if resolution and resolution != "N/A":
            parts.append(resolution)

        # FPS
        fps = self.metadata.get("fps")
        if fps and fps != "N/A" and fps != "Unknown":
            parts.append(f"{fps} fps")

        # Video codec
        video_codec = self.metadata.get("video_codec")
        if video_codec and video_codec != "N/A":
            parts.append(video_codec)

        return " • ".join(parts) if parts else "Stream info available"

    def set_compact_mode(self, compact=True):
        """Set compact display mode showing only essential info."""
        if compact:
            # Hide less important metadata in compact mode
            less_important = [
                "audio_bitrate",
                "video_bitrate",
                "sample_rate",
                "duration",
            ]
            for key in less_important:
                if key in self.metadata_labels:
                    # Find the row and hide both label and value
                    for i in range(self.content_layout.rowCount()):
                        item = self.content_layout.itemAtPosition(i, 1)
                        if item and item.widget() == self.metadata_labels[key]:
                            # Hide both label and value
                            label_item = self.content_layout.itemAtPosition(i, 0)
                            if label_item:
                                label_item.widget().hide()
                            item.widget().hide()
                            break
        else:
            # Show all metadata
            for i in range(self.content_layout.rowCount()):
                for j in range(self.content_layout.columnCount()):
                    item = self.content_layout.itemAtPosition(i, j)
                    if item and item.widget():
                        item.widget().show()
