import os
from enum import Enum

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QStyleFactory


class ThemeMode(Enum):
    """Theme mode options."""

    SYSTEM_AUTO = "system_auto"  # Use system theme (KDE aware)
    MODERN_DARK = "modern_dark"  # Custom dark theme
    MODERN_LIGHT = "modern_light"  # Custom light theme


class KDEIntegratedTheme:
    """
    Simple theme system that primarily uses Qt's native system integration,
    with minimal custom styling only where needed for media applications.
    """

    @staticmethod
    def is_kde_environment():
        """Check if we're running in KDE."""
        desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        kde_session = os.environ.get("KDE_SESSION_VERSION", "")

        return "kde" in desktop_env or "kde" in session or kde_session

    @staticmethod
    def apply_system_theme(app):
        """
        Apply system-native theme with minimal customization.
        This automatically inherits KDE themes on KDE systems.
        """
        # Let Qt use the system's native style - don't force anything
        # Qt6 automatically uses Breeze on KDE, Windows style on Windows, etc.

        # Only set style if Breeze is available and we're on KDE for consistency
        if KDEIntegratedTheme.is_kde_environment() and "Breeze" in QStyleFactory.keys():
            app.setStyle("Breeze")
        # Otherwise, let Qt choose the appropriate system style

        # Use the system palette completely - don't override it
        # Qt6 automatically reads KDE's color schemes, fonts, etc.

        # Apply only minimal stylesheet for media-specific elements
        app.setStyleSheet(KDEIntegratedTheme._get_minimal_media_stylesheet())

        print(
            f"Applied system theme - KDE environment: {KDEIntegratedTheme.is_kde_environment()}"
        )

    @staticmethod
    def apply_modern_dark_theme(app):
        """Apply custom modern dark theme for non-KDE systems or user preference."""
        app.setStyle("Fusion")

        # Create custom dark palette
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))

        # Base colors (for input fields, lists, etc.)
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))

        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))

        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(100, 149, 237))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        # Disabled colors
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(120, 120, 120),
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120)
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(120, 120, 120),
        )

        app.setPalette(palette)
        app.setStyleSheet(KDEIntegratedTheme._get_dark_theme_stylesheet())

        print("Applied custom modern dark theme")

    @staticmethod
    def apply_modern_light_theme(app):
        """Apply custom modern light theme."""
        app.setStyle("Fusion")

        # Create custom light palette
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 248, 248))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(33, 37, 41))

        # Base colors
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))

        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(33, 37, 41))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(220, 20, 60))

        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(233, 236, 239))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(33, 37, 41))

        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 123, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        app.setPalette(palette)
        app.setStyleSheet(KDEIntegratedTheme._get_light_theme_stylesheet())

        print("Applied custom modern light theme")

    @staticmethod
    def _get_minimal_media_stylesheet():
        """
        Minimal stylesheet that only customizes media-specific elements
        while respecting system theming for everything else.
        """
        return """
        /* Only style elements that need media-specific customization */
        
        /* Video widget - always black for video content */
        QVideoWidget {
            background-color: black;
        }
        
        /* Subtle splitter handle enhancement */
        QSplitter::handle:hover {
            background-color: palette(highlight);
        }
        
        /* Media control sliders - slight enhancement for better visibility */
        QSlider::groove:horizontal {
            height: 6px;
            background: palette(base);
            border: 1px solid palette(mid);
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: palette(highlight);
            border: 1px solid palette(highlight);
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background: palette(bright-text);
        }
        
        QSlider::sub-page:horizontal {
            background: palette(highlight);
            border-radius: 3px;
        }
        
        /* Ensure status bar fits well */
        QStatusBar {
            border-top: 1px solid palette(mid);
        }
        """

    @staticmethod
    def _get_dark_theme_stylesheet():
        """Comprehensive dark theme stylesheet."""
        return """
        /* Modern Dark Theme - Custom */
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
        
        /* Status bar */
        QStatusBar {
            background-color: #2d2d2d;
            color: #cccccc;
            border-top: 1px solid #555555;
            padding: 2px;
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
        }
        
        /* Input fields */
        QLineEdit {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 12px;
        }
        
        QLineEdit:focus {
            border-color: #4a90e2;
        }
        
        /* Lists */
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
        }
        
        QListWidget::item {
            padding: 8px 12px;
            border-bottom: 1px solid #3a3a3a;
        }
        
        QListWidget::item:selected {
            background-color: #4a90e2;
        }
        
        QListWidget::item:hover {
            background-color: #3a3a3a;
        }
        
        /* Video widget */
        QVideoWidget {
            background-color: black;
        }
        
        /* Scrollbars */
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 12px;
            border-radius: 6px;
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
        
        /* Splitter */
        QSplitter::handle {
            background-color: #555555;
        }
        
        QSplitter::handle:hover {
            background-color: #4a90e2;
        }
        """

    @staticmethod
    def _get_light_theme_stylesheet():
        """Light theme stylesheet."""
        return """
        /* Modern Light Theme - Custom */
        QMainWindow {
            background-color: #f8f9fa;
            color: #212529;
        }
        
        /* Menu bar */
        QMenuBar {
            background-color: #ffffff;
            color: #212529;
            border-bottom: 1px solid #dee2e6;
        }
        
        QMenuBar::item:selected {
            background-color: #007bff;
            color: #ffffff;
        }
        
        /* Status bar */
        QStatusBar {
            background-color: #ffffff;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }
        
        /* Video widget */
        QVideoWidget {
            background-color: black;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #e9ecef;
            color: #212529;
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding: 8px 16px;
        }
        
        QPushButton:hover {
            background-color: #007bff;
            color: #ffffff;
        }
        """


class ThemeManager:
    """Main theme manager that chooses the appropriate theming approach."""

    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager

    def apply_theme(self, app, theme_mode=None):
        """Apply the appropriate theme based on mode and environment."""
        # Get theme preference from settings or use auto
        if theme_mode is None:
            theme_mode = (
                self.settings_manager.get_setting("theme_mode")
                if self.settings_manager
                else "system_auto"
            )
            if theme_mode is None:
                theme_mode = "system_auto"

        if theme_mode == ThemeMode.SYSTEM_AUTO.value or theme_mode == "system_auto":
            # Use system theme - automatically inherits KDE on KDE systems
            KDEIntegratedTheme.apply_system_theme(app)
        elif theme_mode == ThemeMode.MODERN_DARK.value or theme_mode == "modern_dark":
            KDEIntegratedTheme.apply_modern_dark_theme(app)
        elif theme_mode == ThemeMode.MODERN_LIGHT.value or theme_mode == "modern_light":
            KDEIntegratedTheme.apply_modern_light_theme(app)
        else:
            # Default fallback
            KDEIntegratedTheme.apply_system_theme(app)

        # Save theme preference
        if self.settings_manager:
            self.settings_manager.set_setting("theme_mode", theme_mode)

    def get_available_themes(self):
        """Get list of available theme options."""
        themes = [
            ("system_auto", "System Default (Auto-detects KDE themes)"),
            ("modern_dark", "Modern Dark"),
            ("modern_light", "Modern Light"),
        ]
        return themes

    def is_kde_environment(self):
        """Check if running in KDE environment."""
        return KDEIntegratedTheme.is_kde_environment()

    def get_current_theme_info(self):
        """Get information about current theme setup."""
        return {
            "desktop_environment": "kde" if self.is_kde_environment() else "other",
            "is_kde": self.is_kde_environment(),
            "system_color_scheme": "auto-detected",
        }


# Backward compatibility classes
class ModernDarkTheme:
    """Backward compatibility - applies custom dark theme."""

    @staticmethod
    def apply(app):
        KDEIntegratedTheme.apply_modern_dark_theme(app)


class ModernLightTheme:
    """Backward compatibility - applies custom light theme."""

    @staticmethod
    def apply(app):
        KDEIntegratedTheme.apply_modern_light_theme(app)


# New recommended class for system integration
class SystemIntegratedTheme:
    """Recommended class that automatically integrates with system themes."""

    @staticmethod
    def apply(app):
        KDEIntegratedTheme.apply_system_theme(app)
