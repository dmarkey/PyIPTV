#!/usr/bin/env python3
"""
Enhanced Subtitle Manager for PyIPTV

This module extends the basic subtitle manager with geolocation-based
automatic subtitle track selection and enhanced language management.
"""

import re
from typing import List, Dict, Optional, Tuple
from PySide6.QtCore import QObject, Signal

from pyiptv.subtitle_manager import SubtitleManager
from pyiptv.geolocation_manager import GeolocationManager, CountryLanguageMapper


class SubtitleTrackInfo:
    """Information about a subtitle track."""
    
    def __init__(self, index: int, language_code: str = "", language_name: str = "", 
                 title: str = "", is_default: bool = False, is_forced: bool = False):
        self.index = index
        self.language_code = language_code.lower()
        self.language_name = language_name
        self.title = title
        self.is_default = is_default
        self.is_forced = is_forced
        
    def __str__(self):
        parts = []
        if self.language_name:
            parts.append(self.language_name)
        elif self.language_code:
            parts.append(self.language_code.upper())
        
        if self.title and self.title != self.language_name:
            parts.append(f"({self.title})")
            
        if self.is_default:
            parts.append("[Default]")
        if self.is_forced:
            parts.append("[Forced]")
            
        return " ".join(parts) if parts else f"Track {self.index}"


class EnhancedSubtitleManager(QObject):
    """Enhanced subtitle manager with geolocation-based auto-selection."""
    
    # Signals
    subtitle_tracks_detected = Signal(list)  # List of SubtitleTrackInfo
    auto_track_selected = Signal(int, str)  # track_index, reason
    manual_track_selected = Signal(int)  # track_index
    geolocation_status_changed = Signal(str)  # status message
    
    def __init__(self, settings_manager, base_subtitle_manager: SubtitleManager = None):
        super().__init__()
        self.settings_manager = settings_manager
        self.base_subtitle_manager = base_subtitle_manager or SubtitleManager()
        
        # Initialize geolocation manager
        self.geolocation_manager = GeolocationManager(settings_manager)
        self.geolocation_manager.location_updated.connect(self._on_location_updated)
        self.geolocation_manager.preferred_languages_changed.connect(self._on_preferred_languages_changed)
        
        # Current subtitle tracks
        self.available_tracks: List[SubtitleTrackInfo] = []
        self.current_track_index = -1
        self.preferred_languages = ['en']
        
        # Language detection patterns
        self.language_patterns = self._build_language_patterns()
        
    def _build_language_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for language detection in track titles."""
        return {
            'ar': [r'\barabic?\b', r'\bعربي\b', r'\bعرب\b', r'\bar\b'],
            'en': [r'\benglish?\b', r'\beng?\b', r'\ben\b'],
            'fr': [r'\bfrench?\b', r'\bfrançais?\b', r'\bfra?\b', r'\bfr\b'],
            'de': [r'\bgerman?\b', r'\bdeutsch?\b', r'\bger?\b', r'\bde\b'],
            'es': [r'\bspanish?\b', r'\bespañol?\b', r'\besp?\b', r'\bes\b'],
            'it': [r'\bitalian?\b', r'\bitaliano?\b', r'\bita?\b', r'\bit\b'],
            'pt': [r'\bportuguese?\b', r'\bportuguês?\b', r'\bpor?\b', r'\bpt\b'],
            'ru': [r'\brussian?\b', r'\bрусский?\b', r'\brus?\b', r'\bru\b'],
            'zh': [r'\bchinese?\b', r'\b中文?\b', r'\bchi?\b', r'\bzh\b'],
            'ja': [r'\bjapanese?\b', r'\b日本語?\b', r'\bjpn?\b', r'\bja\b'],
            'ko': [r'\bkorean?\b', r'\b한국어?\b', r'\bkor?\b', r'\bko\b'],
            'hi': [r'\bhindi?\b', r'\bहिन्दी?\b', r'\bhin?\b', r'\bhi\b'],
            'th': [r'\bthai?\b', r'\bไทย?\b', r'\btha?\b', r'\bth\b'],
            'vi': [r'\bvietnamese?\b', r'\btiếng việt?\b', r'\bvie?\b', r'\bvi\b'],
            'tr': [r'\bturkish?\b', r'\btürkçe?\b', r'\btur?\b', r'\btr\b'],
            'pl': [r'\bpolish?\b', r'\bpolski?\b', r'\bpol?\b', r'\bpl\b'],
            'nl': [r'\bdutch?\b', r'\bnederlands?\b', r'\bnld?\b', r'\bnl\b'],
            'sv': [r'\bswedish?\b', r'\bsvenska?\b', r'\bswe?\b', r'\bsv\b'],
            'no': [r'\bnorwegian?\b', r'\bnorsk?\b', r'\bnor?\b', r'\bno\b'],
            'da': [r'\bdanish?\b', r'\bdansk?\b', r'\bdan?\b', r'\bda\b'],
            'fi': [r'\bfinnish?\b', r'\bsuomi?\b', r'\bfin?\b', r'\bfi\b'],
            'el': [r'\bgreek?\b', r'\bελληνικά?\b', r'\bgre?\b', r'\bel\b'],
            'he': [r'\bhebrew?\b', r'\bעברית?\b', r'\bheb?\b', r'\bhe\b'],
            'cs': [r'\bczech?\b', r'\bčeština?\b', r'\bcze?\b', r'\bcs\b'],
            'sk': [r'\bslovak?\b', r'\bslovenčina?\b', r'\bslk?\b', r'\bsk\b'],
            'hu': [r'\bhungarian?\b', r'\bmagyar?\b', r'\bhun?\b', r'\bhu\b'],
            'ro': [r'\bromanian?\b', r'\bromână?\b', r'\brom?\b', r'\bro\b'],
            'bg': [r'\bbulgarian?\b', r'\bбългарски?\b', r'\bbul?\b', r'\bbg\b'],
            'hr': [r'\bcroatian?\b', r'\bhrvatski?\b', r'\bhrv?\b', r'\bhr\b'],
            'sr': [r'\bserbian?\b', r'\bсрпски?\b', r'\bsrp?\b', r'\bsr\b'],
            'sl': [r'\bslovenian?\b', r'\bslovenščina?\b', r'\bslv?\b', r'\bsl\b'],
            'uk': [r'\bukrainian?\b', r'\bукраїнська?\b', r'\bukr?\b', r'\buk\b'],
            'be': [r'\bbelarusian?\b', r'\bбеларуская?\b', r'\bbel?\b', r'\bbe\b'],
            'lt': [r'\blithuanian?\b', r'\blietuvių?\b', r'\blit?\b', r'\blt\b'],
            'lv': [r'\blatvian?\b', r'\blatviešu?\b', r'\blav?\b', r'\blv\b'],
            'et': [r'\bestonian?\b', r'\beesti?\b', r'\best?\b', r'\bet\b'],
        }
    
    def detect_subtitle_tracks(self, media_info: Dict) -> List[SubtitleTrackInfo]:
        """Detect available subtitle tracks from media information."""
        tracks = []
        
        # This would typically come from the media player's metadata
        # For now, we'll simulate track detection
        subtitle_streams = media_info.get('subtitle_streams', [])
        
        for i, stream in enumerate(subtitle_streams):
            track = SubtitleTrackInfo(
                index=i,
                language_code=stream.get('language', ''),
                language_name=stream.get('language_name', ''),
                title=stream.get('title', ''),
                is_default=stream.get('is_default', False),
                is_forced=stream.get('is_forced', False)
            )
            
            # Try to detect language from title if not provided
            if not track.language_code and track.title:
                detected_lang = self._detect_language_from_title(track.title)
                if detected_lang:
                    track.language_code = detected_lang
                    track.language_name = CountryLanguageMapper.get_language_name(detected_lang)
            
            tracks.append(track)
        
        self.available_tracks = tracks
        self.subtitle_tracks_detected.emit(tracks)
        
        # Auto-select track if enabled
        auto_subtitle = self.settings_manager.get_setting("geolocation_auto_subtitle")
        if auto_subtitle is None or auto_subtitle:
            self._auto_select_subtitle_track()
        
        return tracks
    
    def _detect_language_from_title(self, title: str) -> Optional[str]:
        """Detect language code from subtitle track title."""
        title_lower = title.lower()
        
        for lang_code, patterns in self.language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title_lower, re.IGNORECASE):
                    return lang_code
        
        return None
    
    def _auto_select_subtitle_track(self):
        """Automatically select the best subtitle track based on preferences."""
        if not self.available_tracks:
            return
        
        # Get preferred languages from geolocation
        preferred_langs = self.geolocation_manager.get_preferred_languages()
        
        # Check for manual override
        manual_langs = self.settings_manager.get_setting("manual_subtitle_languages")
        if manual_langs:
            preferred_langs = manual_langs
        
        # Find best matching track
        best_track = self._find_best_subtitle_track(preferred_langs)
        
        if best_track is not None:
            self.select_subtitle_track(best_track.index, auto_selected=True)
            
            # Determine selection reason
            reason = self._get_selection_reason(best_track, preferred_langs)
            self.auto_track_selected.emit(best_track.index, reason)
    
    def _find_best_subtitle_track(self, preferred_languages: List[str]) -> Optional[SubtitleTrackInfo]:
        """Find the best subtitle track based on language preferences."""
        if not self.available_tracks:
            return None
        
        # Score each track
        scored_tracks = []
        
        for track in self.available_tracks:
            score = self._calculate_track_score(track, preferred_languages)
            if score > 0:
                scored_tracks.append((score, track))
        
        if not scored_tracks:
            # No matching tracks, return default or first track
            default_tracks = [t for t in self.available_tracks if t.is_default]
            if default_tracks:
                return default_tracks[0]
            return self.available_tracks[0] if self.available_tracks else None
        
        # Return highest scored track
        scored_tracks.sort(key=lambda x: x[0], reverse=True)
        return scored_tracks[0][1]
    
    def _calculate_track_score(self, track: SubtitleTrackInfo, preferred_languages: List[str]) -> int:
        """Calculate a score for a subtitle track based on preferences."""
        score = 0
        
        # Language preference score (higher for earlier in preference list)
        if track.language_code in preferred_languages:
            lang_index = preferred_languages.index(track.language_code)
            score += (len(preferred_languages) - lang_index) * 100
        
        # Bonus for default track
        if track.is_default:
            score += 50
        
        # Penalty for forced subtitles (usually for foreign language parts only)
        if track.is_forced:
            score -= 25
        
        # Bonus for having proper language name
        if track.language_name:
            score += 10
        
        return score
    
    def _get_selection_reason(self, track: SubtitleTrackInfo, preferred_languages: List[str]) -> str:
        """Get human-readable reason for track selection."""
        if track.language_code in preferred_languages:
            lang_name = CountryLanguageMapper.get_language_name(track.language_code)
            location = self.geolocation_manager.get_location_info()
            if location and location.is_valid:
                return f"Auto-selected {lang_name} based on location: {location.country_name}"
            else:
                return f"Auto-selected {lang_name} based on preferences"
        elif track.is_default:
            return "Auto-selected default subtitle track"
        else:
            return "Auto-selected first available subtitle track"
    
    def select_subtitle_track(self, track_index: int, auto_selected: bool = False):
        """Select a subtitle track by index."""
        if 0 <= track_index < len(self.available_tracks):
            self.current_track_index = track_index
            
            # Apply selection to base subtitle manager
            if self.base_subtitle_manager:
                # This would depend on the base subtitle manager's API
                # For now, we'll just store the selection
                pass
            
            if not auto_selected:
                self.manual_track_selected.emit(track_index)
    
    def get_available_tracks(self) -> List[SubtitleTrackInfo]:
        """Get list of available subtitle tracks."""
        return self.available_tracks.copy()
    
    def get_current_track(self) -> Optional[SubtitleTrackInfo]:
        """Get currently selected subtitle track."""
        if 0 <= self.current_track_index < len(self.available_tracks):
            return self.available_tracks[self.current_track_index]
        return None
    
    def set_manual_language_preference(self, languages: List[str]):
        """Set manual language preferences (overrides geolocation)."""
        self.geolocation_manager.set_manual_languages(languages)
        
        # Re-select subtitle track with new preferences
        if self.available_tracks and self.settings_manager.get_setting("geolocation_auto_subtitle", True):
            self._auto_select_subtitle_track()
    
    def get_preferred_languages(self) -> List[str]:
        """Get current preferred languages."""
        return self.geolocation_manager.get_preferred_languages()
    
    def get_location_info(self):
        """Get current location information."""
        return self.geolocation_manager.get_location_info()
    
    def is_auto_selection_enabled(self) -> bool:
        """Check if automatic subtitle selection is enabled."""
        auto_subtitle = self.settings_manager.get_setting("geolocation_auto_subtitle")
        return auto_subtitle if auto_subtitle is not None else True

    def set_auto_selection_enabled(self, enabled: bool):
        """Enable or disable automatic subtitle selection."""
        self.settings_manager.set_setting("geolocation_auto_subtitle", enabled)
    
    def refresh_location(self):
        """Manually refresh geolocation."""
        self.geolocation_manager.detect_location()
    
    def _on_location_updated(self, location):
        """Handle location update."""
        location_name = f"{location.city}, {location.country_name}" if location.city else location.country_name
        self.geolocation_status_changed.emit(f"Location updated: {location_name}")
        
        # Re-select subtitle track if auto-selection is enabled
        if (self.available_tracks and 
            self.settings_manager.get_setting("geolocation_auto_subtitle", True)):
            self._auto_select_subtitle_track()
    
    def _on_preferred_languages_changed(self, languages: List[str]):
        """Handle preferred languages change."""
        self.preferred_languages = languages
        
        # Re-select subtitle track if auto-selection is enabled
        if (self.available_tracks and 
            self.settings_manager.get_setting("geolocation_auto_subtitle", True)):
            self._auto_select_subtitle_track()
    
    def cleanup(self):
        """Cleanup resources."""
        if self.geolocation_manager:
            self.geolocation_manager.stop_auto_detection()
