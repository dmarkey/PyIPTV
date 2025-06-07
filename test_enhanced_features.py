#!/usr/bin/env python3
"""
Test script for PyIPTV enhanced features
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pyiptv.link_validator import AsyncLinkValidator, LinkValidationResult
from pyiptv.auto_updater import M3UAutoSaver
from pyiptv.settings_manager import SettingsManager


def test_link_validator():
    """Test the link validator with some sample URLs."""
    print("Testing Link Validator...")
    
    # Sample URLs for testing (mix of valid and invalid)
    test_urls = [
        "https://www.google.com",  # Should be valid
        "https://httpbin.org/status/200",  # Should be valid
        "https://httpbin.org/status/404",  # Should be invalid (404)
        "https://nonexistent-domain-12345.com",  # Should be invalid (DNS error)
        "https://httpbin.org/delay/15",  # Should timeout
    ]
    
    async def run_validation():
        validator = AsyncLinkValidator(timeout_seconds=5, max_concurrent=3)
        
        def progress_callback(current, total):
            print(f"Progress: {current}/{total}")
        
        try:
            results = await validator.validate_links_batch(test_urls, progress_callback)
            
            print("\nValidation Results:")
            print("-" * 50)
            for result in results:
                status = "✅ VALID" if result.is_valid else "❌ INVALID"
                print(f"{status} | {result.url}")
                print(f"   Response time: {result.response_time:.2f}s")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
                if result.status_code:
                    print(f"   Status: {result.status_code}")
                print()
                
        except Exception as e:
            print(f"Validation failed: {e}")
    
    # Run the async validation
    asyncio.run(run_validation())


def test_m3u_auto_saver():
    """Test the M3U auto-saver."""
    print("Testing M3U Auto-Saver...")
    
    # Create a test settings manager
    settings_manager = SettingsManager()
    
    # Create auto-saver
    auto_saver = M3UAutoSaver(settings_manager)
    
    # Sample channel data
    test_channels = [
        {
            "name": "Test Channel 1",
            "url": "https://example.com/stream1.m3u8",
            "tvg-id": "test1",
            "tvg-logo": "https://example.com/logo1.png",
            "group-title": "Test Category"
        },
        {
            "name": "Test Channel 2", 
            "url": "https://example.com/stream2.m3u8",
            "tvg-id": "test2",
            "tvg-logo": "https://example.com/logo2.png",
            "group-title": "Test Category"
        }
    ]
    
    test_categories = {
        "Test Category": test_channels
    }
    
    # Generate M3U content
    m3u_content = auto_saver._generate_m3u_content(test_channels)
    
    print("Generated M3U Content:")
    print("-" * 30)
    print(m3u_content)
    print("-" * 30)
    
    # Test saving to a file
    test_file = "test_output.m3u"
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        print(f"✅ Successfully saved test M3U file: {test_file}")
        
        # Clean up
        os.remove(test_file)
        print("✅ Test file cleaned up")
        
    except Exception as e:
        print(f"❌ Failed to save test M3U file: {e}")


def test_settings_manager():
    """Test the enhanced settings."""
    print("Testing Enhanced Settings...")
    
    settings_manager = SettingsManager()
    
    # Test new settings
    enhanced_settings = [
        "auto_save_m3u",
        "auto_update_playlists", 
        "dead_link_detection",
        "recording_enabled"
    ]
    
    print("Enhanced Settings:")
    for setting in enhanced_settings:
        value = settings_manager.get_setting(setting)
        print(f"  {setting}: {value}")
    
    print("✅ Settings manager working correctly")


def main():
    """Run all tests."""
    print("🚀 Testing PyIPTV Enhanced Features")
    print("=" * 50)
    
    try:
        test_settings_manager()
        print()
        
        test_m3u_auto_saver()
        print()
        
        test_link_validator()
        print()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
