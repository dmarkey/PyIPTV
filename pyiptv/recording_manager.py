"""
Recording management for PyIPTV.

This module provides comprehensive recording functionality including:
- Stream recording with multiple formats
- Scheduled recording with timer support
- Recording session management
- Recording quality and format selection
- Recording metadata and organization
"""

import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from enum import Enum


class RecordingStatus(Enum):
    """Recording status enumeration."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class RecordingFormat(Enum):
    """Supported recording formats."""
    MP4 = "mp4"
    MKV = "mkv"
    TS = "ts"
    FLV = "flv"


@dataclass
class RecordingSession:
    """Represents a recording session."""
    id: str
    channel_name: str
    stream_url: str
    output_path: str
    format: RecordingFormat
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: RecordingStatus = RecordingStatus.IDLE
    file_size_bytes: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if recording is currently active."""
        return self.status in [RecordingStatus.RECORDING, RecordingStatus.PAUSED]
    
    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        if self.duration_seconds:
            hours = self.duration_seconds // 3600
            minutes = (self.duration_seconds % 3600) // 60
            seconds = self.duration_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    @property
    def file_size_str(self) -> str:
        """Get formatted file size string."""
        if self.file_size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(self.file_size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.1f} {units[unit_index]}"


@dataclass
class ScheduledRecording:
    """Represents a scheduled recording."""
    id: str
    channel_name: str
    stream_url: str
    start_time: datetime
    duration_minutes: int
    output_path: str
    format: RecordingFormat
    repeat_weekly: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def end_time(self) -> datetime:
        """Calculate end time based on start time and duration."""
        return self.start_time + timedelta(minutes=self.duration_minutes)
    
    @property
    def is_due(self) -> bool:
        """Check if recording is due to start."""
        return datetime.now() >= self.start_time


class StreamRecorder:
    """Handles actual stream recording using ffmpeg."""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_recording = False
        
    def start_recording(
        self, 
        stream_url: str, 
        output_path: str, 
        format: RecordingFormat,
        quality: str = "copy"
    ) -> bool:
        """Start recording a stream."""
        if self.is_recording:
            return False
            
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Build ffmpeg command
            cmd = self._build_ffmpeg_command(stream_url, output_path, format, quality)
            
            # Start ffmpeg process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.is_recording = True
            return True
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop the current recording."""
        if not self.is_recording or not self.process:
            return False
            
        try:
            # Send SIGTERM to ffmpeg for graceful shutdown
            self.process.terminate()
            
            # Wait for process to finish (with timeout)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                self.process.kill()
                self.process.wait()
                
            self.is_recording = False
            self.process = None
            return True
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return False
    
    def _build_ffmpeg_command(
        self, 
        stream_url: str, 
        output_path: str, 
        format: RecordingFormat,
        quality: str
    ) -> List[str]:
        """Build ffmpeg command for recording."""
        cmd = [
            "ffmpeg",
            "-i", stream_url,
            "-c", quality,  # codec (copy for stream copy, or specific codec)
            "-f", format.value,
            "-y",  # Overwrite output file
            output_path
        ]
        
        # Add format-specific options
        if format == RecordingFormat.MP4:
            cmd.extend(["-movflags", "faststart"])
        elif format == RecordingFormat.TS:
            cmd.extend(["-bsf:v", "h264_mp4toannexb"])
            
        return cmd
    
    def get_recording_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current recording."""
        if not self.is_recording or not self.process:
            return None
            
        return {
            "pid": self.process.pid,
            "is_running": self.process.poll() is None,
            "return_code": self.process.returncode
        }


class RecordingManager(QObject):
    """Manages recording sessions and scheduling."""
    
    # Signals
    recording_started = Signal(str)  # session_id
    recording_stopped = Signal(str)  # session_id
    recording_failed = Signal(str, str)  # session_id, error_message
    recording_progress = Signal(str, int, int)  # session_id, duration_seconds, file_size_bytes
    scheduled_recording_triggered = Signal(str)  # scheduled_recording_id
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.active_sessions: Dict[str, RecordingSession] = {}
        self.scheduled_recordings: Dict[str, ScheduledRecording] = {}
        self.recorders: Dict[str, StreamRecorder] = {}
        
        # Timer for checking scheduled recordings
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self._check_scheduled_recordings)
        self.schedule_timer.start(60000)  # Check every minute
        
        # Timer for updating recording progress
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_recording_progress)
        self.progress_timer.start(5000)  # Update every 5 seconds
        
        # Default recording settings
        self.default_output_dir = self._get_default_output_directory()
        self.default_format = RecordingFormat.MP4
        
    def start_recording(
        self, 
        channel_name: str, 
        stream_url: str,
        duration_minutes: Optional[int] = None,
        output_path: Optional[str] = None,
        format: RecordingFormat = None
    ) -> Optional[str]:
        """Start a new recording session."""
        if not self._check_ffmpeg_available():
            return None
            
        # Generate session ID
        session_id = f"rec_{int(time.time())}"
        
        # Use defaults if not specified
        if format is None:
            format = self.default_format
            
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{channel_name}_{timestamp}.{format.value}"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            output_path = os.path.join(self.default_output_dir, filename)
        
        # Create recording session
        session = RecordingSession(
            id=session_id,
            channel_name=channel_name,
            stream_url=stream_url,
            output_path=output_path,
            format=format,
            start_time=datetime.now(),
            duration_seconds=duration_minutes * 60 if duration_minutes else None
        )
        
        # Create recorder
        recorder = StreamRecorder()
        
        # Start recording
        if recorder.start_recording(stream_url, output_path, format):
            session.status = RecordingStatus.RECORDING
            self.active_sessions[session_id] = session
            self.recorders[session_id] = recorder
            
            # Schedule stop if duration specified
            if duration_minutes:
                QTimer.singleShot(
                    duration_minutes * 60 * 1000,  # Convert to milliseconds
                    lambda: self.stop_recording(session_id)
                )
            
            self.recording_started.emit(session_id)
            return session_id
        else:
            session.status = RecordingStatus.FAILED
            session.error_message = "Failed to start ffmpeg process"
            self.recording_failed.emit(session_id, session.error_message)
            return None
    
    def stop_recording(self, session_id: str) -> bool:
        """Stop a recording session."""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        recorder = self.recorders.get(session_id)
        
        if recorder and recorder.stop_recording():
            session.status = RecordingStatus.COMPLETED
            session.end_time = datetime.now()
            
            # Calculate final duration
            if session.end_time and session.start_time:
                duration = session.end_time - session.start_time
                session.duration_seconds = int(duration.total_seconds())
            
            # Get final file size
            if os.path.exists(session.output_path):
                session.file_size_bytes = os.path.getsize(session.output_path)
            
            # Clean up
            del self.recorders[session_id]
            
            self.recording_stopped.emit(session_id)
            return True
        else:
            session.status = RecordingStatus.FAILED
            session.error_message = "Failed to stop recording"
            self.recording_failed.emit(session_id, session.error_message)
            return False
    
    def schedule_recording(
        self,
        channel_name: str,
        stream_url: str,
        start_time: datetime,
        duration_minutes: int,
        format: RecordingFormat = None,
        repeat_weekly: bool = False
    ) -> str:
        """Schedule a recording."""
        if format is None:
            format = self.default_format
            
        # Generate scheduled recording ID
        scheduled_id = f"sched_{int(time.time())}"
        
        # Create output path
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{channel_name}_{timestamp}.{format.value}"
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        output_path = os.path.join(self.default_output_dir, filename)
        
        # Create scheduled recording
        scheduled_recording = ScheduledRecording(
            id=scheduled_id,
            channel_name=channel_name,
            stream_url=stream_url,
            start_time=start_time,
            duration_minutes=duration_minutes,
            output_path=output_path,
            format=format,
            repeat_weekly=repeat_weekly
        )
        
        self.scheduled_recordings[scheduled_id] = scheduled_recording
        return scheduled_id
    
    def cancel_scheduled_recording(self, scheduled_id: str) -> bool:
        """Cancel a scheduled recording."""
        if scheduled_id in self.scheduled_recordings:
            del self.scheduled_recordings[scheduled_id]
            return True
        return False
    
    def get_active_sessions(self) -> List[RecordingSession]:
        """Get all active recording sessions."""
        return [session for session in self.active_sessions.values() 
                if session.status == RecordingStatus.RECORDING]
    
    def get_all_sessions(self) -> List[RecordingSession]:
        """Get all recording sessions."""
        return list(self.active_sessions.values())
    
    def get_scheduled_recordings(self) -> List[ScheduledRecording]:
        """Get all scheduled recordings."""
        return list(self.scheduled_recordings.values())
    
    def _check_scheduled_recordings(self):
        """Check for due scheduled recordings."""
        current_time = datetime.now()
        
        for scheduled_id, scheduled_rec in list(self.scheduled_recordings.items()):
            if scheduled_rec.is_due:
                # Start the recording
                session_id = self.start_recording(
                    scheduled_rec.channel_name,
                    scheduled_rec.stream_url,
                    scheduled_rec.duration_minutes,
                    scheduled_rec.output_path,
                    scheduled_rec.format
                )
                
                if session_id:
                    self.scheduled_recording_triggered.emit(scheduled_id)
                
                # Handle weekly repeat
                if scheduled_rec.repeat_weekly:
                    # Schedule for next week
                    scheduled_rec.start_time += timedelta(weeks=1)
                    # Update output path for next week
                    timestamp = scheduled_rec.start_time.strftime("%Y%m%d_%H%M%S")
                    filename = f"{scheduled_rec.channel_name}_{timestamp}.{scheduled_rec.format.value}"
                    filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                    scheduled_rec.output_path = os.path.join(self.default_output_dir, filename)
                else:
                    # Remove one-time scheduled recording
                    del self.scheduled_recordings[scheduled_id]
    
    def _update_recording_progress(self):
        """Update progress for active recordings."""
        for session_id, session in self.active_sessions.items():
            if session.status == RecordingStatus.RECORDING:
                # Update duration
                if session.start_time:
                    duration = datetime.now() - session.start_time
                    session.duration_seconds = int(duration.total_seconds())
                
                # Update file size
                if os.path.exists(session.output_path):
                    session.file_size_bytes = os.path.getsize(session.output_path)
                
                self.recording_progress.emit(
                    session_id, 
                    session.duration_seconds or 0, 
                    session.file_size_bytes
                )
    
    def _get_default_output_directory(self) -> str:
        """Get default output directory for recordings."""
        # Try to get from settings first
        output_dir = self.settings_manager.get_setting("recording_output_dir")
        
        if not output_dir:
            # Use default based on OS
            if os.name == 'nt':  # Windows
                output_dir = os.path.join(os.path.expanduser("~"), "Videos", "PyIPTV Recordings")
            else:  # Linux/macOS
                output_dir = os.path.join(os.path.expanduser("~"), "Videos", "PyIPTV Recordings")
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def _check_ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
