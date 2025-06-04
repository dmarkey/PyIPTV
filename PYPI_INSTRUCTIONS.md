# PyPI Publishing Instructions

This document contains instructions for publishing PyPTV to PyPI and verifying uvx compatibility.

## Package Information
- **Package Name**: `pyptv`
- **Version**: `1.0.0`
- **License**: MIT
- **Author**: David Markey <david@dmarkey.com>
- **Repository**: https://github.com/dmarkey/Pyptv

## Files Created for PyPI

### Essential Files
- `pyproject.toml` - Modern Python packaging configuration
- `README.md` - Package documentation and usage instructions
- `LICENSE` - MIT license file
- `MANIFEST.in` - Controls which files are included in the distribution
- `.gitignore` - Git ignore patterns for Python projects
- `CHANGELOG.md` - Version history and changes

### Package Structure
```
pyptv/
├── __init__.py          # Package metadata and version info
├── main.py             # Main entry point with CLI functionality
├── *.py                # All other Python modules
└── ui/
    ├── images/         # UI assets (logo.png)
    ├── components/     # UI components
    └── *.py           # UI modules
```

## Built Packages
- `dist/pyptv-1.0.0-py3-none-any.whl` - Universal wheel
- `dist/pyptv-1.0.0.tar.gz` - Source distribution

## Publishing to PyPI

### 1. Install Publishing Tools
```bash
pip install twine
```

### 2. Test on TestPyPI (Recommended)
```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ pyptv
```

### 3. Publish to PyPI
```bash
# Upload to production PyPI
twine upload dist/*
```

### 4. Configure PyPI credentials
Create `~/.pypirc`:
```ini
[distutils]
index-servers = pypi testpypi

[pypi]
username = __token__
password = your-pypi-token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = your-testpypi-token
```

## Installation Methods

### From PyPI
```bash
pip install pyptv
```

### Using uvx (Isolated execution)
```bash
uvx pyptv
```

### From source
```bash
git clone https://github.com/dmarkey/Pyptv.git
cd Pyptv
pip install -e .
```

## Usage

### Command Line
- `pyptv` - Launch with playlist manager
- `pyptv /path/to/playlist.m3u` - Launch with specific playlist

### uvx Usage
- `uvx pyptv` - Run in isolated environment
- `uvx --from pyptv pyptv /path/to/playlist.m3u` - Run with playlist

## Package Features
- Modern PySide6/Qt6 interface
- M3U playlist support
- Category organization
- Search and filtering
- System-aware theming
- Performance optimizations for large playlists
- Cross-platform compatibility (Linux, Windows, macOS)

## Dependencies
- Python 3.8+
- PySide6 ≥ 6.5.0
- requests ≥ 2.25.0

## Next Steps
1. Test the package locally: `pip install -e .`
2. Verify CLI works: `pyptv`
3. Test with uvx: `uvx --from . pyptv`
4. Upload to TestPyPI for testing
5. Upload to production PyPI
6. Test installation from PyPI
7. Verify uvx works with published package: `uvx pyptv`

## Notes
- The package includes all necessary metadata for PyPI
- The CLI entry point is properly configured
- All UI assets are included in the package
- The package follows modern Python packaging standards
- License information is properly configured
- Version is synchronized across all files