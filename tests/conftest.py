"""
Pytest configuration and fixtures for PyIPTV tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"  # Run Qt tests without display
os.environ["PYIPTV_TEST_MODE"] = "1"  # Flag to indicate test mode


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_m3u_content():
    """Sample M3U playlist content for testing."""
    return """#EXTM3U
#EXTINF:-1 tvg-id="channel1" tvg-name="Test Channel 1" tvg-logo="logo1.png" group-title="News",Test Channel 1
http://example.com/stream1.m3u8
#EXTINF:-1 tvg-id="channel2" tvg-name="Test Channel 2" tvg-logo="logo2.png" group-title="Sports",Test Channel 2
http://example.com/stream2.m3u8
#EXTINF:-1 tvg-id="channel3" tvg-name="Test Channel 3" group-title="Movies",Test Channel 3
http://example.com/stream3.m3u8
"""


@pytest.fixture
def sample_m3u_file(temp_dir, sample_m3u_content):
    """Create a sample M3U file for testing."""
    m3u_file = temp_dir / "test_playlist.m3u"
    m3u_file.write_text(sample_m3u_content)
    return m3u_file


@pytest.fixture
def mock_settings_manager():
    """Mock settings manager for testing."""
    mock = Mock()
    mock.get_setting.return_value = None
    mock.set_setting.return_value = None
    mock.save_settings.return_value = None
    mock.settings_filepath = "/tmp/test_settings.json"  # Add this for PlaylistManager
    mock._get_settings_filepath.return_value = "/tmp/test_settings.json"
    mock.DEFAULT_SETTINGS = {
        "m3u_filepath": None,
        "last_played_url": None,
        "volume": 80,
        "buffering_ms": 1500,
        "hidden_categories": [],
        "window_geometry": None,
        "auto_play_last": False,
        "default_category": "All Channels",
        "splitter_sizes": None,
        "theme_mode": "system_auto",
        "large_file_threshold": 1000000,
        "search_delay_ms": 300,
        "render_buffer_size": 5,
        "progress_update_interval": 1000,
    }
    return mock


@pytest.fixture
def qt_app():
    """Create a QApplication instance for Qt tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    # Clean up
    app.processEvents()


@pytest.fixture(autouse=True)
def mock_qt_multimedia():
    """Mock Qt multimedia components to avoid hardware dependencies."""
    with patch("PySide6.QtMultimedia.QMediaPlayer"), patch(
        "PySide6.QtMultimedia.QAudioOutput"
    ), patch("PySide6.QtMultimediaWidgets.QVideoWidget"):
        yield


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing."""
    mock = Mock()
    mock.get_cached_data.return_value = None
    mock.cache_data.return_value = None
    mock.is_cache_valid.return_value = False
    mock.clear_cache.return_value = None
    mock.load_cache.return_value = None  # Add this method
    mock.save_cache.return_value = True  # Add this method
    return mock


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "ui: UI tests requiring Qt")
    config.addinivalue_line("markers", "slow: Slow tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    _ = config  # Unused parameter
    for item in items:
        # Add 'ui' marker to tests that use qt_app fixture
        if "qt_app" in item.fixturenames:
            item.add_marker(pytest.mark.ui)

        # Add 'unit' marker to test files in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add 'integration' marker to test files in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
