import sys
import os
import signal
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtCore import Qt, QTimer
from .ui.main_window import MainWindow
from .ui.themes import ModernDarkTheme

# Basic multimedia configuration
os.environ['QT_MULTIMEDIA_FFMPEG_HWACCEL'] = 'none'  # Software decoding for compatibility

# Video driver and hardware acceleration fixes
os.environ['LIBVA_DRIVER_NAME'] = 'i965'               # Software VA-API
#os.environ['VDPAU_DRIVER'] = 'va_gl'                   # VDPAU fallback
#os.environ['QT_XCB_GL_INTEGRATION'] = 'none'           # Disable XCB OpenGL
#os.environ['QT_MULTIMEDIA_CAMERA_BACKEND'] = 'gstreamer'

# Force software rendering for multimedia
#os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'
#os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '330'

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM signals."""
    print("\nReceived interrupt signal. Shutting down gracefully...")
    QApplication.quit()

def main():
    """Main function to run the IPTV Player application."""
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
    app.setApplicationName("Python IPTV Player")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("IPTV Player")
    
    # Enable high DPI support (updated for newer Qt versions)
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    # Use desktop OpenGL for better compatibility
    if hasattr(Qt.ApplicationAttribute, 'AA_UseDesktopOpenGL'):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
    
    # Apply modern dark theme
    ModernDarkTheme.apply(app)
    
    # Create and show main window
    main_win = MainWindow()
    main_win.setGeometry(100, 100, 1200, 800)  # Larger default size
    main_win.show()
    
    # Connect app aboutToQuit signal to cleanup
    app.aboutToQuit.connect(lambda: print("Application shutting down..."))
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting...")
        sys.exit(0)

if __name__ == '__main__':
    main()