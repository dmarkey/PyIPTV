"""
FFmpeg Manager - Automatically download and manage ffmpeg binaries for PyIPTV.
"""

import os
import sys
import platform
import subprocess
import zipfile
import tarfile
import shutil
from pathlib import Path
import urllib.request
import urllib.error


class FFmpegManager:
    """Manages ffmpeg binaries for PyIPTV."""
    
    def __init__(self):
        self.app_dir = Path(__file__).parent.parent  # PyIPTV root directory
        self.ffmpeg_dir = self.app_dir / "ffmpeg_binaries"
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # FFmpeg download URLs for different platforms
        self.download_urls = {
            "windows": {
                "x86_64": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
                "amd64": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
            },
            "linux": {
                "x86_64": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
                "amd64": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
            },
            "darwin": {  # macOS
                "x86_64": "https://evermeet.cx/ffmpeg/getrelease/zip",
                "arm64": "https://evermeet.cx/ffmpeg/getrelease/zip",
            }
        }
    
    def get_ffprobe_path(self):
        """Get the path to ffprobe executable."""
        if self.system == "windows":
            return self.ffmpeg_dir / "bin" / "ffprobe.exe"
        else:
            return self.ffmpeg_dir / "bin" / "ffprobe"
    
    def get_ffmpeg_path(self):
        """Get the path to ffmpeg executable."""
        if self.system == "windows":
            return self.ffmpeg_dir / "bin" / "ffmpeg.exe"
        else:
            return self.ffmpeg_dir / "bin" / "ffmpeg"
    
    def is_ffmpeg_available(self):
        """Check if ffmpeg binaries are available."""
        ffprobe_path = self.get_ffprobe_path()
        ffmpeg_path = self.get_ffmpeg_path()
        
        return (
            ffprobe_path.exists() and 
            ffmpeg_path.exists() and 
            os.access(ffprobe_path, os.X_OK) and 
            os.access(ffmpeg_path, os.X_OK)
        )
    
    def check_system_ffmpeg(self):
        """Check if ffmpeg is available in system PATH."""
        try:
            subprocess.run(
                ["ffprobe", "-version"], 
                capture_output=True, 
                check=True, 
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def download_ffmpeg(self, progress_callback=None):
        """Download and extract ffmpeg binaries."""
        print("📥 Downloading FFmpeg binaries...")
        
        # Create ffmpeg directory
        self.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        
        # Get download URL for current platform
        platform_urls = self.download_urls.get(self.system, {})
        download_url = platform_urls.get(self.arch) or platform_urls.get("x86_64")
        
        if not download_url:
            raise RuntimeError(f"No FFmpeg binaries available for {self.system} {self.arch}")
        
        # Download file
        filename = download_url.split("/")[-1]
        if "?" in filename:  # Handle URLs with query parameters
            filename = filename.split("?")[0]

        # Ensure we have a proper filename
        if not filename or filename == "latest":
            filename = f"ffmpeg-{self.system}-{self.arch}.zip"

        download_path = self.ffmpeg_dir / filename

        # Remove existing file if it exists
        if download_path.exists():
            download_path.unlink()
        
        try:
            print(f"Downloading from: {download_url}")

            def report_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    progress_callback(percent)

            # Add headers to avoid blocking
            request = urllib.request.Request(download_url)
            request.add_header('User-Agent', 'PyIPTV/1.0 (Windows NT 10.0; Win64; x64)')

            with urllib.request.urlopen(request, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0

                with open(download_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            percent = min(100, (downloaded * 100) // total_size)
                            progress_callback(percent)

            print(f"✅ Downloaded: {download_path}")

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            if download_path.exists():
                download_path.unlink()  # Clean up partial download
            raise RuntimeError(f"Failed to download FFmpeg: {e}")
        
        # Extract archive
        self._extract_archive(download_path)
        
        # Clean up download file
        download_path.unlink()
        
        # Verify installation
        if not self.is_ffmpeg_available():
            raise RuntimeError("FFmpeg installation verification failed")
        
        print("✅ FFmpeg binaries installed successfully!")
    
    def _extract_archive(self, archive_path):
        """Extract downloaded archive."""
        print(f"📦 Extracting: {archive_path}")
        
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.ffmpeg_dir)
        elif archive_path.suffix in [".tar", ".xz"]:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(self.ffmpeg_dir)
        else:
            raise RuntimeError(f"Unsupported archive format: {archive_path.suffix}")
        
        # Move binaries to correct location
        self._organize_binaries()
    
    def _organize_binaries(self):
        """Organize extracted binaries into bin/ directory."""
        bin_dir = self.ffmpeg_dir / "bin"
        bin_dir.mkdir(exist_ok=True)
        
        # Find ffmpeg and ffprobe in extracted files
        for root, dirs, files in os.walk(self.ffmpeg_dir):
            for file in files:
                if file.startswith("ffmpeg") and not file.endswith(".txt"):
                    src = Path(root) / file
                    dst = bin_dir / file
                    if src != dst:
                        shutil.move(str(src), str(dst))
                        # Make executable on Unix systems
                        if self.system != "windows":
                            os.chmod(dst, 0o755)
                elif file.startswith("ffprobe") and not file.endswith(".txt"):
                    src = Path(root) / file
                    dst = bin_dir / file
                    if src != dst:
                        shutil.move(str(src), str(dst))
                        # Make executable on Unix systems
                        if self.system != "windows":
                            os.chmod(dst, 0o755)
        
        # Clean up extracted directories
        for item in self.ffmpeg_dir.iterdir():
            if item.is_dir() and item.name != "bin":
                shutil.rmtree(item)
    
    def ensure_ffmpeg(self, progress_callback=None):
        """Ensure ffmpeg is available, download if necessary."""
        # First check if system ffmpeg is available
        if self.check_system_ffmpeg():
            print("✅ Using system FFmpeg")
            return "system"
        
        # Check if bundled ffmpeg is available
        if self.is_ffmpeg_available():
            print("✅ Using bundled FFmpeg")
            return "bundled"
        
        # Download and install ffmpeg
        try:
            self.download_ffmpeg(progress_callback)
            return "downloaded"
        except Exception as e:
            print(f"❌ Failed to download FFmpeg: {e}")
            raise
    
    def get_ffprobe_command(self):
        """Get the appropriate ffprobe command."""
        if self.check_system_ffmpeg():
            return ["ffprobe"]
        elif self.is_ffmpeg_available():
            return [str(self.get_ffprobe_path())]
        else:
            raise RuntimeError("FFmpeg not available. Call ensure_ffmpeg() first.")
    
    def get_ffmpeg_command(self):
        """Get the appropriate ffmpeg command."""
        if self.check_system_ffmpeg():
            return ["ffmpeg"]
        elif self.is_ffmpeg_available():
            return [str(self.get_ffmpeg_path())]
        else:
            raise RuntimeError("FFmpeg not available. Call ensure_ffmpeg() first.")


# Global instance
ffmpeg_manager = FFmpegManager()


def ensure_ffmpeg_available(progress_callback=None):
    """Convenience function to ensure ffmpeg is available."""
    return ffmpeg_manager.ensure_ffmpeg(progress_callback)


def get_ffprobe_command():
    """Convenience function to get ffprobe command."""
    return ffmpeg_manager.get_ffprobe_command()


def get_ffmpeg_command():
    """Convenience function to get ffmpeg command."""
    return ffmpeg_manager.get_ffmpeg_command()
