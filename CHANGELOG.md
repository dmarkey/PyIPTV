# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-04

### Added
- Initial PyPI release
- Modern PySide6/Qt6 interface
- M3U playlist support with category organization
- Real-time search and filtering capabilities
- System-aware theming with KDE integration
- Performance optimizations for large playlists
- Virtualized channel lists for smooth scrolling
- Persistent settings management
- Audio track selection support
- High DPI display support
- uvx compatibility for isolated execution

### Features
- **Playlist Management**: Load and manage IPTV playlists in M3U format
- **User Interface**: Modern Qt6-based interface with responsive design
- **Performance**: Optimized for handling large playlists with thousands of channels
- **Customization**: Configurable buffering, themes, and performance settings
- **Cross-Platform**: Support for Linux, Windows, and macOS

### Technical
- Built with PySide6 6.5.0+
- Python 3.8+ compatibility
- Standard packaging with pyproject.toml
- Entry point: `pyiptv` command
- Package data includes UI assets and themes

## [1.1.0] - 2026-04-19

### Added
- Native **Xtream Codes** playlist support as a third source type (alongside file and URL). Authenticates against `player_api.php`, fetches live categories and streams, transforms them into the existing channel-dict shape so the UI pipeline is reused unchanged. Channel + category data is pickled to `~/.config/PyIPTV/playlist_cache/` with a 6-hour TTL; stale cache is used as an offline fallback on fetch failure. Right-click a source → "Refresh Xtream Source" to force a re-fetch. `get_short_epg` is plumbed through the client but not yet displayed.
- Sleep inhibition during fullscreen playback (macOS). Holds a `PreventUserIdleDisplaySleep` IOKit assertion while fullscreen is active, released on exit or app shutdown.
- Automatic audio-output rebinding. The player now follows the macOS system default (e.g. a Bluetooth headset connecting mid-playback) by listening to `QMediaDevices.audioOutputsChanged` and swapping the `QAudioOutput`'s device.

### Planned
- VOD and series browsers for Xtream sources
- EPG guide UI (now/next strip and full program guide)
- XMLTV ingestion
- Keyring-backed credential storage
- Local UA-rewriting proxy for providers that gate streams on User-Agent
- Enhanced search functionality
- Playlist synchronization features
- Improved error handling
- Additional theme options