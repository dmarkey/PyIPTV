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

## [Unreleased]

### Planned
- Enhanced search functionality
- Playlist synchronization features
- Improved error handling
- Additional theme options
- EPG (Electronic Program Guide) support