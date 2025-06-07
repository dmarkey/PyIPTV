#!/usr/bin/env python3
"""
Recording Status Widget for PyIPTV

This widget displays active recordings and provides controls to stop them.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class RecordingStatusItem(QFrame):
    """Widget representing a single recording session."""
    
    stop_requested = Signal(str)  # session_id
    
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the UI for this recording item."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMaximumHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Recording indicator
        self.status_label = QLabel("🔴")
        self.status_label.setStyleSheet("color: red; font-size: 16px;")
        layout.addWidget(self.status_label)
        
        # Channel info
        info_layout = QVBoxLayout()
        
        self.channel_label = QLabel(self.session.channel_name)
        font = QFont()
        font.setBold(True)
        self.channel_label.setFont(font)
        info_layout.addWidget(self.channel_label)
        
        self.details_label = QLabel()
        self.details_label.setStyleSheet("color: gray; font-size: 11px;")
        info_layout.addWidget(self.details_label)
        
        layout.addLayout(info_layout, 1)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMaximumWidth(60)
        self.stop_button.clicked.connect(lambda: self.stop_requested.emit(self.session.id))
        layout.addWidget(self.stop_button)
        
        self.update_display()
        
    def update_display(self):
        """Update the display with current recording info."""
        if not self.session.is_active:
            self.update_timer.stop()
            return
            
        # Update details
        duration_str = self.session.duration_str
        size_str = self.session.file_size_str
        
        details = f"Duration: {duration_str} | Size: {size_str}"
        if self.session.status.value:
            details += f" | Status: {self.session.status.value.title()}"
            
        self.details_label.setText(details)
        
        # Update status indicator based on recording state
        if self.session.status.value == "recording":
            self.status_label.setText("🔴")
            self.status_label.setStyleSheet("color: red; font-size: 16px;")
        elif self.session.status.value == "paused":
            self.status_label.setText("⏸️")
            self.status_label.setStyleSheet("color: orange; font-size: 16px;")
        else:
            self.status_label.setText("⏹️")
            self.status_label.setStyleSheet("color: gray; font-size: 16px;")


class RecordingStatusWidget(QWidget):
    """Widget to display and manage active recordings."""
    
    stop_recording_requested = Signal(str)  # session_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording_items = {}  # session_id -> RecordingStatusItem
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("🎬 Active Recordings")
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: gray; font-size: 11px;")
        header_layout.addWidget(self.count_label)
        
        layout.addLayout(header_layout)
        
        # Scroll area for recording items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(200)
        
        # Container widget for recording items
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)
        
        # Add stretch to push items to top
        self.container_layout.addStretch()
        
        self.scroll_area.setWidget(self.container_widget)
        layout.addWidget(self.scroll_area)
        
        # Initially hidden
        self.setVisible(False)
        
    def add_recording(self, session):
        """Add a new recording session."""
        if session.id in self.recording_items:
            return  # Already exists
            
        # Create recording item
        item = RecordingStatusItem(session)
        item.stop_requested.connect(self.stop_recording_requested.emit)
        
        # Insert before the stretch
        self.container_layout.insertWidget(
            self.container_layout.count() - 1, 
            item
        )
        
        self.recording_items[session.id] = item
        self.update_display()
        
    def remove_recording(self, session_id):
        """Remove a recording session."""
        if session_id not in self.recording_items:
            return
            
        item = self.recording_items[session_id]
        self.container_layout.removeWidget(item)
        item.deleteLater()
        
        del self.recording_items[session_id]
        self.update_display()
        
    def update_recording(self, session):
        """Update an existing recording session."""
        if session.id in self.recording_items:
            self.recording_items[session.id].session = session
            
    def clear_all_recordings(self):
        """Clear all recording items."""
        for session_id in list(self.recording_items.keys()):
            self.remove_recording(session_id)
            
    def update_display(self):
        """Update the display based on current recordings."""
        count = len(self.recording_items)
        
        # Update count label
        self.count_label.setText(str(count))
        
        # Show/hide widget based on whether there are active recordings
        self.setVisible(count > 0)
        
        # Update title
        if count == 0:
            self.title_label.setText("🎬 Active Recordings")
        elif count == 1:
            self.title_label.setText("🎬 Active Recording")
        else:
            self.title_label.setText(f"🎬 Active Recordings ({count})")
            
    def get_active_count(self):
        """Get the number of active recordings."""
        return len(self.recording_items)
