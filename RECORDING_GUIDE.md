# 🎬 PyIPTV Recording Guide

## How to Record Live Streams

PyIPTV provides multiple ways to record live IPTV streams. Here's a comprehensive guide on how to use the recording features.

### 📋 Prerequisites

1. **FFmpeg Required**: Make sure FFmpeg is installed and available
   - **Windows**: Run `python download_ffmpeg.py` or install via Chocolatey/Scoop
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo dnf install ffmpeg` (Fedora/CentOS)
   - **macOS**: `brew install ffmpeg`

2. **Storage Space**: Ensure you have sufficient disk space for recordings
   - Default location: `~/Videos/PyIPTV Recordings/`
   - Configurable in Enhanced Features Settings

### 🎯 How to Start Recording

#### Method 1: Right-Click Context Menu (Easiest)
1. **Right-click** on any channel in the channel list
2. Select **"🔴 Start Recording"** from the context menu
3. Recording starts immediately with automatic file naming

#### Method 2: Keyboard Shortcut
1. Select a channel in the channel list
2. Press **`Ctrl+R`** to start recording
3. Recording begins for the selected channel

#### Method 3: Tools Menu
1. Select a channel in the channel list
2. Go to **Tools** → **"Start Recording"**
3. Recording starts for the selected channel

### 📊 Managing Active Recordings

#### Recording Status Widget
- **Location**: Appears in the left panel when recordings are active
- **Features**:
  - Shows all active recordings
  - Real-time duration and file size updates
  - Individual **Stop** buttons for each recording
  - Auto-hides when no recordings are active

#### Status Bar Indicator
- **Location**: Bottom status bar
- **Display**: Shows "🔴 Recording (X)" where X is the number of active recordings
- **Purpose**: Quick overview of recording status

### ⏹️ How to Stop Recording

#### Individual Recording Stop
1. Find the recording in the **Recording Status Widget**
2. Click the **"Stop"** button next to the specific recording
3. Recording stops and file is saved

#### Stop All Recordings
- Currently, stop each recording individually
- Closing the application will stop all recordings safely

### 📁 Recording Output

#### Default Settings
- **Format**: MP4 (configurable)
- **Quality**: Stream copy (no re-encoding for best quality)
- **Location**: `~/Videos/PyIPTV Recordings/`
- **Naming**: `ChannelName_YYYYMMDD_HHMMSS.mp4`

#### File Organization
```
~/Videos/PyIPTV Recordings/
├── CNN_20241201_143022.mp4
├── BBC_News_20241201_150315.mp4
└── Sports_Channel_20241201_160445.mp4
```

### ⚙️ Recording Settings

#### Access Settings
1. Go to **Tools** → **"Enhanced Features Settings..."**
2. Navigate to the **Recording** section
3. Configure your preferences

#### Available Options
- **Output Directory**: Choose where recordings are saved
- **Recording Format**: MP4, MKV, TS, FLV
- **Quality Settings**: Stream copy or re-encode options
- **Auto-naming**: Automatic file naming with timestamps

### 🔧 Troubleshooting

#### "Recording not available"
- **Cause**: FFmpeg not installed or not found
- **Solution**: Install FFmpeg using the methods above
- **Check**: Run `ffmpeg -version` in terminal to verify installation

#### "Failed to start recording"
- **Cause**: Stream URL not accessible or invalid
- **Solution**: Try playing the channel first to verify it works
- **Check**: Ensure you have write permissions to the output directory

#### "No stream URL available"
- **Cause**: Channel doesn't have a valid stream URL
- **Solution**: Check the M3U playlist for valid URLs
- **Note**: Some channels may be offline or have expired URLs

#### Recording stops unexpectedly
- **Cause**: Stream went offline or network issues
- **Solution**: Check internet connection and stream availability
- **Note**: This is normal for live streams that go offline

### 💡 Tips and Best Practices

#### Storage Management
- **Monitor disk space**: Recordings can be large (1-2 GB per hour)
- **Regular cleanup**: Delete old recordings you no longer need
- **External storage**: Consider using external drives for long recordings

#### Quality vs. Size
- **Stream copy**: Best quality, larger files, no CPU usage
- **Re-encode**: Smaller files, lower quality, uses CPU
- **Recommendation**: Use stream copy for most cases

#### Multiple Recordings
- **Simultaneous**: Record multiple channels at once
- **Performance**: Each recording uses network bandwidth
- **Limit**: Depends on your internet speed and system resources

#### Scheduling (Future Feature)
- Currently: Manual start/stop only
- **Planned**: Scheduled recordings with start/end times
- **Workaround**: Use system task scheduler with PyIPTV commands

### 🎬 Recording Workflow Example

1. **Browse channels** in PyIPTV
2. **Find interesting content** you want to record
3. **Right-click** the channel → **"🔴 Start Recording"**
4. **Monitor progress** in the Recording Status Widget
5. **Stop recording** when content ends
6. **Find your recording** in `~/Videos/PyIPTV Recordings/`
7. **Enjoy** your recorded content!

### 📞 Support

If you encounter issues with recording:

1. **Check FFmpeg**: Ensure it's properly installed
2. **Verify permissions**: Make sure you can write to the output directory
3. **Test stream**: Try playing the channel first
4. **Check logs**: Look for error messages in the application
5. **Report issues**: Create an issue on GitHub with details

---

**Happy Recording! 🎉**

*Record your favorite shows, news, sports, and more with PyIPTV's powerful recording features.*
