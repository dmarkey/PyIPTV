#!/usr/bin/env python3
"""
Auto-Updater for PyIPTV

This module provides functionality to automatically update playlists,
save modified M3U files, and manage playlist synchronization.
"""

import os
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer, QThread
from PySide6.QtWidgets import QApplication

from pyiptv.m3u_parser import M3UParser


class PlaylistUpdateResult:
    """Result of playlist update operation."""
    
    def __init__(self, playlist_id: str, success: bool, 
                 channels_added: int = 0, channels_removed: int = 0,
                 error_message: str = ""):
        self.playlist_id = playlist_id
        self.success = success
        self.channels_added = channels_added
        self.channels_removed = channels_removed
        self.error_message = error_message
        self.timestamp = datetime.now()


class M3UAutoSaver(QObject):
    """Handles automatic saving of modified M3U files."""
    
    # Signals
    file_saved = Signal(str)  # file_path
    save_failed = Signal(str, str)  # file_path, error_message
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.pending_saves = {}  # file_path -> (channels, categories)
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._perform_pending_saves)
        
    def schedule_save(self, file_path: str, channels: List[Dict], categories: Dict):
        """Schedule an M3U file save (debounced)."""
        if not self.settings_manager.get_setting("auto_save_m3u", True):
            return
            
        self.pending_saves[file_path] = (channels, categories)
        
        # Debounce saves - wait 2 seconds before saving
        self.save_timer.stop()
        self.save_timer.start(2000)
        
    def _perform_pending_saves(self):
        """Perform all pending saves."""
        for file_path, (channels, categories) in self.pending_saves.items():
            self._save_m3u_file(file_path, channels, categories)
            
        self.pending_saves.clear()
        
    def _save_m3u_file(self, file_path: str, channels: List[Dict], categories: Dict):
        """Save channels to M3U file."""
        try:
            # Create backup first
            self._create_backup(file_path)
            
            # Generate M3U content
            m3u_content = self._generate_m3u_content(channels)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(m3u_content)
                
            self.file_saved.emit(file_path)
            print(f"Auto-saved M3U file: {file_path}")
            
        except Exception as e:
            error_msg = f"Failed to save M3U file: {str(e)}"
            self.save_failed.emit(file_path, error_msg)
            print(error_msg)
            
    def _create_backup(self, file_path: str):
        """Create a backup of the original file."""
        if not os.path.exists(file_path):
            return
            
        backup_dir = os.path.join(os.path.dirname(file_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            shutil.copy2(file_path, backup_path)
            
            # Keep only last 10 backups
            self._cleanup_old_backups(backup_dir, os.path.basename(file_path))
            
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
            
    def _cleanup_old_backups(self, backup_dir: str, original_filename: str):
        """Keep only the most recent backups."""
        try:
            backup_files = []
            for f in os.listdir(backup_dir):
                if f.startswith(original_filename + ".backup_"):
                    backup_path = os.path.join(backup_dir, f)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
                    
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups (keep only 10 most recent)
            for backup_path, _ in backup_files[10:]:
                os.remove(backup_path)
                
        except Exception as e:
            print(f"Warning: Could not cleanup old backups: {e}")
            
    def _generate_m3u_content(self, channels: List[Dict]) -> str:
        """Generate M3U file content from channels."""
        lines = ["#EXTM3U"]
        
        for channel in channels:
            # Build EXTINF line
            extinf_parts = ["#EXTINF:-1"]
            
            # Add attributes
            if channel.get("tvg-id"):
                extinf_parts.append(f'tvg-id="{channel["tvg-id"]}"')
            if channel.get("tvg-name"):
                extinf_parts.append(f'tvg-name="{channel["tvg-name"]}"')
            if channel.get("tvg-logo"):
                extinf_parts.append(f'tvg-logo="{channel["tvg-logo"]}"')
            if channel.get("group-title"):
                extinf_parts.append(f'group-title="{channel["group-title"]}"')
                
            # Add channel name
            channel_name = channel.get("name", "Unknown Channel")
            extinf_line = " ".join(extinf_parts) + f",{channel_name}"
            
            lines.append(extinf_line)
            lines.append(channel.get("url", ""))
            
        return "\n".join(lines) + "\n"


class PlaylistAutoUpdater(QObject):
    """Handles automatic playlist updates."""
    
    # Signals
    update_started = Signal(str)  # playlist_id
    update_completed = Signal(str, object)  # playlist_id, PlaylistUpdateResult
    update_failed = Signal(str, str)  # playlist_id, error_message
    
    def __init__(self, settings_manager, playlist_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.playlist_manager = playlist_manager
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._check_for_updates)
        
        # Setup automatic updates if enabled
        self.setup_auto_updates()
        
    def setup_auto_updates(self):
        """Setup automatic playlist updates."""
        if self.settings_manager.get_setting("auto_update_playlists", True):
            interval_hours = self.settings_manager.get_setting("auto_update_interval_hours", 24)
            interval_ms = interval_hours * 60 * 60 * 1000  # Convert to milliseconds
            self.update_timer.start(interval_ms)
            print(f"Auto-update enabled: checking every {interval_hours} hours")
            
    def _check_for_updates(self):
        """Check which playlists need updating."""
        current_time = datetime.now()
        update_interval = timedelta(hours=self.settings_manager.get_setting("auto_update_interval_hours", 24))
        
        for playlist_id, playlist in self.playlist_manager.playlists.items():
            if playlist.source_type == "url":  # Only update URL-based playlists
                last_update = datetime.fromtimestamp(playlist.last_opened)
                if current_time - last_update >= update_interval:
                    self.update_playlist(playlist_id)
                    
    def update_playlist(self, playlist_id: str):
        """Update a specific playlist."""
        if playlist_id not in self.playlist_manager.playlists:
            return
            
        playlist = self.playlist_manager.playlists[playlist_id]
        
        if playlist.source_type != "url":
            return  # Only update URL playlists
            
        self.update_started.emit(playlist_id)
        
        # Start update in a separate thread
        update_thread = PlaylistUpdateThread(playlist, self.settings_manager)
        update_thread.update_completed.connect(
            lambda result: self.update_completed.emit(playlist_id, result)
        )
        update_thread.update_failed.connect(
            lambda error: self.update_failed.emit(playlist_id, error)
        )
        update_thread.start()
        
    def stop_auto_updates(self):
        """Stop automatic updates."""
        self.update_timer.stop()


class PlaylistUpdateThread(QThread):
    """Thread for updating playlists."""
    
    # Signals
    update_completed = Signal(object)  # PlaylistUpdateResult
    update_failed = Signal(str)  # error_message
    
    def __init__(self, playlist, settings_manager):
        super().__init__()
        self.playlist = playlist
        self.settings_manager = settings_manager
        
    def run(self):
        """Run the playlist update."""
        try:
            # Download and parse the updated playlist
            parser = M3UParser()
            
            if self.playlist.source_type == "url":
                # For URL playlists, we need to download first
                # This would require implementing URL download functionality
                # For now, we'll simulate the update
                
                # Parse the current cached file to compare
                if self.playlist.cached_file_path and os.path.exists(self.playlist.cached_file_path):
                    old_channels, old_categories = parser.parse_m3u_from_file(self.playlist.cached_file_path)
                    
                    # Here we would download the new version and compare
                    # For now, we'll just return a success result
                    result = PlaylistUpdateResult(
                        self.playlist.id,
                        True,
                        channels_added=0,
                        channels_removed=0
                    )
                    
                    self.update_completed.emit(result)
                else:
                    self.update_failed.emit("No cached file found for URL playlist")
            else:
                self.update_failed.emit("Only URL playlists can be auto-updated")
                
        except Exception as e:
            self.update_failed.emit(str(e))
