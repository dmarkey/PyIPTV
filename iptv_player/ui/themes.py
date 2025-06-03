from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

class ModernDarkTheme:
    """
    Modern dark theme for the IPTV player with improved UX.
    """
    
    @staticmethod
    def apply(app):
        """Apply the modern dark theme to the application."""
        app.setStyle('Fusion')
        
        # Create custom palette
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        
        # Base colors (for input fields, lists, etc.)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        
        # Text colors
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        
        # Button colors
        palette.setColor(QPalette.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        
        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(100, 149, 237))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Disabled colors
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(120, 120, 120))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
        
        app.setPalette(palette)
        
        # Apply global stylesheet
        app.setStyleSheet(ModernDarkTheme.get_stylesheet())
    
    @staticmethod
    def get_stylesheet():
        """Get the global stylesheet for the modern dark theme."""
        return """
        /* Global styling */
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        /* Menu bar */
        QMenuBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-bottom: 1px solid #555555;
            padding: 2px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #4a90e2;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 8px 20px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #4a90e2;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #555555;
            margin: 4px 0;
        }
        
        /* Status bar */
        QStatusBar {
            background-color: #2d2d2d;
            color: #cccccc;
            border-top: 1px solid #555555;
            padding: 2px;
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: #555555;
            width: 2px;
            height: 2px;
        }
        
        QSplitter::handle:hover {
            background-color: #4a90e2;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #4a90e2;
            border-color: #6ba3f0;
        }
        
        QPushButton:pressed {
            background-color: #357abd;
            border-color: #4a90e2;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #666666;
            border-color: #3a3a3a;
        }
        
        /* Line edits */
        QLineEdit {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
        }
        
        QLineEdit:focus {
            border-color: #4a90e2;
            background-color: #404040;
        }
        
        /* List widgets */
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            outline: none;
            font-size: 13px;
        }
        
        QListWidget::item {
            padding: 8px 12px;
            border-bottom: 1px solid #3a3a3a;
        }
        
        QListWidget::item:selected {
            background-color: #4a90e2;
            color: #ffffff;
        }
        
        QListWidget::item:hover {
            background-color: #3a3a3a;
        }
        
        /* Scroll bars */
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
        }
        
        QScrollBar:horizontal {
            background-color: #2a2a2a;
            height: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #555555;
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #666666;
        }
        
        /* Labels */
        QLabel {
            color: #ffffff;
        }
        
        /* Frames */
        QFrame {
            border-radius: 6px;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #555555;
            border-radius: 3px;
            background-color: #3d3d3d;
        }
        
        QCheckBox::indicator:checked {
            background-color: #4a90e2;
            border-color: #6ba3f0;
        }
        
        QCheckBox::indicator:hover {
            border-color: #4a90e2;
        }
        
        /* Tooltips */
        QToolTip {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 6px;
            font-size: 12px;
        }
        
        /* Progress bars */
        QProgressBar {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            border-radius: 6px;
            text-align: center;
            color: #ffffff;
            font-weight: bold;
        }
        
        QProgressBar::chunk {
            background-color: #4a90e2;
            border-radius: 5px;
        }
        
        /* Sliders */
        QSlider::groove:horizontal {
            border: 1px solid #555555;
            height: 6px;
            background-color: #3d3d3d;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background-color: #4a90e2;
            border: 1px solid #6ba3f0;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #6ba3f0;
        }
        
        QSlider::sub-page:horizontal {
            background-color: #4a90e2;
            border-radius: 3px;
        }
        """

class ModernLightTheme:
    """
    Modern light theme alternative.
    """
    
    @staticmethod
    def apply(app):
        """Apply the modern light theme to the application."""
        app.setStyle('Fusion')
        
        # Create custom palette
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.Window, QColor(248, 248, 248))
        palette.setColor(QPalette.WindowText, QColor(33, 37, 41))
        
        # Base colors
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        
        # Text colors
        palette.setColor(QPalette.Text, QColor(33, 37, 41))
        palette.setColor(QPalette.BrightText, QColor(220, 20, 60))
        
        # Button colors
        palette.setColor(QPalette.Button, QColor(233, 236, 239))
        palette.setColor(QPalette.ButtonText, QColor(33, 37, 41))
        
        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(0, 123, 255))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)