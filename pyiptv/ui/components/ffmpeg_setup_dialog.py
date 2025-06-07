"""
FFmpeg Setup Dialog - Shows progress when downloading FFmpeg binaries.
"""

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QMessageBox
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QIcon


class FFmpegDownloadThread(QThread):
    """Thread for downloading FFmpeg binaries."""
    
    progress_updated = Signal(int)  # Progress percentage
    status_updated = Signal(str)    # Status message
    download_completed = Signal(bool)  # Success/failure
    
    def __init__(self, ffmpeg_manager):
        super().__init__()
        self.ffmpeg_manager = ffmpeg_manager
    
    def run(self):
        """Download FFmpeg in background thread."""
        try:
            self.status_updated.emit("Checking FFmpeg availability...")
            
            # Check if already available
            if self.ffmpeg_manager.check_system_ffmpeg():
                self.status_updated.emit("✅ System FFmpeg found")
                self.download_completed.emit(True)
                return
            
            if self.ffmpeg_manager.is_ffmpeg_available():
                self.status_updated.emit("✅ Bundled FFmpeg found")
                self.download_completed.emit(True)
                return
            
            # Download FFmpeg
            self.status_updated.emit("📥 Downloading FFmpeg binaries...")
            
            def progress_callback(percent):
                self.progress_updated.emit(percent)
                self.status_updated.emit(f"📥 Downloading FFmpeg... {percent}%")
            
            self.ffmpeg_manager.download_ffmpeg(progress_callback)
            
            self.status_updated.emit("✅ FFmpeg installed successfully!")
            self.download_completed.emit(True)
            
        except Exception as e:
            self.status_updated.emit(f"❌ Error: {str(e)}")
            self.download_completed.emit(False)


class FFmpegSetupDialog(QDialog):
    """Dialog for setting up FFmpeg binaries."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyIPTV - Setting up FFmpeg")
        self.setModal(True)
        self.setFixedSize(500, 350)
        
        # Center on parent
        if parent:
            parent_rect = parent.geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        
        self.setup_ui()
        
        # Download thread
        self.download_thread = None
        self.setup_complete = False
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("🎬 Setting up FFmpeg for PyIPTV")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "PyIPTV needs FFmpeg to detect and manage subtitle tracks.\n"
            "This is a one-time setup that will download the required binaries."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to download...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Log area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("Download FFmpeg")
        self.download_btn.clicked.connect(self.start_download)
        
        self.skip_btn = QPushButton("Skip (Limited Features)")
        self.skip_btn.clicked.connect(self.skip_setup)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setEnabled(False)
        
        button_layout.addWidget(self.skip_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def start_download(self):
        """Start FFmpeg download."""
        from pyiptv.ffmpeg_manager import ffmpeg_manager
        
        self.download_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        # Create and start download thread
        self.download_thread = FFmpegDownloadThread(ffmpeg_manager)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.status_updated.connect(self.update_status)
        self.download_thread.download_completed.connect(self.download_finished)
        self.download_thread.start()
    
    def update_progress(self, percent):
        """Update progress bar."""
        self.progress_bar.setValue(percent)
    
    def update_status(self, message):
        """Update status label and log."""
        self.status_label.setText(message)
        self.log_text.append(message)
        
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def download_finished(self, success):
        """Handle download completion."""
        if success:
            self.progress_bar.setValue(100)
            self.update_status("🎉 Setup complete! Subtitle features are now available.")
            self.setup_complete = True
            
            # Auto-close after 2 seconds
            QTimer.singleShot(2000, self.accept)
        else:
            self.update_status("❌ Setup failed. Subtitle features will be limited.")
            self.skip_btn.setEnabled(True)
            self.download_btn.setText("Retry Download")
            self.download_btn.setEnabled(True)
        
        self.close_btn.setEnabled(True)
    
    def skip_setup(self):
        """Skip FFmpeg setup."""
        reply = QMessageBox.question(
            self,
            "Skip FFmpeg Setup",
            "Are you sure you want to skip FFmpeg setup?\n\n"
            "Without FFmpeg, PyIPTV will have limited subtitle features:\n"
            "• No automatic subtitle detection\n"
            "• No embedded subtitle support\n"
            "• Only external subtitle files (.srt) will work\n\n"
            "You can run setup later from the Settings menu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close."""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        event.accept()


def show_ffmpeg_setup_dialog(parent=None):
    """Show FFmpeg setup dialog and return whether setup was completed."""
    dialog = FFmpegSetupDialog(parent)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted and dialog.setup_complete
