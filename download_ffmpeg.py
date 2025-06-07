#!/usr/bin/env python3
"""
FFmpeg Download Script for PyIPTV

This script downloads and extracts FFmpeg binaries for Windows.
For other platforms, please install FFmpeg using your system package manager.
"""

import os
import sys
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path


def download_ffmpeg_windows():
    """Download and extract FFmpeg for Windows."""
    if platform.system() != "Windows":
        print("This script is for Windows only.")
        print("For other platforms, install FFmpeg using your package manager:")
        print("  Linux: sudo apt install ffmpeg  (Ubuntu/Debian)")
        print("         sudo dnf install ffmpeg  (Fedora/CentOS)")
        print("  macOS: brew install ffmpeg")
        return False
    
    # FFmpeg download URL (latest stable build)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Create directories
    bin_dir = Path("ffmpeg_binaries/bin")
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    temp_dir = Path("temp_ffmpeg")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        print("Downloading FFmpeg...")
        zip_path = temp_dir / "ffmpeg.zip"
        
        # Download with progress
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded * 100) // total_size)
                print(f"\rProgress: {percent}%", end="", flush=True)
        
        urllib.request.urlretrieve(ffmpeg_url, zip_path, show_progress)
        print("\nDownload complete!")
        
        print("Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find the extracted directory
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            raise Exception("No directories found in extracted archive")
        
        ffmpeg_dir = extracted_dirs[0] / "bin"
        
        # Copy required files
        required_files = ["ffmpeg.exe", "ffprobe.exe"]
        for file_name in required_files:
            src = ffmpeg_dir / file_name
            dst = bin_dir / file_name
            
            if src.exists():
                shutil.copy2(src, dst)
                print(f"Copied {file_name}")
            else:
                print(f"Warning: {file_name} not found in archive")
        
        print("FFmpeg installation complete!")
        return True
        
    except Exception as e:
        print(f"Error downloading FFmpeg: {e}")
        return False
    
    finally:
        # Clean up temporary files
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def check_ffmpeg():
    """Check if FFmpeg is already available."""
    # Check if ffmpeg is in PATH
    if shutil.which("ffmpeg"):
        print("FFmpeg is already installed and available in PATH.")
        return True
    
    # Check if ffmpeg is in local bin directory
    local_ffmpeg = Path("ffmpeg_binaries/bin/ffmpeg.exe")
    if local_ffmpeg.exists():
        print("FFmpeg found in local bin directory.")
        return True
    
    return False


def main():
    """Main function."""
    print("PyIPTV FFmpeg Setup")
    print("=" * 20)
    
    if check_ffmpeg():
        print("FFmpeg is already available. No action needed.")
        return
    
    if platform.system() == "Windows":
        print("FFmpeg not found. Downloading...")
        if download_ffmpeg_windows():
            print("\nFFmpeg has been downloaded and installed successfully!")
            print("You can now run PyIPTV.")
        else:
            print("\nFailed to download FFmpeg. Please install manually:")
            print("1. Download from https://ffmpeg.org/download.html")
            print("2. Extract ffmpeg.exe and ffprobe.exe to ffmpeg_binaries/bin/")
    else:
        print("Please install FFmpeg using your system package manager:")
        print("  Linux: sudo apt install ffmpeg  (Ubuntu/Debian)")
        print("         sudo dnf install ffmpeg  (Fedora/CentOS)")
        print("  macOS: brew install ffmpeg")


if __name__ == "__main__":
    main()
