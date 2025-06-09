"""
Unit tests for Favorites Manager functionality.
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from pyiptv.favorites_manager import FavoritesManager, FavoriteChannel, CustomCategory, WatchHistoryEntry


class TestFavoriteChannel:
    """Test cases for FavoriteChannel class."""

    def test_from_channel(self):
        """Test creating FavoriteChannel from channel dict."""
        channel = {
            "name": "Test Channel",
            "url": "http://example.com/stream",
            "group-title": "News",
            "tvg-id": "test123",
            "tvg-logo": "logo.png"
        }
        
        favorite = FavoriteChannel.from_channel(channel, "My Category")
        
        assert favorite.name == "Test Channel"
        assert favorite.url == "http://example.com/stream"
        assert favorite.category == "News"
        assert favorite.tvg_id == "test123"
        assert favorite.tvg_logo == "logo.png"
        assert favorite.custom_category == "My Category"
        assert favorite.watch_count == 0
        assert favorite.rating == 0

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        original = FavoriteChannel(
            name="Test",
            url="http://test.com",
            category="Sports",
            rating=4,
            watch_count=10
        )
        
        data = original.to_dict()
        restored = FavoriteChannel.from_dict(data)
        
        assert restored.name == original.name
        assert restored.url == original.url
        assert restored.category == original.category
        assert restored.rating == original.rating
        assert restored.watch_count == original.watch_count


class TestWatchHistoryEntry:
    """Test cases for WatchHistoryEntry class."""

    def test_duration_str(self):
        """Test duration string formatting."""
        entry = WatchHistoryEntry(
            channel_name="Test",
            channel_url="http://test.com",
            start_time="2023-01-01T12:00:00",
            duration_seconds=3665  # 1 hour, 1 minute, 5 seconds
        )
        
        assert entry.duration_str == "01:01:05"

    def test_duration_str_short(self):
        """Test duration string for short durations."""
        entry = WatchHistoryEntry(
            channel_name="Test",
            channel_url="http://test.com",
            start_time="2023-01-01T12:00:00",
            duration_seconds=125  # 2 minutes, 5 seconds
        )
        
        assert entry.duration_str == "00:02:05"


class TestFavoritesManager:
    """Test cases for FavoritesManager class."""

    def test_init(self, mock_settings_manager, temp_dir):
        """Test FavoritesManager initialization."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            assert len(manager.favorites) == 0
            assert len(manager.custom_categories) >= 3  # Default categories
            assert len(manager.watch_history) == 0

    def test_add_favorite(self, mock_settings_manager, temp_dir):
        """Test adding a channel to favorites."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            
            result = manager.add_favorite(channel, "My Category")
            
            assert result is True
            assert manager.is_favorite("http://example.com/stream")
            assert len(manager.favorites) == 1
            
            favorite = manager.favorites["http://example.com/stream"]
            assert favorite.name == "Test Channel"
            assert favorite.custom_category == "My Category"

    def test_add_duplicate_favorite(self, mock_settings_manager, temp_dir):
        """Test adding duplicate favorite."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            
            # Add first time
            result1 = manager.add_favorite(channel)
            assert result1 is True
            
            # Add second time (should return False but update category)
            result2 = manager.add_favorite(channel, "New Category")
            assert result2 is False
            assert len(manager.favorites) == 1
            
            # Check category was updated
            favorite = manager.favorites["http://example.com/stream"]
            assert favorite.custom_category == "New Category"

    def test_remove_favorite(self, mock_settings_manager, temp_dir):
        """Test removing a favorite."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            
            manager.add_favorite(channel)
            assert len(manager.favorites) == 1
            
            result = manager.remove_favorite("http://example.com/stream")
            assert result is True
            assert len(manager.favorites) == 0
            assert not manager.is_favorite("http://example.com/stream")

    def test_rate_channel(self, mock_settings_manager, temp_dir):
        """Test rating a channel."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            
            manager.add_favorite(channel)
            
            # Valid rating
            result = manager.rate_channel("http://example.com/stream", 4)
            assert result is True
            assert manager.favorites["http://example.com/stream"].rating == 4
            
            # Invalid rating
            result = manager.rate_channel("http://example.com/stream", 10)
            assert result is False
            assert manager.favorites["http://example.com/stream"].rating == 4

    def test_create_custom_category(self, mock_settings_manager, temp_dir):
        """Test creating custom category."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            result = manager.create_custom_category("Sports", "Sports channels", "#ff0000")
            assert result is True
            assert "Sports" in manager.custom_categories
            
            category = manager.custom_categories["Sports"]
            assert category.description == "Sports channels"
            assert category.color == "#ff0000"
            
            # Try to create duplicate
            result = manager.create_custom_category("Sports", "Duplicate")
            assert result is False

    def test_delete_custom_category(self, mock_settings_manager, temp_dir):
        """Test deleting custom category."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            # Create category and add channel to it
            manager.create_custom_category("Test Category")
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            manager.add_favorite(channel, "Test Category")
            
            # Delete category
            result = manager.delete_custom_category("Test Category")
            assert result is True
            assert "Test Category" not in manager.custom_categories
            
            # Check that channel's custom category was cleared
            favorite = manager.favorites["http://example.com/stream"]
            assert favorite.custom_category is None

    def test_start_stop_watching(self, mock_settings_manager, temp_dir):
        """Test watch tracking."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            # Add channel to favorites
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            manager.add_favorite(channel)
            
            # Start watching
            manager.start_watching("Test Channel", "http://example.com/stream")
            assert manager.current_watching is not None
            assert manager.current_watching.channel_name == "Test Channel"
            
            # Simulate some watching time
            import time
            time.sleep(0.1)  # Small delay to ensure duration > 0
            
            # Stop watching
            manager.stop_watching()
            assert manager.current_watching is None
            
            # Check history was recorded (if duration >= 30 seconds)
            # Note: In real test, we'd mock datetime to control duration

    def test_get_favorites_by_category(self, mock_settings_manager, temp_dir):
        """Test getting favorites filtered by category."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            # Create custom category
            manager.create_custom_category("My Sports")
            
            # Add channels
            channels = [
                {"name": "News 1", "url": "http://news1.com", "group-title": "News"},
                {"name": "Sports 1", "url": "http://sports1.com", "group-title": "Sports"},
                {"name": "Sports 2", "url": "http://sports2.com", "group-title": "Sports"}
            ]
            
            manager.add_favorite(channels[0])
            manager.add_favorite(channels[1], "My Sports")
            manager.add_favorite(channels[2], "My Sports")
            
            # Test original category filter
            news_favorites = manager.get_favorites("News")
            assert len(news_favorites) == 1
            assert news_favorites[0].name == "News 1"
            
            # Test custom category filter
            sports_favorites = manager.get_favorites("custom:My Sports")
            assert len(sports_favorites) == 2
            
            # Test no filter
            all_favorites = manager.get_favorites()
            assert len(all_favorites) == 3

    def test_get_viewing_stats(self, mock_settings_manager, temp_dir):
        """Test viewing statistics."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            manager = FavoritesManager(mock_settings_manager)
            
            # Add some watch history entries
            today = datetime.now().date().isoformat()
            entries = [
                WatchHistoryEntry("Channel 1", "http://ch1.com", "2023-01-01T12:00:00", 
                                 duration_seconds=3600, date=today),
                WatchHistoryEntry("Channel 2", "http://ch2.com", "2023-01-01T13:00:00", 
                                 duration_seconds=1800, date=today),
                WatchHistoryEntry("Channel 1", "http://ch1.com", "2023-01-01T14:00:00", 
                                 duration_seconds=2400, date=today),
            ]
            
            manager.watch_history = entries
            
            stats = manager.get_viewing_stats(30)
            
            assert stats["total_watch_time"] == 7800  # 3600 + 1800 + 2400
            assert stats["total_sessions"] == 3
            assert stats["average_session_length"] == 2600  # 7800 / 3
            assert len(stats["most_watched_channels"]) > 0
            assert stats["most_watched_channels"][0][0] == "Channel 1"  # Most watched
            assert stats["most_watched_channels"][0][1] == 2  # Watched twice

    def test_export_import_favorites(self, mock_settings_manager, temp_dir):
        """Test exporting and importing favorites."""
        with patch.object(FavoritesManager, '_get_data_file_path', 
                         return_value=str(temp_dir / "favorites.json")):
            # Create manager and add data
            manager1 = FavoritesManager(mock_settings_manager)
            
            manager1.create_custom_category("Test Category", "Test description")
            
            channel = {
                "name": "Test Channel",
                "url": "http://example.com/stream",
                "group-title": "News"
            }
            manager1.add_favorite(channel, "Test Category")
            
            # Export
            export_file = temp_dir / "export.json"
            result = manager1.export_favorites(str(export_file), "json")
            assert result is True
            assert export_file.exists()
            
            # Create new manager and import
            manager2 = FavoritesManager(mock_settings_manager)
            result = manager2.import_favorites(str(export_file))
            assert result is True
            
            # Verify imported data
            assert len(manager2.favorites) == 1
            assert "http://example.com/stream" in manager2.favorites
            assert "Test Category" in manager2.custom_categories
