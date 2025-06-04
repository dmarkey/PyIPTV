import sys
import os
import signal
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer
from pyiptv.ui.main_window import MainWindow
from pyiptv.ui.themes import ThemeManager
from pyiptv.ui.playlist_manager_window import PlaylistManagerWindow
from pyiptv.settings_manager import SettingsManager

os.environ["LIBVA_DRIVER_NAME"] = "i965"  # Software VA-API


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM signals."""
    print("\nReceived interrupt signal. Shutting down gracefully...")
    QApplication.quit()


def main():
    """Main function to run the PyIPTV application."""
    app = QApplication(sys.argv)

    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set up a timer to handle signals periodically
    # This allows Qt to process the signals since Python signal handling
    # is disabled when Qt takes control of the event loop
    timer = QTimer()
    timer.start(500)  # Check for signals every 500ms
    timer.timeout.connect(lambda: None)  # Just wake up Qt event loop

    # Set application properties
    app.setApplicationName("PyIPTV")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PyIPTV")

    # Set application icon for taskbar using robust path resolution

    current_dir = Path(__file__).parent
    logo_path = str(current_dir / "ui" / "images" / "logo.png")
    app.setWindowIcon(QIcon(logo_path))

    # Enable high DPI support (updated for newer Qt versions)
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Use desktop OpenGL for better compatibility
    if hasattr(Qt.ApplicationAttribute, "AA_UseDesktopOpenGL"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)

    # Initialize settings and theme manager
    settings_manager = SettingsManager()
    theme_manager = ThemeManager(settings_manager)

    # Apply theme based on user preference (defaults to system_auto which is KDE-aware)
    theme_manager.apply_theme(app)

    # Check if a playlist path was provided as command line argument
    playlist_path = None
    if len(sys.argv) > 1:
        playlist_path = sys.argv[1]
        if not os.path.exists(playlist_path):
            print(f"Warning: Playlist file not found: {playlist_path}")
            playlist_path = None

    # Global variables to hold window references
    main_window = None
    playlist_manager = None

    if playlist_path:
        # Launch directly with the provided playlist
        main_window = MainWindow(playlist_path)
        main_window.setGeometry(100, 100, 1200, 800)
        main_window.show()

        # Print theme info for debugging
        theme_info = theme_manager.get_current_theme_info()
        print(
            f"Theme applied - Desktop: {theme_info.get('desktop_environment', 'unknown')}, "
            f"KDE: {theme_info.get('is_kde', False)}, "
            f"System colors: {theme_info.get('system_color_scheme', 'unknown')}"
        )
    else:
        # Show playlist manager first

        def on_playlist_selected(selected_playlist_path):
            # Create main window with selected playlist
            nonlocal main_window
            main_window = MainWindow(selected_playlist_path)
            main_window.setGeometry(100, 100, 1200, 800)
            main_window.show()

        playlist_manager = PlaylistManagerWindow()
        playlist_manager.playlist_selected.connect(on_playlist_selected)
        playlist_manager.show()

    # Connect app aboutToQuit signal to cleanup
    app.aboutToQuit.connect(lambda: print("Application shutting down..."))

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
