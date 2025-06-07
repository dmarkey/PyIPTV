#!/usr/bin/env python3

"""
Manual FFmpeg setup script for PyIPTV.
Run this if the automatic setup fails.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def manual_ffmpeg_setup():
    """Manually setup FFmpeg for PyIPTV."""
    print("🔧 Manual FFmpeg Setup for PyIPTV")
    print("=" * 40)
    
    try:
        from pyiptv.ffmpeg_manager import FFmpegManager
        
        manager = FFmpegManager()
        print(f"Platform: {manager.system} {manager.arch}")
        print(f"FFmpeg directory: {manager.ffmpeg_dir}")
        
        # Check current status
        has_system = manager.check_system_ffmpeg()
        has_bundled = manager.is_ffmpeg_available()
        
        print(f"\nCurrent Status:")
        print(f"  System FFmpeg: {'✅ Available' if has_system else '❌ Not found'}")
        print(f"  Bundled FFmpeg: {'✅ Available' if has_bundled else '❌ Not found'}")
        
        if has_system or has_bundled:
            print("\n✅ FFmpeg is already available!")
            print("Subtitle detection should work.")
            return True
        
        print(f"\n📥 Attempting to download FFmpeg...")
        
        def progress_callback(percent):
            print(f"Progress: {percent}%")
        
        try:
            result = manager.ensure_ffmpeg(progress_callback)
            print(f"\n✅ FFmpeg setup completed: {result}")
            
            # Verify installation
            if manager.is_ffmpeg_available():
                print("✅ FFmpeg binaries verified")
                print("✅ Subtitle detection is now available!")
                return True
            else:
                print("❌ FFmpeg verification failed")
                return False
                
        except Exception as e:
            print(f"❌ FFmpeg download failed: {e}")
            print("\n🔧 Manual Installation Options:")
            print("1. Download FFmpeg manually from https://ffmpeg.org/download.html")
            print("2. Extract to a folder and add to your PATH")
            print("3. Or install using package manager:")
            print("   - Windows: choco install ffmpeg")
            print("   - Windows: winget install ffmpeg")
            return False
            
    except Exception as e:
        print(f"❌ Error in manual setup: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_subtitle_detection():
    """Test subtitle detection with a sample URL."""
    print("\n🧪 Testing Subtitle Detection...")
    
    try:
        from pyiptv.subtitle_manager import SubtitleManager
        
        manager = SubtitleManager()
        print("✅ SubtitleManager created")
        
        # Test with a dummy URL (will fail but should not crash)
        test_url = "http://example.com/test.mkv"
        print(f"Testing detection with: {test_url}")
        
        try:
            tracks = manager.detect_embedded_tracks(test_url)
            print(f"✅ Detection method works (found {len(tracks)} tracks)")
            print("Note: No tracks found because test URL is not real")
        except Exception as e:
            if "FFmpeg not available" in str(e):
                print("❌ FFmpeg still not available for detection")
                return False
            else:
                print(f"⚠️ Detection failed as expected: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing subtitle detection: {e}")
        return False

def show_usage_guide():
    """Show usage guide after setup."""
    print("\n🎯 HOW TO USE SUBTITLES IN PYIPTV:")
    
    print("\n1. 🚀 Start PyIPTV:")
    print("   python pyiptv/main.py")
    
    print("\n2. 📺 Play media with embedded subtitles:")
    print("   - Load your M3U playlist")
    print("   - Play any channel/video with embedded subs")
    print("   - Watch for status: 'Detected X embedded subtitle tracks'")
    
    print("\n3. 📝 Use the Sub Track button:")
    print("   - Look for 📝 button in control bar")
    print("   - Click dropdown to see available languages")
    print("   - Select your preferred language")
    print("   - Subtitles should activate immediately")
    
    print("\n4. 🔧 If subtitles don't appear:")
    print("   - Check that your media actually has embedded subtitles")
    print("   - Test with VLC player first")
    print("   - Try pressing Ctrl+D to force detection")
    print("   - Check console output for error messages")
    
    print("\n⚡ Keyboard Shortcuts:")
    print("   Ctrl+D - Detect embedded subtitles")
    print("   Ctrl+T - Toggle subtitle control panel")
    print("   Ctrl+S - Load external subtitle file")
    print("   C      - Toggle subtitles on/off")

def main():
    """Main function."""
    success = manual_ffmpeg_setup()
    
    if success:
        print("\n🎉 FFMPEG SETUP SUCCESSFUL!")
        
        # Test subtitle detection
        detection_ok = test_subtitle_detection()
        
        if detection_ok:
            print("\n✅ Subtitle system is ready!")
            show_usage_guide()
        else:
            print("\n⚠️ Subtitle detection may have issues")
            print("Try restarting PyIPTV and test with real media")
    else:
        print("\n❌ FFMPEG SETUP FAILED!")
        print("You may need to install FFmpeg manually")
        print("Subtitle features will be limited without FFmpeg")

if __name__ == "__main__":
    main()
