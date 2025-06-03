from PySide6.QtWidgets import QProgressDialog, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import time

class EnhancedProgressDialog(QProgressDialog):
    """
    Enhanced progress dialog with additional stats and ETA calculation.
    """
    
    def __init__(self, title="Progress", cancel_text="Cancel", parent=None):
        super().__init__(title, cancel_text, 0, 100, parent)
        
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(0)
        self.setAutoClose(False)
        self.setMinimumWidth(400)
        
        # Timing for ETA calculation
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.items_processed = 0
        self.last_items_processed = 0
        self.processing_rates = []  # Store recent processing rates
        self.main_status = "Initializing..."
        
        # Setup enhanced UI
        self.setup_enhanced_ui()
        
        # Timer for smooth updates (more frequent for better responsiveness)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms for better responsiveness
        
        # Throttling for rapid updates
        self.last_ui_update_time = time.time()
        self.ui_update_interval = 0.1  # Minimum 100ms between UI updates
        
    def setup_enhanced_ui(self):
        """Setup the enhanced UI with additional information."""
        # Create custom widget for the dialog
        self.stats_widget = QWidget()
        layout = QVBoxLayout(self.stats_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Main progress label
        self.main_label = QLabel("Initializing...")
        self.main_label.setAlignment(Qt.AlignCenter)
        font = self.main_label.font()
        font.setPointSize(font.pointSize() + 1)
        self.main_label.setFont(font)
        layout.addWidget(self.main_label)
        
        # Stats layout
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Items processed
        self.items_label = QLabel("Items: 0")
        self.items_label.setStyleSheet("color: #666; font-size: 11px;")
        stats_layout.addWidget(self.items_label)
        
        # Processing speed
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("color: #666; font-size: 11px;")
        stats_layout.addWidget(self.speed_label)
        
        # ETA
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #666; font-size: 11px;")
        stats_layout.addWidget(self.eta_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Add stats widget to dialog (this is tricky with QProgressDialog)
        # We'll update the label text to include this information instead
        
    def update_progress(self, progress_percent, items_processed=None, status_text=None):
        """Update progress with additional information."""
        self.setValue(progress_percent)
        
        if items_processed is not None:
            self.items_processed = items_processed
            
        if status_text:
            self.main_status = status_text
            
        self._update_stats()
        
    def show_completion(self, total_items, elapsed_time):
        """Show completion message before closing."""
        completion_msg = f"Completed! Processed {total_items:,} items in {self._format_time(elapsed_time)}"
        self.setLabelText(completion_msg)
        self.setValue(100)
        
        # Auto-close after 2 seconds
        QTimer.singleShot(2000, self.close)
        
    def _update_display(self):
        """Update the display with current stats."""
        if self.items_processed > 0:
            self._update_stats()
            
    def _update_stats(self):
        """Update statistics and ETA with improved calculations."""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        if self.items_processed > 0 and elapsed_time > 0.5:  # Reduced wait time for faster feedback
            # Calculate processing rate
            rate = self.items_processed / elapsed_time
            
            # Keep a rolling average of recent rates for smoother ETA
            self.processing_rates.append(rate)
            if len(self.processing_rates) > 8:  # Keep more measurements for stability
                self.processing_rates.pop(0)
                
            avg_rate = sum(self.processing_rates) / len(self.processing_rates)
            
            # Format rate with better scaling
            if avg_rate > 10000:
                rate_str = f"{avg_rate/1000:.0f}K/s"
            elif avg_rate > 1000:
                rate_str = f"{avg_rate/1000:.1f}K/s"
            else:
                rate_str = f"{avg_rate:.0f}/s"
                
            # Calculate ETA with improved logic
            progress = self.value()
            if progress > 2 and progress < 98 and len(self.processing_rates) >= 2:
                # Estimate remaining items based on current progress
                if progress > 0:
                    estimated_total = (self.items_processed * 100) / progress
                    remaining_items = max(0, estimated_total - self.items_processed)
                    if avg_rate > 0:
                        eta_seconds = remaining_items / avg_rate
                        eta_str = self._format_time(eta_seconds)
                    else:
                        eta_str = "--"
                else:
                    eta_str = "--"
            else:
                eta_str = "--"
                
            # Build complete status message with better formatting
            if self.items_processed > 0:
                status_line = f"{self.main_status}\n{self.items_processed:,} items • {rate_str} • ETA: {eta_str}"
            else:
                status_line = f"{self.main_status}\nInitializing..."
            self.setLabelText(status_line)
        else:
            # Just show the main status for now
            self.setLabelText(self.main_status)
                
    def _format_time(self, seconds):
        """Format time in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
            
    def closeEvent(self, event):
        """Clean up when dialog is closed."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        super().closeEvent(event)