<div align="center">
  <img src="pyiptv/ui/images/logo.png" alt="PyIPTV Logo" width="200"/>
  
  # PyIPTV
  
  **A Modern Python IPTV Player**
  
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)](https://www.qt.io/)
  [![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/dmarkey/PyIPTV/graphs/commit-activity)
  
  *Feature-rich IPTV player built with PySide6/Qt6 for streaming live television content from M3U playlists*
</div>

---

## ✨ Features

### Core Functionality
- 📺 **M3U Playlist Support** - Load and manage IPTV playlists in M3U format
- 🎨 **Modern Qt6 Interface** - Built with PySide6 for a responsive, native desktop experience
- 📂 **Category Organization** - Automatically organize channels by categories
- 🔍 **Search & Filtering** - Quickly find channels with real-time search
- 🎵 **Audio Track Selection** - Multi-language audio track support

### Enhanced Features ⭐ NEW
- 📹 **Live Stream Recording** - Record streams to MP4 with FFmpeg integration
- 🔗 **Dead Link Detection** - Automatic validation and removal of broken streams
- 🔄 **Auto-Updates** - Automatic playlist refresh for URL-based sources
- 💾 **Auto-Save** - Automatic M3U file saving with backup system
- ⚙️ **Advanced Settings** - Comprehensive configuration for all enhanced features

### User Experience
- 🌓 **Theme Support** - System-aware theming with KDE integration
- ⚡ **Performance Optimized** - Handles large playlists with virtualized lists and smart buffering
- ⚙️ **Settings Management** - Persistent settings with user-friendly configuration
- 🖥️ **High DPI Support** - Optimized for high-resolution displays

## 🚀 Installation

### From PyPI (Recommended)

```bash
pip install pyiptv
```

### Using uvx (Isolated execution)

```bash
uvx pyiptv
```

### From Source

```bash
git clone https://github.com/zinzied/PyIPTV.git
cd PyIPTV
pip install -e .
```

### Enhanced Features Dependencies

For the enhanced features (recording, dead link detection, auto-updates), install additional dependencies:

```bash
pip install aiohttp
```

**Note:** FFmpeg is required for recording functionality. See the FFmpeg installation section below.

## 📖 Usage

### Basic Usage

Launch PyIPTV without arguments to open the playlist manager:

```bash
pyiptv
```

### Direct Playlist Loading

Launch directly with a playlist file:

```bash
pyiptv /path/to/your/playlist.m3u
```

### Command Line Arguments

| Command | Description |
|---------|-------------|
| `pyiptv` | Launch with playlist manager |
| `pyiptv <playlist_path>` | Launch directly with specified playlist |

## 🚀 Enhanced Features

### 📹 Live Stream Recording

Record live IPTV streams directly to your local storage:

- **Multiple Formats**: MP4, MKV, AVI support
- **Quality Control**: Copy stream or re-encode with custom settings
- **Session Management**: Start/stop recordings with progress tracking
- **Auto-naming**: Automatic file naming with timestamps
- **Background Recording**: Continue recording while watching other channels

**Usage:**
- Right-click on any channel → "Start Recording"
- Use `Ctrl+R` keyboard shortcut
- Access via Tools menu → "Start Recording"

### 🔗 Dead Link Detection

Automatically detect and manage broken stream links:

- **Async Validation**: Fast concurrent link checking
- **Smart Detection**: HTTP status codes, timeouts, and connection errors
- **Auto-Removal**: Optional automatic removal of dead links
- **User Control**: Review and confirm before removing links
- **Scheduled Checks**: Configurable automatic validation intervals

**Configuration:**
- Check interval: 1-168 hours (default: 6 hours)
- Timeout: 5-60 seconds (default: 10 seconds)
- Auto-removal: Enable/disable (default: disabled for safety)

### 🔄 Automatic Playlist Updates

Keep your playlists fresh with automatic updates:

- **URL Playlists**: Automatic refresh for web-based playlists
- **Smart Caching**: Efficient download and storage management
- **Change Detection**: Only update when content actually changes
- **Scheduled Updates**: Configurable update intervals
- **Background Processing**: Non-blocking updates with progress notifications

**Features:**
- Update interval: 1-168 hours (default: 24 hours)
- Automatic caching and backup
- Manual update trigger available
- Status notifications for all operations

### 💾 Auto-Save M3U Files

Automatically save playlist modifications:

- **Real-time Saving**: Automatic save when playlists are modified
- **Backup System**: Keeps 10 most recent backups
- **Debounced Saves**: Intelligent saving to prevent excessive I/O
- **Format Preservation**: Maintains all M3U metadata and structure
- **Error Recovery**: Backup restoration on save failures

**Backup Location:** `<playlist_directory>/backups/`

## ⌨️ Keyboard Shortcuts

### Playback Controls
| Shortcut | Action |
|----------|--------|
| `Space` / `P` | Play/Pause |
| `S` | Stop |
| `M` | Mute/Unmute |
| `↑` / `↓` | Volume Up/Down |
| `←` / `→` | Previous/Next Channel |

### Enhanced Features
| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Start Recording Current Channel |
| `Ctrl+V` | Validate All Links |
| `F5` | Update Current Playlist |
| `Ctrl+F` | Search Channels |
| `Ctrl+Shift+F` | Search Categories |

### View Controls
| Shortcut | Action |
|----------|--------|
| `F11` / `F` | Toggle Fullscreen |
| `Escape` | Exit Fullscreen |
| `Ctrl+T` | Toggle Subtitle Panel |
| `C` | Toggle Subtitles |

### Application
| Shortcut | Action |
|----------|--------|
| `F1` / `Ctrl+H` | Show Help |
| `Ctrl+,` | Open Settings |
| `Ctrl+Q` | Quit Application |

## 📋 Requirements

| Component | Version | Description |
|-----------|---------|-------------|
| Python | 3.8+ | Core runtime |
| PySide6 | 6.5.0+ | Qt6 bindings |
| aiohttp | Latest | Async HTTP for link validation |
| Qt6 multimedia libraries | Latest | Media playback |
| Operating System | Linux, Windows, macOS | Cross-platform support |

### System Dependencies

<details>
<summary><strong>🐧 Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt install python3-pip qt6-multimedia-dev ffmpeg
```
</details>

<details>
<summary><strong>🎩 Linux (Fedora/CentOS)</strong></summary>

```bash
sudo dnf install python3-pip qt6-qtmultimedia-devel ffmpeg
```
</details>

<details>
<summary><strong>🍎 macOS</strong></summary>

```bash
brew install python qt6 ffmpeg
```
</details>

<details>
<summary><strong>🪟 Windows</strong></summary>

**FFmpeg Installation Required:**

1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract the binaries to `ffmpeg_binaries/bin/` in your PyIPTV directory
3. Required files:
   - `ffmpeg.exe`
   - `ffprobe.exe`

Alternatively, install via package manager:
```bash
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg
```

No additional Qt dependencies required - PySide6 includes all necessary Qt libraries.
</details>

## ⚙️ Configuration

PyIPTV automatically creates configuration files in platform-appropriate locations:

| Platform | Configuration Path |
|----------|-------------------|
| **Linux** | `~/.config/PyIPTV/pyiptv_settings.json` |
| **Windows** | `%APPDATA%/PyIPTV/pyiptv_settings.json` |
| **macOS** | `~/.config/PyIPTV/pyiptv_settings.json` |

### Available Settings

- **Theme Mode** - System auto-detection, light, or dark themes
- **Buffering** - Adjustable buffering time for smooth playback
- **Performance** - Options for handling large playlists
- **UI Preferences** - Window geometry, splitter sizes, and more

## 📝 Playlist Format

PyIPTV supports standard M3U playlist format with extended information:

```m3u
#EXTM3U
#EXTINF:-1 tvg-id="channel1" tvg-name="Channel Name" tvg-logo="logo.png" group-title="Category",Channel Display Name
http://example.com/stream1.m3u8
#EXTINF:-1 tvg-id="channel2" tvg-name="Another Channel" group-title="Movies",Movie Channel
http://example.com/stream2.m3u8
```

## 🏗️ Architecture

PyIPTV follows a modular architecture design:

```
┌─────────────────┐
│ Main Application│
├─────────────────┤
│ UI Components   │
│ Playlist Manager│
│ Media Player    │
│ Settings Manager│
│ Theme Manager   │
└─────────────────┘
```

### Components

- **Main Application** - Entry point and application lifecycle management
- **UI Components** - Modular Qt widgets for different functionality
- **Playlist Manager** - M3U parsing and playlist management
- **Media Player** - Qt6 multimedia integration
- **Settings Manager** - Configuration persistence
- **Theme Manager** - System-aware theming

## 🛠️ Development

### Setting up Development Environment

```bash
git clone https://github.com/dmarkey/PyIPTV.git
cd PyIPTV
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black pyiptv/
isort pyiptv/
```

### Linting

```bash
flake8 pyiptv/
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Video playback problems | Ensure Qt6 multimedia libraries are installed |
| Theme not applying correctly | Check desktop environment compatibility |
| Performance issues with large playlists | Adjust performance settings in configuration |

### Debug Mode

Run with debug information:

```bash
PYTHONPATH=. python -m pyiptv.main --debug
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure compatibility with supported Python versions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Most of the codebase for PyIPTV was generated by Claude Sonnet 4
- Enhanced by [zinzied](https://github.com/zinzied) (zinzied@gmail.com)
- Built with [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python
- Inspired by the need for a modern, cross-platform IPTV player
- Thanks to the open-source community for tools and libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/dmarkey/PyIPTV/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dmarkey/PyIPTV/discussions)
- **Email**: david@dmarkey.com

---

<div align="center">
  
**⚠️ Legal Notice**

*This software is for personal use with legally obtained IPTV content. Users are responsible for ensuring they have appropriate rights to access any content streams.*

</div>