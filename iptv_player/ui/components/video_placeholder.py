from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QPoint
from PySide6.QtGui import QPainter, QPixmap, QIcon, QFont, QFontMetrics, QPalette, QLinearGradient, QBrush, QColor
import math

class VideoPlaceholder(QWidget):
    """
    A beautiful placeholder widget displayed when no video is playing.
    Features animated elements and helpful information.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        
        # Animation properties
        self._animation_progress = 0.0
        self._pulse_opacity = 1.0
        
        # Setup animations
        self.setup_animations()
        
        # Setup UI
        self.setup_ui()
        
        # Start animations
        self.start_animations()
        
    def setup_ui(self):
        """Setup the placeholder UI elements."""
        self.setStyleSheet("""
            VideoPlaceholder {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:0.5 #2d2d2d, stop:1 #1a1a1a);
                border: none;
            }
        """)
        
    def setup_animations(self):
        """Setup smooth animations for the placeholder."""
        # Rotation animation
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.update_animation)
        
        # Pulse animation for text
        self.pulse_animation = QPropertyAnimation(self, b"pulse_opacity")
        self.pulse_animation.setDuration(2000)
        self.pulse_animation.setStartValue(0.3)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        
    def start_animations(self):
        """Start all animations."""
        self.rotation_timer.start(50)  # 20 FPS for smooth animation
        self.pulse_animation.start()
        
    def stop_animations(self):
        """Stop all animations."""
        self.rotation_timer.stop()
        self.pulse_animation.stop()
        
    def update_animation(self):
        """Update animation progress and repaint."""
        self._animation_progress += 2.0  # Degrees per frame
        if self._animation_progress >= 360:
            self._animation_progress = 0.0
        self.update()
        
    @Property(float)
    def pulse_opacity(self):
        return self._pulse_opacity
        
    @pulse_opacity.setter
    def pulse_opacity(self, value):
        self._pulse_opacity = value
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event for the placeholder."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        
        # Draw background gradient
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(26, 26, 26))
        gradient.setColorAt(0.5, QColor(45, 45, 45))
        gradient.setColorAt(1, QColor(26, 26, 26))
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # Draw animated play icon in center
        self.draw_animated_play_icon(painter, center_x, center_y)
        
        # Draw pulsing text
        self.draw_pulsing_text(painter, center_x, center_y + 80)
        
        # Draw helpful shortcuts
        self.draw_shortcuts(painter, width, height)
        
    def draw_animated_play_icon(self, painter, x, y):
        """Draw an animated play icon with rotating elements."""
        painter.save()
        
        # Translate to center
        painter.translate(x, y)
        
        # Draw outer rotating ring
        painter.rotate(self._animation_progress)
        painter.setPen(QColor(70, 130, 180, 100))  # Steel blue with transparency
        painter.setBrush(Qt.NoBrush)
        for i in range(8):
            angle = i * 45
            painter.save()
            painter.rotate(angle)
            painter.drawEllipse(-2, -40, 4, 8)
            painter.restore()
            
        painter.restore()
        painter.save()
        painter.translate(x, y)
        
        # Draw inner counter-rotating ring
        painter.rotate(-self._animation_progress * 0.7)
        painter.setPen(QColor(100, 149, 237, 80))  # Cornflower blue
        for i in range(6):
            angle = i * 60
            painter.save()
            painter.rotate(angle)
            painter.drawRect(-1, -30, 2, 6)
            painter.restore()
            
        painter.restore()
        painter.save()
        painter.translate(x, y)
        
        # Draw main play icon (triangle)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(100, 149, 237, int(200 * self._pulse_opacity)))
        
        # Create play triangle
        triangle = [
            QPoint(-15, -20),
            QPoint(-15, 20),
            QPoint(20, 0)
        ]
        painter.drawPolygon(triangle)
        
        # Draw inner highlight
        painter.setBrush(QColor(255, 255, 255, int(100 * self._pulse_opacity)))
        triangle_small = [
            QPoint(-10, -12),
            QPoint(-10, 12),
            QPoint(12, 0)
        ]
        painter.drawPolygon(triangle_small)
        
        painter.restore()
        
    def draw_pulsing_text(self, painter, x, y):
        """Draw pulsing text below the icon."""
        painter.save()
        
        # Set font
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        
        # Set color with pulsing opacity
        color = QColor(200, 200, 200, int(255 * self._pulse_opacity))
        painter.setPen(color)
        
        # Draw main text
        text = "No video playing"
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        painter.drawText(x - text_width // 2, y, text)
        
        # Draw subtitle
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        color.setAlpha(int(180 * self._pulse_opacity))
        painter.setPen(color)
        
        subtitle = "Select a channel to start watching"
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(subtitle)
        painter.drawText(x - text_width // 2, y + 25, subtitle)
        
        painter.restore()
        
    def draw_shortcuts(self, painter, width, height):
        """Draw helpful keyboard shortcuts in the corners."""
        painter.save()
        
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QColor(120, 120, 120, int(150 * self._pulse_opacity)))
        
        # Bottom left shortcuts
        shortcuts = [
            "F11 - Fullscreen",
            "Ctrl+O - Open M3U",
            "Ctrl+F - Search channels",
            "Space - Play/Pause"
        ]
        
        y_offset = height - 20
        for i, shortcut in enumerate(shortcuts):
            painter.drawText(10, y_offset - (i * 15), shortcut)
            
        # Bottom right info
        info_text = "Python IPTV Player"
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(info_text)
        painter.drawText(width - text_width - 10, height - 10, info_text)
        
        painter.restore()
        
    def hideEvent(self, event):
        """Stop animations when hidden."""
        self.stop_animations()
        super().hideEvent(event)
        
    def showEvent(self, event):
        """Start animations when shown."""
        self.start_animations()
        super().showEvent(event)