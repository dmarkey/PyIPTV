"""
Advanced search and filtering system for PyIPTV.

This module provides comprehensive search functionality including:
- Multi-criteria search (name, category, language, quality)
- Fuzzy search with similarity scoring
- Search filters and saved filter presets
- Real-time search suggestions
- Search history and popular searches
"""

import re
import json
from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from PySide6.QtCore import QObject, Signal
from difflib import SequenceMatcher


class SearchType(Enum):
    """Search type enumeration."""
    EXACT = "exact"
    CONTAINS = "contains"
    FUZZY = "fuzzy"
    REGEX = "regex"


class SortCriteria(Enum):
    """Sort criteria enumeration."""
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    CATEGORY_ASC = "category_asc"
    CATEGORY_DESC = "category_desc"
    RELEVANCE = "relevance"
    RECENTLY_ADDED = "recently_added"
    MOST_WATCHED = "most_watched"


@dataclass
class SearchFilter:
    """Represents search filter criteria."""
    name_query: str = ""
    category_filter: List[str] = field(default_factory=list)
    language_filter: List[str] = field(default_factory=list)
    quality_filter: List[str] = field(default_factory=list)
    country_filter: List[str] = field(default_factory=list)
    favorites_only: bool = False
    min_rating: int = 0
    search_type: SearchType = SearchType.CONTAINS
    case_sensitive: bool = False
    include_description: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["search_type"] = self.search_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchFilter':
        """Create from dictionary."""
        if "search_type" in data:
            data["search_type"] = SearchType(data["search_type"])
        return cls(**data)


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""
    channel: Dict[str, str]
    relevance_score: float
    match_reasons: List[str] = field(default_factory=list)
    
    def __lt__(self, other):
        """For sorting by relevance score."""
        return self.relevance_score < other.relevance_score


@dataclass
class SavedSearchFilter:
    """Represents a saved search filter preset."""
    name: str
    filter: SearchFilter
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "filter": self.filter.to_dict(),
            "created_date": self.created_date,
            "usage_count": self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SavedSearchFilter':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            filter=SearchFilter.from_dict(data["filter"]),
            created_date=data.get("created_date", datetime.now().isoformat()),
            usage_count=data.get("usage_count", 0)
        )


class AdvancedSearch(QObject):
    """Advanced search and filtering engine."""
    
    # Signals
    search_completed = Signal(list)  # List[SearchResult]
    suggestions_updated = Signal(list)  # List[str]
    filter_saved = Signal(str)  # filter_name
    
    def __init__(self, settings_manager, favorites_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.favorites_manager = favorites_manager
        
        # Search data
        self.channels: List[Dict[str, str]] = []
        self.search_history: List[str] = []
        self.saved_filters: Dict[str, SavedSearchFilter] = {}
        self.popular_searches: Dict[str, int] = {}
        
        # Search cache for performance
        self._search_cache: Dict[str, List[SearchResult]] = {}
        self._cache_max_size = 100
        
        # Load saved data
        self._load_search_data()
        
        # Language and country mappings
        self.language_codes = self._load_language_codes()
        self.country_codes = self._load_country_codes()
    
    def set_channels(self, channels: List[Dict[str, str]]):
        """Set the channels to search through."""
        self.channels = channels
        self._clear_cache()
    
    def search(self, filter: SearchFilter, sort_by: SortCriteria = SortCriteria.RELEVANCE) -> List[SearchResult]:
        """Perform advanced search with the given filter."""
        # Check cache first
        cache_key = self._get_cache_key(filter, sort_by)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        results = []
        
        for channel in self.channels:
            # Apply filters
            if self._matches_filter(channel, filter):
                relevance_score, match_reasons = self._calculate_relevance(channel, filter)
                
                result = SearchResult(
                    channel=channel,
                    relevance_score=relevance_score,
                    match_reasons=match_reasons
                )
                results.append(result)
        
        # Sort results
        results = self._sort_results(results, sort_by)
        
        # Cache results
        self._cache_results(cache_key, results)
        
        # Update search history
        if filter.name_query:
            self._add_to_search_history(filter.name_query)
        
        self.search_completed.emit(results)
        return results
    
    def search_by_name(self, query: str, search_type: SearchType = SearchType.CONTAINS) -> List[SearchResult]:
        """Quick search by channel name."""
        filter = SearchFilter(name_query=query, search_type=search_type)
        return self.search(filter)
    
    def search_by_category(self, categories: List[str]) -> List[SearchResult]:
        """Search by categories."""
        filter = SearchFilter(category_filter=categories)
        return self.search(filter)
    
    def search_by_language(self, languages: List[str]) -> List[SearchResult]:
        """Search by languages."""
        filter = SearchFilter(language_filter=languages)
        return self.search(filter)
    
    def get_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = set()
        
        # Add suggestions from channel names
        for channel in self.channels:
            name = channel.get("name", "").lower()
            if partial_query.lower() in name:
                suggestions.add(channel.get("name", ""))
        
        # Add suggestions from search history
        for query in self.search_history:
            if partial_query.lower() in query.lower():
                suggestions.add(query)
        
        # Add suggestions from popular searches
        for query in self.popular_searches.keys():
            if partial_query.lower() in query.lower():
                suggestions.add(query)
        
        # Sort by relevance and limit
        suggestions_list = list(suggestions)[:limit]
        
        self.suggestions_updated.emit(suggestions_list)
        return suggestions_list
    
    def get_available_categories(self) -> List[str]:
        """Get all available categories from channels."""
        categories = set()
        for channel in self.channels:
            category = channel.get("group-title", "").strip()
            if category:
                categories.add(category)
        return sorted(list(categories))
    
    def get_available_languages(self) -> List[str]:
        """Get all available languages from channels."""
        languages = set()
        for channel in self.channels:
            # Try to extract language from various fields
            name = channel.get("name", "").lower()
            
            # Look for language indicators in channel name
            for lang_code, lang_name in self.language_codes.items():
                if lang_code in name or lang_name.lower() in name:
                    languages.add(lang_name)
        
        return sorted(list(languages))
    
    def get_available_countries(self) -> List[str]:
        """Get all available countries from channels."""
        countries = set()
        for channel in self.channels:
            name = channel.get("name", "").lower()
            
            # Look for country indicators in channel name
            for country_code, country_name in self.country_codes.items():
                if country_code.lower() in name or country_name.lower() in name:
                    countries.add(country_name)
        
        return sorted(list(countries))
    
    def save_filter(self, name: str, filter: SearchFilter) -> bool:
        """Save a search filter preset."""
        if name in self.saved_filters:
            return False
        
        saved_filter = SavedSearchFilter(name=name, filter=filter)
        self.saved_filters[name] = saved_filter
        
        self._save_search_data()
        self.filter_saved.emit(name)
        return True
    
    def load_filter(self, name: str) -> Optional[SearchFilter]:
        """Load a saved search filter."""
        if name in self.saved_filters:
            saved_filter = self.saved_filters[name]
            saved_filter.usage_count += 1
            self._save_search_data()
            return saved_filter.filter
        return None
    
    def delete_filter(self, name: str) -> bool:
        """Delete a saved search filter."""
        if name in self.saved_filters:
            del self.saved_filters[name]
            self._save_search_data()
            return True
        return False
    
    def get_saved_filters(self) -> List[SavedSearchFilter]:
        """Get all saved search filters."""
        return list(self.saved_filters.values())
    
    def get_popular_searches(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get popular search queries."""
        sorted_searches = sorted(
            self.popular_searches.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_searches[:limit]
    
    def clear_search_history(self):
        """Clear search history."""
        self.search_history.clear()
        self._save_search_data()
    
    def _matches_filter(self, channel: Dict[str, str], filter: SearchFilter) -> bool:
        """Check if channel matches the search filter."""
        # Name query filter
        if filter.name_query:
            if not self._matches_name_query(channel, filter):
                return False
        
        # Category filter
        if filter.category_filter:
            channel_category = channel.get("group-title", "").strip()
            if channel_category not in filter.category_filter:
                return False
        
        # Language filter
        if filter.language_filter:
            if not self._matches_language_filter(channel, filter.language_filter):
                return False
        
        # Country filter
        if filter.country_filter:
            if not self._matches_country_filter(channel, filter.country_filter):
                return False
        
        # Favorites filter
        if filter.favorites_only and self.favorites_manager:
            channel_url = channel.get("url", "")
            if not self.favorites_manager.is_favorite(channel_url):
                return False
        
        # Rating filter
        if filter.min_rating > 0 and self.favorites_manager:
            channel_url = channel.get("url", "")
            if channel_url in self.favorites_manager.favorites:
                favorite = self.favorites_manager.favorites[channel_url]
                if favorite.rating < filter.min_rating:
                    return False
            else:
                return False  # Not in favorites, so no rating
        
        return True
    
    def _matches_name_query(self, channel: Dict[str, str], filter: SearchFilter) -> bool:
        """Check if channel matches name query."""
        query = filter.name_query
        if not filter.case_sensitive:
            query = query.lower()
        
        # Get searchable text
        searchable_fields = ["name"]
        if filter.include_description:
            searchable_fields.extend(["tvg-name", "group-title"])
        
        searchable_text = " ".join(
            channel.get(field, "") for field in searchable_fields
        )
        
        if not filter.case_sensitive:
            searchable_text = searchable_text.lower()
        
        # Apply search type
        if filter.search_type == SearchType.EXACT:
            return query == searchable_text.strip()
        elif filter.search_type == SearchType.CONTAINS:
            return query in searchable_text
        elif filter.search_type == SearchType.FUZZY:
            # Use fuzzy matching with threshold
            similarity = SequenceMatcher(None, query, searchable_text).ratio()
            return similarity >= 0.6  # 60% similarity threshold
        elif filter.search_type == SearchType.REGEX:
            try:
                pattern = re.compile(query, re.IGNORECASE if not filter.case_sensitive else 0)
                return bool(pattern.search(searchable_text))
            except re.error:
                return False
        
        return False
    
    def _matches_language_filter(self, channel: Dict[str, str], languages: List[str]) -> bool:
        """Check if channel matches language filter."""
        channel_name = channel.get("name", "").lower()
        
        for language in languages:
            # Check if language name or code is in channel name
            if language.lower() in channel_name:
                return True
            
            # Check language codes
            for code, name in self.language_codes.items():
                if name == language and code in channel_name:
                    return True
        
        return False
    
    def _matches_country_filter(self, channel: Dict[str, str], countries: List[str]) -> bool:
        """Check if channel matches country filter."""
        channel_name = channel.get("name", "").lower()
        
        for country in countries:
            # Check if country name is in channel name
            if country.lower() in channel_name:
                return True
            
            # Check country codes
            for code, name in self.country_codes.items():
                if name == country and code.lower() in channel_name:
                    return True
        
        return False
    
    def _calculate_relevance(self, channel: Dict[str, str], filter: SearchFilter) -> Tuple[float, List[str]]:
        """Calculate relevance score for a channel."""
        score = 0.0
        reasons = []
        
        # Name match scoring
        if filter.name_query:
            name = channel.get("name", "").lower()
            query = filter.name_query.lower()
            
            if query == name:
                score += 100
                reasons.append("Exact name match")
            elif name.startswith(query):
                score += 80
                reasons.append("Name starts with query")
            elif query in name:
                score += 60
                reasons.append("Name contains query")
            
            # Fuzzy match bonus
            similarity = SequenceMatcher(None, query, name).ratio()
            score += similarity * 20
        
        # Category match bonus
        if filter.category_filter:
            category = channel.get("group-title", "")
            if category in filter.category_filter:
                score += 30
                reasons.append(f"Category: {category}")
        
        # Favorites bonus
        if self.favorites_manager:
            channel_url = channel.get("url", "")
            if self.favorites_manager.is_favorite(channel_url):
                score += 25
                reasons.append("Favorite channel")
                
                # Rating bonus
                favorite = self.favorites_manager.favorites[channel_url]
                if favorite.rating > 0:
                    score += favorite.rating * 5
                    reasons.append(f"Rating: {favorite.rating}/5")
                
                # Watch count bonus
                if favorite.watch_count > 0:
                    score += min(favorite.watch_count * 2, 20)
                    reasons.append(f"Watched {favorite.watch_count} times")
        
        return score, reasons
    
    def _sort_results(self, results: List[SearchResult], sort_by: SortCriteria) -> List[SearchResult]:
        """Sort search results by criteria."""
        if sort_by == SortCriteria.RELEVANCE:
            results.sort(key=lambda r: r.relevance_score, reverse=True)
        elif sort_by == SortCriteria.NAME_ASC:
            results.sort(key=lambda r: r.channel.get("name", "").lower())
        elif sort_by == SortCriteria.NAME_DESC:
            results.sort(key=lambda r: r.channel.get("name", "").lower(), reverse=True)
        elif sort_by == SortCriteria.CATEGORY_ASC:
            results.sort(key=lambda r: r.channel.get("group-title", "").lower())
        elif sort_by == SortCriteria.CATEGORY_DESC:
            results.sort(key=lambda r: r.channel.get("group-title", "").lower(), reverse=True)
        elif sort_by == SortCriteria.MOST_WATCHED and self.favorites_manager:
            # Sort by watch count for favorites
            def get_watch_count(result):
                url = result.channel.get("url", "")
                if url in self.favorites_manager.favorites:
                    return self.favorites_manager.favorites[url].watch_count
                return 0
            results.sort(key=get_watch_count, reverse=True)
        
        return results
    
    def _add_to_search_history(self, query: str):
        """Add query to search history."""
        # Remove if already exists
        if query in self.search_history:
            self.search_history.remove(query)
        
        # Add to beginning
        self.search_history.insert(0, query)
        
        # Limit history size
        if len(self.search_history) > 50:
            self.search_history = self.search_history[:50]
        
        # Update popular searches
        self.popular_searches[query] = self.popular_searches.get(query, 0) + 1
        
        self._save_search_data()
    
    def _get_cache_key(self, filter: SearchFilter, sort_by: SortCriteria) -> str:
        """Generate cache key for search results."""
        filter_str = json.dumps(filter.to_dict(), sort_keys=True)
        return f"{filter_str}_{sort_by.value}"
    
    def _cache_results(self, key: str, results: List[SearchResult]):
        """Cache search results."""
        if len(self._search_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._search_cache))
            del self._search_cache[oldest_key]
        
        self._search_cache[key] = results
    
    def _clear_cache(self):
        """Clear search cache."""
        self._search_cache.clear()
    
    def _load_language_codes(self) -> Dict[str, str]:
        """Load language codes mapping."""
        # Simplified language codes - in real implementation, load from file
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "nl": "Dutch"
        }
    
    def _load_country_codes(self) -> Dict[str, str]:
        """Load country codes mapping."""
        # Simplified country codes - in real implementation, load from file
        return {
            "US": "United States",
            "UK": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia",
            "DE": "Germany",
            "FR": "France",
            "ES": "Spain",
            "IT": "Italy",
            "BR": "Brazil",
            "MX": "Mexico",
            "RU": "Russia",
            "CN": "China",
            "JP": "Japan",
            "KR": "South Korea",
            "IN": "India",
            "TR": "Turkey"
        }
    
    def _get_search_data_file(self) -> str:
        """Get path to search data file."""
        return self.settings_manager._get_settings_filepath("search_data.json")
    
    def _load_search_data(self):
        """Load search data from file."""
        data_file = self._get_search_data_file()
        
        if not os.path.exists(data_file):
            return
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.search_history = data.get("search_history", [])
            self.popular_searches = data.get("popular_searches", {})
            
            # Load saved filters
            if "saved_filters" in data:
                for filter_data in data["saved_filters"]:
                    saved_filter = SavedSearchFilter.from_dict(filter_data)
                    self.saved_filters[saved_filter.name] = saved_filter
                    
        except Exception as e:
            print(f"Error loading search data: {e}")
    
    def _save_search_data(self):
        """Save search data to file."""
        data_file = self._get_search_data_file()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        try:
            data = {
                "search_history": self.search_history,
                "popular_searches": self.popular_searches,
                "saved_filters": [filter.to_dict() for filter in self.saved_filters.values()],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving search data: {e}")
