from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QUrl
from PySide6.QtGui import QPainter, QPixmap, QFont, QPalette
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class ChannelInfoDisplay(QWidget):
    """
    Widget to display current channel information with logo overlay.
    Shows when channel changes and auto-hides after a few seconds.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup widget properties
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 120)
        
        # Current channel data
        self.current_channel = None
        self.channel_logo = None
        
        # Network manager for logo downloads
        self.network_manager = QNetworkAccessManager()
        
        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_with_animation)
        
        # Animation for show/hide
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Setup UI
        self.setup_ui()
        
        # Initially hidden
        self.hide()
        
    def setup_ui(self):
        """Setup the UI layout."""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Logo label
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(80, 80)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("""
            QLabel {
                border: 2px solid #555;
                border-radius: 8px;
                background-color: rgba(40, 40, 40, 200);
                color: white;
                font-size: 24px;
            }
        """)
        self.logo_label.setText("📺")
        layout.addWidget(self.logo_label)
        
        # Text info layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        # Channel name
        self.name_label = QLabel("No Channel")
        self.name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 150);
                padding: 5px 10px;
                border-radius: 5px;
            }
        """)
        text_layout.addWidget(self.name_label)
        
        # Channel category
        self.category_label = QLabel("")
        self.category_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                font-size: 14px;
                background-color: rgba(0, 0, 0, 100);
                padding: 3px 8px;
                border-radius: 3px;
            }
        """)
        text_layout.addWidget(self.category_label)
        
        # Channel info (resolution, etc.)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 12px;
                background-color: rgba(0, 0, 0, 80);
                padding: 2px 6px;
                border-radius: 3px;
            }
        """)
        text_layout.addWidget(self.info_label)
        
        text_layout.addStretch()
        layout.addLayout(text_layout, 1)
        
        # Overall widget styling
        self.setStyleSheet("""
            ChannelInfoDisplay {
                background-color: rgba(20, 20, 20, 220);
                border: 2px solid rgba(100, 100, 100, 150);
                border-radius: 10px;
            }
        """)
    
    def show_channel_info(self, channel, duration_ms=4000):
        """
        Show channel information overlay.
        
        Args:
            channel: Channel dictionary with name, logo, etc.
            duration_ms: How long to show the overlay (milliseconds)
        """
        self.current_channel = channel
        
        # Update channel name
        channel_name = channel.get("name", "Unknown Channel")
        self.name_label.setText(channel_name)
        
        # Update category
        category = channel.get("group-title", "")
        if category and category != "Uncategorized":
            self.category_label.setText(f"📂 {category}")
            self.category_label.show()
        else:
            self.category_label.hide()
        
        # Update additional info
        info_parts = []
        if channel.get("content_type"):
            info_parts.append(f"Type: {channel.get('content_type').title()}")
        if channel.get("tvg-id"):
            info_parts.append(f"ID: {channel.get('tvg-id')}")
        
        if info_parts:
            self.info_label.setText(" • ".join(info_parts))
            self.info_label.show()
        else:
            self.info_label.hide()
        
        # Load logo
        self.load_channel_logo(channel.get("tvg-logo", ""))
        
        # Position the widget
        self.position_overlay()
        
        # Show with animation
        self.show_with_animation()
        
        # Start auto-hide timer
        self.hide_timer.stop()
        self.hide_timer.start(duration_ms)
    
    def load_channel_logo(self, logo_url):
        """Load channel logo from URL."""
        if not logo_url:
            self.logo_label.setText("📺")
            self.channel_logo = None
            return
        
        # Start download
        request = QNetworkRequest(QUrl(logo_url))
        request.setRawHeader(b"User-Agent", b"PyIPTV/1.0")
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._on_logo_downloaded(reply))
    
    def _on_logo_downloaded(self, reply):
        """Handle downloaded logo."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Scale to fit logo label
                scaled_pixmap = pixmap.scaled(
                    76, 76,  # Slightly smaller than label size for padding
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setText("")  # Clear text when image is set
                self.channel_logo = scaled_pixmap
        else:
            # Keep default icon on error
            self.logo_label.setText("📺")
            self.channel_logo = None
        
        reply.deleteLater()
    
    def position_overlay(self):
        """Position the overlay on the parent widget."""
        if self.parent():
            parent_rect = self.parent().rect()
            # Position in top-right corner with some margin
            x = parent_rect.width() - self.width() - 20
            y = 20
            self.move(x, y)
    
    def show_with_animation(self):
        """Show the widget with fade-in animation."""
        self.setWindowOpacity(0.0)
        self.show()
        
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
    
    def hide_with_animation(self):
        """Hide the widget with fade-out animation."""
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self.hide)
        self.opacity_animation.start()
    
    def update_position(self):
        """Update position when parent is resized."""
        if self.isVisible():
            self.position_overlay()
    
    def paintEvent(self, event):
        """Custom paint event for better appearance."""
        super().paintEvent(event)
        
        # Additional custom drawing can be added here if needed
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw subtle shadow effect
        shadow_rect = self.rect().adjusted(2, 2, 2, 2)
        painter.fillRect(shadow_rect, Qt.GlobalColor.black)


class SimpleChannelInfoBar(QWidget):
    """
    Simple channel info bar that can be embedded in the main window.
    Shows current channel name and logo in a compact format.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Current channel data
        self.current_channel = None
        self.channel_logo = None
        
        # Network manager for logo downloads
        self.network_manager = QNetworkAccessManager()
        
        # Setup UI
        self.setup_ui()
        
        # Set fixed height
        self.setFixedHeight(50)
        
    def setup_ui(self):
        """Setup the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Logo label
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(40, 40)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("""
            QLabel {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #2a2a2a;
                color: white;
                font-size: 16px;
            }
        """)
        self.logo_label.setText("📺")
        layout.addWidget(self.logo_label)
        
        # Channel name
        self.name_label = QLabel("No Channel Selected")
        self.name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.name_label, 1)
        
        # Category label
        self.category_label = QLabel("")
        self.category_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.category_label)
        
        # Overall styling
        self.setStyleSheet("""
            SimpleChannelInfoBar {
                background-color: #1e1e1e;
                border-top: 1px solid #555;
            }
        """)
    
    def update_channel_info(self, channel):
        """Update the displayed channel information."""
        self.current_channel = channel
        
        if not channel:
            self.name_label.setText("No Channel Selected")
            self.category_label.setText("")
            self.logo_label.setText("📺")
            self.logo_label.setPixmap(QPixmap())  # Clear pixmap
            return
        
        # Update channel name
        channel_name = channel.get("name", "Unknown Channel")
        self.name_label.setText(channel_name)
        
        # Update category
        category = channel.get("group-title", "")
        if category and category != "Uncategorized":
            self.category_label.setText(f"[{category}]")
        else:
            self.category_label.setText("")
        
        # Load logo
        self.load_channel_logo(channel.get("tvg-logo", ""))
    
    def load_channel_logo(self, logo_url):
        """Load channel logo from URL."""
        if not logo_url:
            self.logo_label.setText("📺")
            self.logo_label.setPixmap(QPixmap())  # Clear pixmap
            self.channel_logo = None
            return
        
        # Start download
        request = QNetworkRequest(QUrl(logo_url))
        request.setRawHeader(b"User-Agent", b"PyIPTV/1.0")
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._on_logo_downloaded(reply))
    
    def _on_logo_downloaded(self, reply):
        """Handle downloaded logo."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Scale to fit logo label
                scaled_pixmap = pixmap.scaled(
                    36, 36,  # Slightly smaller than label size for padding
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setText("")  # Clear text when image is set
                self.channel_logo = scaled_pixmap
        else:
            # Keep default icon on error
            self.logo_label.setText("📺")
            self.logo_label.setPixmap(QPixmap())  # Clear pixmap
            self.channel_logo = None
        
        reply.deleteLater()
