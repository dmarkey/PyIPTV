"""
Favorites and Watchlist management for PyIPTV.

This module provides comprehensive favorites functionality including:
- Channel favorites management
- Custom category creation
- Watchlist with viewing history
- Import/export functionality
- Smart recommendations based on viewing patterns
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from collections import defaultdict, Counter


@dataclass
class FavoriteChannel:
    """Represents a favorite channel."""
    name: str
    url: str
    category: str
    tvg_id: str = ""
    tvg_logo: str = ""
    added_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_watched: Optional[str] = None
    watch_count: int = 0
    custom_category: Optional[str] = None
    notes: str = ""
    rating: int = 0  # 0-5 stars
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FavoriteChannel':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_channel(cls, channel: Dict[str, str], custom_category: str = None) -> 'FavoriteChannel':
        """Create from channel dictionary."""
        return cls(
            name=channel.get("name", ""),
            url=channel.get("url", ""),
            category=channel.get("group-title", "Uncategorized"),
            tvg_id=channel.get("tvg-id", ""),
            tvg_logo=channel.get("tvg-logo", ""),
            custom_category=custom_category
        )


@dataclass
class WatchHistoryEntry:
    """Represents a watch history entry."""
    channel_name: str
    channel_url: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: int = 0
    date: str = field(default_factory=lambda: datetime.now().date().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchHistoryEntry':
        """Create from dictionary."""
        return cls(**data)
    
    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@dataclass
class CustomCategory:
    """Represents a custom category."""
    name: str
    description: str = ""
    color: str = "#3498db"  # Default blue color
    icon: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    channel_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomCategory':
        """Create from dictionary."""
        return cls(**data)


class FavoritesManager(QObject):
    """Manages favorites, watchlist, and viewing history."""
    
    # Signals
    favorite_added = Signal(str)  # channel_name
    favorite_removed = Signal(str)  # channel_name
    category_created = Signal(str)  # category_name
    category_deleted = Signal(str)  # category_name
    watch_history_updated = Signal(str)  # channel_name
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        
        # Data storage
        self.favorites: Dict[str, FavoriteChannel] = {}  # key: channel_url
        self.custom_categories: Dict[str, CustomCategory] = {}
        self.watch_history: List[WatchHistoryEntry] = []
        self.current_watching: Optional[WatchHistoryEntry] = None
        
        # Load data
        self._load_data()
        
        # Default custom categories
        self._create_default_categories()
    
    def add_favorite(self, channel: Dict[str, str], custom_category: str = None) -> bool:
        """Add a channel to favorites."""
        channel_url = channel.get("url", "")
        if not channel_url:
            return False
            
        if channel_url in self.favorites:
            # Already in favorites, update custom category if provided
            if custom_category:
                self.favorites[channel_url].custom_category = custom_category
                self._save_data()
            return False
            
        # Create favorite channel
        favorite = FavoriteChannel.from_channel(channel, custom_category)
        self.favorites[channel_url] = favorite
        
        # Update custom category count
        if custom_category and custom_category in self.custom_categories:
            self.custom_categories[custom_category].channel_count += 1
        
        self._save_data()
        self.favorite_added.emit(favorite.name)
        return True
    
    def remove_favorite(self, channel_url: str) -> bool:
        """Remove a channel from favorites."""
        if channel_url not in self.favorites:
            return False
            
        favorite = self.favorites[channel_url]
        
        # Update custom category count
        if favorite.custom_category and favorite.custom_category in self.custom_categories:
            self.custom_categories[favorite.custom_category].channel_count -= 1
        
        del self.favorites[channel_url]
        self._save_data()
        self.favorite_removed.emit(favorite.name)
        return True
    
    def is_favorite(self, channel_url: str) -> bool:
        """Check if a channel is in favorites."""
        return channel_url in self.favorites
    
    def get_favorites(self, category: str = None) -> List[FavoriteChannel]:
        """Get favorite channels, optionally filtered by category."""
        favorites = list(self.favorites.values())
        
        if category:
            if category.startswith("custom:"):
                # Custom category
                custom_cat = category[7:]  # Remove "custom:" prefix
                favorites = [f for f in favorites if f.custom_category == custom_cat]
            else:
                # Original category
                favorites = [f for f in favorites if f.category == category]
        
        # Sort by most recently added
        favorites.sort(key=lambda f: f.added_date, reverse=True)
        return favorites
    
    def get_favorites_by_rating(self, min_rating: int = 1) -> List[FavoriteChannel]:
        """Get favorites filtered by minimum rating."""
        favorites = [f for f in self.favorites.values() if f.rating >= min_rating]
        favorites.sort(key=lambda f: f.rating, reverse=True)
        return favorites
    
    def get_most_watched_favorites(self, limit: int = 10) -> List[FavoriteChannel]:
        """Get most watched favorite channels."""
        favorites = [f for f in self.favorites.values() if f.watch_count > 0]
        favorites.sort(key=lambda f: f.watch_count, reverse=True)
        return favorites[:limit]
    
    def rate_channel(self, channel_url: str, rating: int) -> bool:
        """Rate a favorite channel (0-5 stars)."""
        if channel_url not in self.favorites:
            return False
            
        if not 0 <= rating <= 5:
            return False
            
        self.favorites[channel_url].rating = rating
        self._save_data()
        return True
    
    def add_note_to_channel(self, channel_url: str, note: str) -> bool:
        """Add a note to a favorite channel."""
        if channel_url not in self.favorites:
            return False
            
        self.favorites[channel_url].notes = note
        self._save_data()
        return True
    
    def create_custom_category(self, name: str, description: str = "", color: str = "#3498db") -> bool:
        """Create a new custom category."""
        if name in self.custom_categories:
            return False
            
        category = CustomCategory(
            name=name,
            description=description,
            color=color
        )
        
        self.custom_categories[name] = category
        self._save_data()
        self.category_created.emit(name)
        return True
    
    def delete_custom_category(self, name: str) -> bool:
        """Delete a custom category."""
        if name not in self.custom_categories:
            return False
            
        # Remove category from all favorites
        for favorite in self.favorites.values():
            if favorite.custom_category == name:
                favorite.custom_category = None
        
        del self.custom_categories[name]
        self._save_data()
        self.category_deleted.emit(name)
        return True
    
    def get_custom_categories(self) -> List[CustomCategory]:
        """Get all custom categories."""
        return list(self.custom_categories.values())
    
    def move_to_category(self, channel_url: str, category_name: str) -> bool:
        """Move a favorite channel to a different custom category."""
        if channel_url not in self.favorites:
            return False
            
        if category_name and category_name not in self.custom_categories:
            return False
            
        favorite = self.favorites[channel_url]
        
        # Update old category count
        if favorite.custom_category and favorite.custom_category in self.custom_categories:
            self.custom_categories[favorite.custom_category].channel_count -= 1
        
        # Update new category count
        if category_name and category_name in self.custom_categories:
            self.custom_categories[category_name].channel_count += 1
        
        favorite.custom_category = category_name
        self._save_data()
        return True
    
    def start_watching(self, channel_name: str, channel_url: str):
        """Start tracking viewing session."""
        if self.current_watching:
            # End previous session
            self.stop_watching()
        
        self.current_watching = WatchHistoryEntry(
            channel_name=channel_name,
            channel_url=channel_url,
            start_time=datetime.now().isoformat()
        )
    
    def stop_watching(self):
        """Stop tracking current viewing session."""
        if not self.current_watching:
            return
            
        # Calculate duration
        start_time = datetime.fromisoformat(self.current_watching.start_time)
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.current_watching.end_time = end_time.isoformat()
        self.current_watching.duration_seconds = int(duration.total_seconds())
        
        # Only save if watched for more than 30 seconds
        if self.current_watching.duration_seconds >= 30:
            self.watch_history.append(self.current_watching)
            
            # Update favorite watch count
            if self.current_watching.channel_url in self.favorites:
                favorite = self.favorites[self.current_watching.channel_url]
                favorite.watch_count += 1
                favorite.last_watched = self.current_watching.start_time
            
            # Limit history size (keep last 1000 entries)
            if len(self.watch_history) > 1000:
                self.watch_history = self.watch_history[-1000:]
            
            self._save_data()
            self.watch_history_updated.emit(self.current_watching.channel_name)
        
        self.current_watching = None
    
    def get_watch_history(self, days: int = 30) -> List[WatchHistoryEntry]:
        """Get watch history for the last N days."""
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        recent_history = []
        for entry in self.watch_history:
            entry_date = datetime.fromisoformat(entry.date).date()
            if entry_date >= cutoff_date:
                recent_history.append(entry)
        
        # Sort by most recent first
        recent_history.sort(key=lambda e: e.start_time, reverse=True)
        return recent_history
    
    def get_viewing_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get viewing statistics."""
        recent_history = self.get_watch_history(days)
        
        if not recent_history:
            return {
                "total_watch_time": 0,
                "total_sessions": 0,
                "average_session_length": 0,
                "most_watched_channels": [],
                "viewing_by_day": {}
            }
        
        # Calculate stats
        total_watch_time = sum(entry.duration_seconds for entry in recent_history)
        total_sessions = len(recent_history)
        average_session_length = total_watch_time / total_sessions if total_sessions > 0 else 0
        
        # Most watched channels
        channel_counts = Counter(entry.channel_name for entry in recent_history)
        most_watched = channel_counts.most_common(10)
        
        # Viewing by day
        viewing_by_day = defaultdict(int)
        for entry in recent_history:
            date = entry.date
            viewing_by_day[date] += entry.duration_seconds
        
        return {
            "total_watch_time": total_watch_time,
            "total_sessions": total_sessions,
            "average_session_length": average_session_length,
            "most_watched_channels": most_watched,
            "viewing_by_day": dict(viewing_by_day)
        }
    
    def get_recommendations(self, limit: int = 10) -> List[str]:
        """Get channel recommendations based on viewing history."""
        # Simple recommendation based on categories of watched channels
        recent_history = self.get_watch_history(7)  # Last week
        
        if not recent_history:
            return []
        
        # Count categories from recent viewing
        category_counts = Counter()
        for entry in recent_history:
            if entry.channel_url in self.favorites:
                favorite = self.favorites[entry.channel_url]
                category_counts[favorite.category] += 1
        
        # Get top categories
        top_categories = [cat for cat, _ in category_counts.most_common(3)]
        
        # Find unwatched channels in these categories
        watched_urls = {entry.channel_url for entry in recent_history}
        recommendations = []
        
        for favorite in self.favorites.values():
            if (favorite.url not in watched_urls and 
                favorite.category in top_categories and
                len(recommendations) < limit):
                recommendations.append(favorite.name)
        
        return recommendations
    
    def export_favorites(self, file_path: str, format: str = "json") -> bool:
        """Export favorites to file."""
        try:
            if format.lower() == "json":
                export_data = {
                    "favorites": [fav.to_dict() for fav in self.favorites.values()],
                    "custom_categories": [cat.to_dict() for cat in self.custom_categories.values()],
                    "export_date": datetime.now().isoformat()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
            elif format.lower() == "m3u":
                # Export as M3U playlist
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for favorite in self.favorites.values():
                        f.write(f"#EXTINF:-1 tvg-id=\"{favorite.tvg_id}\" ")
                        f.write(f"tvg-logo=\"{favorite.tvg_logo}\" ")
                        f.write(f"group-title=\"{favorite.custom_category or favorite.category}\",")
                        f.write(f"{favorite.name}\n")
                        f.write(f"{favorite.url}\n")
            
            return True
            
        except Exception as e:
            print(f"Error exporting favorites: {e}")
            return False
    
    def import_favorites(self, file_path: str) -> bool:
        """Import favorites from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Import favorites
            if "favorites" in data:
                for fav_data in data["favorites"]:
                    favorite = FavoriteChannel.from_dict(fav_data)
                    self.favorites[favorite.url] = favorite
            
            # Import custom categories
            if "custom_categories" in data:
                for cat_data in data["custom_categories"]:
                    category = CustomCategory.from_dict(cat_data)
                    self.custom_categories[category.name] = category
            
            self._save_data()
            return True
            
        except Exception as e:
            print(f"Error importing favorites: {e}")
            return False
    
    def _create_default_categories(self):
        """Create default custom categories if they don't exist."""
        default_categories = [
            ("Recently Added", "Recently added favorites", "#e74c3c"),
            ("Top Rated", "Highest rated channels", "#f39c12"),
            ("Most Watched", "Most frequently watched", "#27ae60"),
        ]
        
        for name, description, color in default_categories:
            if name not in self.custom_categories:
                self.create_custom_category(name, description, color)
    
    def _get_data_file_path(self) -> str:
        """Get the path to the favorites data file."""
        return self.settings_manager._get_settings_filepath("favorites.json")
    
    def _load_data(self):
        """Load favorites data from file."""
        data_file = self._get_data_file_path()
        
        if not os.path.exists(data_file):
            return
            
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load favorites
            if "favorites" in data:
                for fav_data in data["favorites"]:
                    favorite = FavoriteChannel.from_dict(fav_data)
                    self.favorites[favorite.url] = favorite
            
            # Load custom categories
            if "custom_categories" in data:
                for cat_data in data["custom_categories"]:
                    category = CustomCategory.from_dict(cat_data)
                    self.custom_categories[category.name] = category
            
            # Load watch history
            if "watch_history" in data:
                for hist_data in data["watch_history"]:
                    entry = WatchHistoryEntry.from_dict(hist_data)
                    self.watch_history.append(entry)
                    
        except Exception as e:
            print(f"Error loading favorites data: {e}")
    
    def _save_data(self):
        """Save favorites data to file."""
        data_file = self._get_data_file_path()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        try:
            data = {
                "favorites": [fav.to_dict() for fav in self.favorites.values()],
                "custom_categories": [cat.to_dict() for cat in self.custom_categories.values()],
                "watch_history": [entry.to_dict() for entry in self.watch_history],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving favorites data: {e}")
