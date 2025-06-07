#!/usr/bin/env python3
"""
Test script for PyIPTV geolocation-based subtitle features
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pyiptv.geolocation_manager import GeolocationManager, CountryLanguageMapper
from pyiptv.enhanced_subtitle_manager import EnhancedSubtitleManager, SubtitleTrackInfo
from pyiptv.settings_manager import SettingsManager


def test_country_language_mapper():
    """Test the country to language mapping."""
    print("Testing Country Language Mapper...")
    print("-" * 40)
    
    # Test some countries
    test_countries = [
        ('TN', 'Tunisia'),
        ('FR', 'France'), 
        ('DE', 'Germany'),
        ('SA', 'Saudi Arabia'),
        ('US', 'United States'),
        ('CN', 'China'),
        ('JP', 'Japan'),
        ('ES', 'Spain'),
        ('IT', 'Italy'),
        ('RU', 'Russia')
    ]
    
    for country_code, country_name in test_countries:
        languages = CountryLanguageMapper.get_preferred_languages(country_code)
        lang_names = [CountryLanguageMapper.get_language_name(lang) for lang in languages]
        print(f"{country_name} ({country_code}): {', '.join(lang_names)} ({', '.join(languages)})")
    
    print("✅ Country Language Mapper test completed\n")


def test_geolocation_manager():
    """Test the geolocation manager."""
    print("Testing Geolocation Manager...")
    print("-" * 40)
    
    # Create settings manager
    settings_manager = SettingsManager()
    
    # Create geolocation manager
    geo_manager = GeolocationManager(settings_manager)
    
    # Test manual location detection
    print("Starting location detection...")
    geo_manager.detect_location()
    
    # Wait a bit for detection to complete
    import time
    time.sleep(3)
    
    # Check results
    location = geo_manager.get_location_info()
    if location and location.is_valid:
        print(f"✅ Location detected:")
        print(f"   Country: {location.country_name} ({location.country_code})")
        print(f"   City: {location.city}")
        print(f"   Region: {location.region}")
        print(f"   Coordinates: {location.latitude:.4f}, {location.longitude:.4f}")
        
        # Test preferred languages
        preferred_langs = geo_manager.get_preferred_languages()
        lang_names = [CountryLanguageMapper.get_language_name(lang) for lang in preferred_langs]
        print(f"   Preferred languages: {', '.join(lang_names)} ({', '.join(preferred_langs)})")
    else:
        print("❌ Location detection failed or not completed")
    
    print("✅ Geolocation Manager test completed\n")


def test_enhanced_subtitle_manager():
    """Test the enhanced subtitle manager."""
    print("Testing Enhanced Subtitle Manager...")
    print("-" * 40)
    
    # Create settings manager
    settings_manager = SettingsManager()
    
    # Create enhanced subtitle manager
    subtitle_manager = EnhancedSubtitleManager(settings_manager)
    
    # Simulate subtitle tracks
    test_tracks = [
        {
            'language': 'en',
            'language_name': 'English',
            'title': 'English Subtitles',
            'is_default': True,
            'is_forced': False
        },
        {
            'language': 'fr',
            'language_name': 'French',
            'title': 'Français',
            'is_default': False,
            'is_forced': False
        },
        {
            'language': 'ar',
            'language_name': 'Arabic',
            'title': 'العربية',
            'is_default': False,
            'is_forced': False
        },
        {
            'language': '',
            'language_name': '',
            'title': 'Spanish Subtitles',
            'is_default': False,
            'is_forced': False
        }
    ]
    
    # Test track detection
    media_info = {'subtitle_streams': test_tracks}
    detected_tracks = subtitle_manager.detect_subtitle_tracks(media_info)
    
    print(f"Detected {len(detected_tracks)} subtitle tracks:")
    for i, track in enumerate(detected_tracks):
        print(f"  {i}: {track}")
    
    # Test language detection from title
    test_titles = [
        "English Subtitles",
        "Français",
        "العربية", 
        "Spanish Subtitles",
        "Deutsch",
        "Italiano",
        "中文字幕",
        "日本語字幕"
    ]
    
    print("\nLanguage detection from titles:")
    for title in test_titles:
        detected_lang = subtitle_manager._detect_language_from_title(title)
        if detected_lang:
            lang_name = CountryLanguageMapper.get_language_name(detected_lang)
            print(f"  '{title}' -> {lang_name} ({detected_lang})")
        else:
            print(f"  '{title}' -> Not detected")
    
    print("✅ Enhanced Subtitle Manager test completed\n")


def test_manual_language_preferences():
    """Test manual language preference setting."""
    print("Testing Manual Language Preferences...")
    print("-" * 40)
    
    settings_manager = SettingsManager()
    subtitle_manager = EnhancedSubtitleManager(settings_manager)
    
    # Test setting manual preferences
    manual_langs = ['ar', 'fr', 'en']
    subtitle_manager.set_manual_language_preference(manual_langs)
    
    current_prefs = subtitle_manager.get_preferred_languages()
    lang_names = [CountryLanguageMapper.get_language_name(lang) for lang in current_prefs]
    
    print(f"Set manual preferences: {', '.join(lang_names)} ({', '.join(current_prefs)})")
    
    # Test with different preferences
    manual_langs2 = ['zh', 'ja', 'en']
    subtitle_manager.set_manual_language_preference(manual_langs2)
    
    current_prefs2 = subtitle_manager.get_preferred_languages()
    lang_names2 = [CountryLanguageMapper.get_language_name(lang) for lang in current_prefs2]
    
    print(f"Updated preferences: {', '.join(lang_names2)} ({', '.join(current_prefs2)})")
    
    print("✅ Manual Language Preferences test completed\n")


def test_subtitle_track_scoring():
    """Test subtitle track scoring algorithm."""
    print("Testing Subtitle Track Scoring...")
    print("-" * 40)
    
    settings_manager = SettingsManager()
    subtitle_manager = EnhancedSubtitleManager(settings_manager)
    
    # Create test tracks
    tracks = [
        SubtitleTrackInfo(0, 'en', 'English', 'English Subtitles', True, False),
        SubtitleTrackInfo(1, 'fr', 'French', 'Français', False, False),
        SubtitleTrackInfo(2, 'ar', 'Arabic', 'العربية', False, False),
        SubtitleTrackInfo(3, 'es', 'Spanish', 'Español', False, True),  # Forced
        SubtitleTrackInfo(4, 'de', 'German', 'Deutsch', False, False),
    ]
    
    # Test different language preferences
    test_preferences = [
        ['ar', 'fr', 'en'],  # Arabic first
        ['fr', 'en'],        # French first
        ['en'],              # English only
        ['zh', 'ja'],        # Languages not available
    ]
    
    for prefs in test_preferences:
        print(f"\nPreferences: {', '.join(prefs)}")
        
        scores = []
        for track in tracks:
            score = subtitle_manager._calculate_track_score(track, prefs)
            scores.append((score, track))
        
        # Sort by score (highest first)
        scores.sort(key=lambda x: x[0], reverse=True)
        
        print("Track scores:")
        for score, track in scores:
            print(f"  {score:3d}: {track}")
        
        # Find best track
        best_track = subtitle_manager._find_best_subtitle_track(prefs)
        if best_track:
            print(f"Best track: {best_track}")
        else:
            print("No suitable track found")
    
    print("\n✅ Subtitle Track Scoring test completed\n")


def main():
    """Run all tests."""
    print("🌍 Testing PyIPTV Geolocation-based Subtitle Features")
    print("=" * 60)
    
    try:
        test_country_language_mapper()
        test_enhanced_subtitle_manager()
        test_manual_language_preferences()
        test_subtitle_track_scoring()
        
        # Note: Geolocation test requires internet connection
        print("🌐 Testing live geolocation (requires internet)...")
        test_geolocation_manager()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
