"""
Subtitle display widget for PyIPTV.

This module provides a customizable subtitle overlay widget that can be
positioned over the video player to display subtitle text with proper
styling and positioning.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, 
    QComboBox, QSlider, QCheckBox, QColorDialog, QFontDialog,
    QGroupBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QPainter, QFontMetrics


class SubtitleDisplayWidget(QLabel):
    """Widget for displaying subtitle text over video."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_styling()
        
        # Animation for subtitle transitions
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def setup_ui(self):
        """Setup the subtitle display UI."""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Default positioning (bottom center)
        self.setGeometry(0, 0, 800, 100)
        
    def setup_styling(self):
        """Setup default subtitle styling."""
        font = QFont("Arial", 16, QFont.Weight.Bold)
        self.setFont(font)
        
        # Default style with outline
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 120);
                border: 2px solid black;
                border-radius: 5px;
                padding: 8px 12px;
                text-align: center;
            }
        """)
        
    def update_subtitle_text(self, text: str):
        """Update the displayed subtitle text with fade animation."""
        if text != self.text():
            if text:
                self.setText(text)
                self.show()
                self.fade_in()
            else:
                self.fade_out()
                
    def fade_in(self):
        """Fade in the subtitle."""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        
    def fade_out(self):
        """Fade out the subtitle."""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
        
    def position_subtitle(self, video_widget_geometry, position="bottom"):
        """Position subtitle relative to video widget."""
        video_rect = video_widget_geometry
        
        # Calculate subtitle dimensions
        font_metrics = QFontMetrics(self.font())
        text_width = font_metrics.horizontalAdvance(self.text())
        text_height = font_metrics.height()
        
        # Add padding
        width = min(text_width + 40, video_rect.width() - 20)
        height = text_height + 20
        
        if position == "bottom":
            x = video_rect.x() + (video_rect.width() - width) // 2
            y = video_rect.y() + video_rect.height() - height - 20
        elif position == "top":
            x = video_rect.x() + (video_rect.width() - width) // 2
            y = video_rect.y() + 20
        elif position == "center":
            x = video_rect.x() + (video_rect.width() - width) // 2
            y = video_rect.y() + (video_rect.height() - height) // 2
        else:  # bottom default
            x = video_rect.x() + (video_rect.width() - width) // 2
            y = video_rect.y() + video_rect.height() - height - 20
            
        self.setGeometry(x, y, width, height)


class SubtitleControlWidget(QWidget):
    """Widget for controlling subtitle settings."""
    
    # Signals
    track_changed = Signal(str)  # track_id
    subtitles_toggled = Signal(bool)  # enabled
    font_changed = Signal(QFont)
    color_changed = Signal(QColor)
    position_changed = Signal(str)  # position
    size_changed = Signal(int)  # font size
    
    def __init__(self, subtitle_manager, parent=None):
        super().__init__(parent)
        self.subtitle_manager = subtitle_manager
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the subtitle control UI."""
        layout = QVBoxLayout(self)
        
        # Subtitle track selection
        track_group = QGroupBox("Subtitle Track")
        track_layout = QVBoxLayout(track_group)
        
        self.track_combo = QComboBox()
        self.track_combo.addItem("None", "")
        track_layout.addWidget(self.track_combo)
        
        # Load subtitle file button
        self.load_button = QPushButton("Load Subtitle File...")
        track_layout.addWidget(self.load_button)
        
        layout.addWidget(track_group)
        
        # Subtitle display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout(display_group)
        
        # Enable/disable subtitles
        self.enable_checkbox = QCheckBox("Enable Subtitles")
        self.enable_checkbox.setChecked(True)
        display_layout.addWidget(self.enable_checkbox)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 48)
        self.font_size_slider.setValue(16)
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 48)
        self.font_size_spinbox.setValue(16)
        font_layout.addWidget(self.font_size_slider)
        font_layout.addWidget(self.font_size_spinbox)
        display_layout.addLayout(font_layout)
        
        # Font selection
        self.font_button = QPushButton("Select Font...")
        display_layout.addWidget(self.font_button)
        
        # Color selection
        self.color_button = QPushButton("Select Color...")
        display_layout.addWidget(self.color_button)
        
        # Position selection
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Bottom", "Top", "Center"])
        position_layout.addWidget(self.position_combo)
        display_layout.addLayout(position_layout)
        
        layout.addWidget(display_group)
        
        # Current font and color
        self.current_font = QFont("Arial", 16, QFont.Weight.Bold)
        self.current_color = QColor(Qt.GlobalColor.white)
        
    def connect_signals(self):
        """Connect widget signals."""
        self.track_combo.currentTextChanged.connect(self._on_track_changed)
        self.load_button.clicked.connect(self._on_load_subtitle)
        self.enable_checkbox.toggled.connect(self.subtitles_toggled.emit)
        self.font_size_slider.valueChanged.connect(self._on_font_size_changed)
        self.font_size_spinbox.valueChanged.connect(self._on_font_size_changed)
        self.font_button.clicked.connect(self._on_select_font)
        self.color_button.clicked.connect(self._on_select_color)
        self.position_combo.currentTextChanged.connect(self._on_position_changed)
        
        # Connect to subtitle manager signals
        self.subtitle_manager.subtitle_loaded.connect(self._on_subtitle_loaded)
        
    def _on_track_changed(self):
        """Handle track selection change."""
        track_id = self.track_combo.currentData()
        if track_id:
            self.track_changed.emit(track_id)
            
    def _on_load_subtitle(self):
        """Handle load subtitle button click."""
        track = self.subtitle_manager.select_subtitle_file(self)
        if track:
            self.refresh_tracks()
            
    def _on_font_size_changed(self, size):
        """Handle font size change."""
        # Sync slider and spinbox
        if self.sender() == self.font_size_slider:
            self.font_size_spinbox.setValue(size)
        else:
            self.font_size_slider.setValue(size)
            
        self.current_font.setPointSize(size)
        self.font_changed.emit(self.current_font)
        self.size_changed.emit(size)
        
    def _on_select_font(self):
        """Handle font selection."""
        font, ok = QFontDialog.getFont(self.current_font, self)
        if ok:
            self.current_font = font
            self.font_size_slider.setValue(font.pointSize())
            self.font_size_spinbox.setValue(font.pointSize())
            self.font_changed.emit(font)
            
    def _on_select_color(self):
        """Handle color selection."""
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self.color_changed.emit(color)
            
    def _on_position_changed(self):
        """Handle position change."""
        position = self.position_combo.currentText().lower()
        self.position_changed.emit(position)
        
    def _on_subtitle_loaded(self, track):
        """Handle new subtitle track loaded."""
        self.refresh_tracks()
        
    def refresh_tracks(self):
        """Refresh the track combo box."""
        self.track_combo.clear()
        self.track_combo.addItem("None", "")
        
        for track in self.subtitle_manager.get_available_tracks():
            display_name = f"{track.title} ({track.language})"
            self.track_combo.addItem(display_name, track.id)
            
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current subtitle settings."""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "font": self.current_font,
            "color": self.current_color,
            "position": self.position_combo.currentText().lower(),
            "font_size": self.font_size_slider.value()
        }
