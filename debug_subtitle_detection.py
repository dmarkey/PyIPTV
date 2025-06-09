#!/usr/bin/env python3

"""
Debug subtitle track detection issues.
"""

import sys
import os
import subprocess
import json

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def test_ffprobe_detection(url):
    """Test ffprobe subtitle detection directly."""
    print(f"\n🔍 Testing ffprobe detection for: {url}")
    
    try:
        # Run ffprobe command
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            url
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ ffprobe failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        
        # Parse JSON output
        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        
        print(f"✅ Found {len(streams)} total streams")
        
        # Find subtitle streams
        subtitle_streams = []
        for i, stream in enumerate(streams):
            codec_type = stream.get('codec_type', '')
            if codec_type == 'subtitle':
                subtitle_streams.append({
                    'index': i,
                    'codec_name': stream.get('codec_name', 'unknown'),
                    'language': stream.get('tags', {}).get('language', 'unknown'),
                    'title': stream.get('tags', {}).get('title', ''),
                    'disposition': stream.get('disposition', {})
                })
        
        if subtitle_streams:
            print(f"✅ Found {len(subtitle_streams)} subtitle streams:")
            for sub in subtitle_streams:
                print(f"  Stream {sub['index']}: {sub['codec_name']} - {sub['language']} - {sub['title']}")
        else:
            print("❌ No subtitle streams found")
            
        return len(subtitle_streams) > 0
        
    except subprocess.TimeoutExpired:
        print("❌ ffprobe command timed out")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse ffprobe JSON output: {e}")
        return False
    except Exception as e:
        print(f"❌ Error running ffprobe: {e}")
        return False

def test_subtitle_manager_detection(url):
    """Test PyIPTV subtitle manager detection."""
    print(f"\n🔍 Testing PyIPTV subtitle manager detection for: {url}")
    
    try:
        from pyiptv.subtitle_manager import SubtitleManager
        
        manager = SubtitleManager()
        print("✅ SubtitleManager created")
        
        # Test detection
        tracks = manager.detect_embedded_tracks(url)
        
        if tracks:
            print(f"✅ PyIPTV detected {len(tracks)} subtitle tracks:")
            for track in tracks:
                print(f"  {track.id}: {track.display_name} (Stream {track.stream_index})")
        else:
            print("❌ PyIPTV detected no subtitle tracks")
            
        return len(tracks) > 0
        
    except Exception as e:
        print(f"❌ Error in PyIPTV subtitle detection: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_ffprobe_availability():
    """Check if ffprobe is available."""
    print("🔍 Checking ffprobe availability...")
    
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ ffprobe available: {version_line}")
            return True
        else:
            print("❌ ffprobe not working properly")
            return False
    except FileNotFoundError:
        print("❌ ffprobe not found in PATH")
        print("💡 Install ffmpeg to enable subtitle detection")
        return False
    except Exception as e:
        print(f"❌ Error checking ffprobe: {e}")
        return False

def test_sample_urls():
    """Test with some sample URLs."""
    print("\n🧪 Testing with sample URLs...")
    
    # Test URLs (replace with your actual URLs)
    test_urls = [
        "http://example.com/channel1.ts",  # Replace with your actual URL
        "http://example.com/movie.mkv",    # Replace with your actual URL
    ]
    
    print("⚠️  Please replace these with your actual stream URLs:")
    for url in test_urls:
        print(f"  - {url}")
    
    print("\n💡 To test with your URLs, modify this script and add your actual stream URLs")

def show_troubleshooting_guide():
    """Show troubleshooting guide."""
    print("\n🔧 SUBTITLE DETECTION TROUBLESHOOTING GUIDE:")
    
    print("\n1. 📋 CHECK YOUR MEDIA:")
    print("   ✅ Confirm your streams actually have embedded subtitles")
    print("   ✅ Test with VLC player - can you see subtitle tracks there?")
    print("   ✅ Check if subtitles are embedded or external (.srt files)")
    
    print("\n2. 🛠️ CHECK FFPROBE:")
    print("   ✅ Make sure ffmpeg/ffprobe is installed")
    print("   ✅ Run: ffprobe -show_streams [your_stream_url]")
    print("   ✅ Look for codec_type='subtitle' in the output")
    
    print("\n3. 🔍 CHECK PYIPTV DETECTION:")
    print("   ✅ Load media in PyIPTV")
    print("   ✅ Press Ctrl+D to manually detect subtitles")
    print("   ✅ Check status messages for detection results")
    print("   ✅ Look at console output for error messages")
    
    print("\n4. 🎯 CHECK CONTROL BAR:")
    print("   ✅ Look for 📝 'Sub Track' button in control bar")
    print("   ✅ Click dropdown - should show detected tracks")
    print("   ✅ If shows 'No tracks', detection failed")
    
    print("\n5. 🐛 COMMON ISSUES:")
    print("   ❌ ffprobe not installed → Install ffmpeg")
    print("   ❌ Network timeout → Check internet connection")
    print("   ❌ Stream has no subtitles → Verify with VLC")
    print("   ❌ Subtitles are external → Use Ctrl+S to load .srt files")
    print("   ❌ Detection timing → Wait a few seconds after loading")

def main():
    """Main diagnostic function."""
    print("🔍 SUBTITLE DETECTION DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Check ffprobe
    ffprobe_ok = check_ffprobe_availability()
    
    if not ffprobe_ok:
        print("\n❌ CRITICAL: ffprobe not available!")
        print("💡 Install ffmpeg to enable subtitle detection:")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("   Linux: sudo apt install ffmpeg")
        print("   macOS: brew install ffmpeg")
        return
    
    # Test sample URLs
    test_sample_urls()
    
    # Show troubleshooting guide
    show_troubleshooting_guide()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Replace sample URLs in this script with your actual stream URLs")
    print("2. Run the script again to test detection")
    print("3. If detection works here but not in PyIPTV, check the control bar")
    print("4. If detection fails, verify your streams have embedded subtitles")

if __name__ == "__main__":
    main()
    
    # Interactive testing
    print("\n" + "=" * 50)
    print("🧪 INTERACTIVE TESTING")
    
    url = input("\nEnter a stream URL to test (or press Enter to skip): ").strip()
    
    if url:
        print(f"\nTesting URL: {url}")
        
        # Test ffprobe detection
        ffprobe_result = test_ffprobe_detection(url)
        
        # Test PyIPTV detection
        pyiptv_result = test_subtitle_manager_detection(url)
        
        print(f"\n📊 RESULTS:")
        print(f"  ffprobe detection: {'✅ SUCCESS' if ffprobe_result else '❌ FAILED'}")
        print(f"  PyIPTV detection:  {'✅ SUCCESS' if pyiptv_result else '❌ FAILED'}")
        
        if ffprobe_result and not pyiptv_result:
            print("\n⚠️  ffprobe works but PyIPTV doesn't - check PyIPTV integration")
        elif not ffprobe_result:
            print("\n⚠️  ffprobe can't detect subtitles - stream may not have embedded subtitles")
        elif ffprobe_result and pyiptv_result:
            print("\n✅ Both work! Check the 📝 Sub Track button in PyIPTV control bar")
    else:
        print("\nSkipping interactive test. Use the troubleshooting guide above.")
