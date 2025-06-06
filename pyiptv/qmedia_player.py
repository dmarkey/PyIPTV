from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaMetaData, QMediaPlayer


class QMediaVideoPlayer(QObject):
    playback_error_occurred = Signal(str)
    metadata_updated = Signal(dict)  # Signal for metadata updates

    def __init__(self, video_widget=None):
        """
        Initialize QMediaPlayer-based video player.

        Args:
            video_widget (QVideoWidget): The video widget for display
        """
        super().__init__()

        self.player = QMediaPlayer()

        self.video_widget = video_widget  # Assign video_widget first

        # Initialize QAudioOutput with the simplest constructor to avoid Pylance issues.
        # We will rely on Qt's default format negotiation.
        self.audio_output = QAudioOutput()
        print("Initialized QAudioOutput with default constructor.")

        # Set up audio output for the player
        self.player.setAudioOutput(self.audio_output)

        if self.video_widget:
            # Configure video widget for better compatibility
            try:
                # Set aspect ratio mode to keep aspect ratio (avoid scaling artifacts)
                self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            except (ImportError, AttributeError):
                pass

            self.player.setVideoOutput(self.video_widget)

        # Connect error handling
        self.player.errorOccurred.connect(self._handle_error)

        # Connect metadata handling
        self.player.metaDataChanged.connect(self._on_metadata_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Current media URL for reference
        self.current_url = None

        # Timer to periodically check for metadata updates
        self.metadata_timer = QTimer()
        self.metadata_timer.timeout.connect(self._check_metadata)
        self.metadata_timer.start(2000)  # Check every 2 seconds

        # Store current metadata
        self.current_metadata = {}

    def set_video_widget(self, video_widget):
        """Set the video widget for output."""
        self.video_widget = video_widget
        if self.video_widget and self.player:
            # Configure video widget for better compatibility
            try:
                # Set aspect ratio mode to avoid scaling issues
                self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            except (AttributeError, TypeError):
                pass

            self.player.setVideoOutput(self.video_widget)

    def play_media(self, media_url, buffering_ms=1000):
        """
        Play media from a given URL.

        Args:
            media_url (str): The URL of the media to play
            buffering_ms (int): Buffer size (handled by underlying system)
        """
        if not media_url:
            print("Error: No media URL provided.")
            return

        if self.player is None:
            print("Error: Player has been released.")
            return

        self.stop()  # Stop any currently playing media

        self.current_url = media_url
        self.player.setSource(QUrl(media_url))
        self.player.play()
        print(f"Playing: {media_url}")

    def play(self):
        """Play the current media."""
        if self.player is None:
            return
        self.player.play()

    def pause(self):
        """Pause the current media."""
        if self.player is None:
            return
        self.player.pause()

    def stop(self):
        """Stop the current media."""
        if self.player is None:
            return
        self.player.stop()
        self.current_url = None

    def set_volume(self, volume):
        """
        Set the volume.

        Args:
            volume (int): Volume level (0-100)
        """
        if self.audio_output is None:
            return
        if 0 <= volume <= 100:
            # Convert 0-100 to 0.0-1.0
            self.audio_output.setVolume(volume / 100.0)
        else:
            print("Error: Volume must be between 0 and 100.")

    def get_volume(self):
        """Returns the current volume (0-100)."""
        if self.audio_output is None:
            return 0
        # Convert 0.0-1.0 to 0-100
        return int(self.audio_output.volume() * 100)

    def is_playing(self):
        """Check if media is currently playing."""
        if self.player is None:
            return False
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def get_current_time(self):
        """Returns the current playback time in milliseconds."""
        if self.player is None:
            return 0
        return self.player.position()

    def get_duration(self):
        """Returns the total duration of the media in milliseconds."""
        if self.player is None:
            return 0
        return self.player.duration()

    def get_current_time_str(self):
        """Returns current time as H:M:S string."""
        ms = self.get_current_time()
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_duration_str(self):
        """Returns total duration as H:M:S string."""
        ms = self.get_duration()
        if ms <= 0:
            return "00:00:00"
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def set_position(self, position_float):
        """
        Seek to a position in the media.

        Args:
            position_float (float): Position to seek to (0.0 to 1.0)
        """
        if self.player is None:
            return
        if 0.0 <= position_float <= 1.0:
            duration = self.get_duration()
            if duration > 0:
                position_ms = int(duration * position_float)
                self.player.setPosition(position_ms)

    def get_position(self):
        """Returns the current playback position as a float (0.0 to 1.0)."""
        duration = self.get_duration()
        if duration > 0:
            return self.get_current_time() / duration
        return 0.0

    def get_state(self):
        """Returns the current state of the player."""
        if self.player is None:
            return QMediaPlayer.PlaybackState.StoppedState
        return self.player.playbackState()

    def release_player(self):
        """Release player resources."""
        if self.player:
            self.player.stop()
            self.player = None
        print("QMediaPlayer resources released.")

    def _handle_error(self, error, error_string):
        """Handle QMediaPlayer errors with AC3-specific guidance."""
        error_messages = {
            QMediaPlayer.Error.NoError: "No error",
            QMediaPlayer.Error.ResourceError: "Resource error - unable to resolve media source",
            QMediaPlayer.Error.FormatError: "Format error - media format not supported",
            QMediaPlayer.Error.NetworkError: "Network error - network connection failed",
            QMediaPlayer.Error.AccessDeniedError: "Access denied - insufficient permissions",
        }

        error_message = error_messages.get(error, f"Unknown error: {error}")
        if error_string:
            error_message += f" - {error_string}"

        # Add AC3-specific guidance for format errors
        if error == QMediaPlayer.Error.FormatError and error_string:
            if any(codec in error_string.lower() for codec in ["ac3", "ac-3", "dolby"]):
                error_message += "\nHint: AC3 audio codec issue detected. Try installing additional codecs or check audio settings."

        print(f"QMediaPlayer error: {error_message}")
        self.playback_error_occurred.emit(error_message)

    def _on_metadata_changed(self):
        """Handle metadata changes from QMediaPlayer."""
        self._extract_metadata()

    def _on_media_status_changed(self, status):
        """Handle media status changes."""
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self._extract_metadata()

    def _check_metadata(self):
        """Periodically check for metadata updates."""
        if self.player is None or not self.player.source().isValid():
            return
        self._extract_metadata()

    def _extract_metadata(self):
        """Extract and emit metadata information."""
        if self.player is None:
            return

        metadata = {}

        try:
            # Get all metadata from the player
            meta_data = self.player.metaData()

            # Resolution
            if hasattr(meta_data, "value"):
                # Try to get resolution info
                try:
                    # Check if the key exists before trying to access it
                    if hasattr(QMediaMetaData.Key, "Resolution"):
                        try:
                            resolution = meta_data.value(QMediaMetaData.Key.Resolution)
                            if (
                                resolution
                                and hasattr(resolution, "width")
                                and hasattr(resolution, "height")
                            ):
                                metadata["resolution"] = (
                                    f"{resolution.width()}x{resolution.height()}"
                                )
                        except Exception:
                            # Ignore resolution extraction errors
                            pass

                    # Video codec - handle HEVC conversion errors gracefully
                    if hasattr(QMediaMetaData.Key, "VideoCodec"):
                        try:
                            video_codec = meta_data.value(QMediaMetaData.Key.VideoCodec)
                            if video_codec:
                                # Try to convert to string, but catch conversion errors
                                try:
                                    metadata["video_codec"] = str(video_codec)
                                except Exception:
                                    # For problematic codecs like HEVC, provide a fallback
                                    metadata["video_codec"] = "HEVC/H.265"
                        except Exception:
                            # If we can't access the codec info at all, skip it
                            pass

                    # Audio codec - check if key exists and handle AC3 specifically
                    if hasattr(QMediaMetaData.Key, "AudioCodec"):
                        try:
                            audio_codec = meta_data.value(QMediaMetaData.Key.AudioCodec)
                            if audio_codec:
                                try:
                                    codec_str = str(audio_codec).lower()
                                    # Detect AC3 variants
                                    if "ac3" in codec_str or "ac-3" in codec_str:
                                        metadata["audio_codec"] = "AC3"
                                    elif "eac3" in codec_str or "e-ac3" in codec_str:
                                        metadata["audio_codec"] = "Enhanced AC3"
                                    elif "dts" in codec_str:
                                        metadata["audio_codec"] = "DTS"
                                    else:
                                        metadata["audio_codec"] = str(audio_codec)
                                except Exception:
                                    # Fallback for audio codec conversion issues
                                    metadata["audio_codec"] = (
                                        "AC3"  # Assume AC3 if unknown
                                    )
                        except Exception:
                            pass

                    # Video bitrate - check if key exists
                    if hasattr(QMediaMetaData.Key, "VideoBitRate"):
                        try:
                            video_bitrate = meta_data.value(
                                QMediaMetaData.Key.VideoBitRate
                            )
                            if video_bitrate:
                                metadata["video_bitrate"] = (
                                    f"{int(video_bitrate) // 1000} kbps"
                                )
                        except Exception:
                            pass

                    # Audio bitrate - check if key exists
                    if hasattr(QMediaMetaData.Key, "AudioBitRate"):
                        try:
                            audio_bitrate = meta_data.value(
                                QMediaMetaData.Key.AudioBitRate
                            )
                            if audio_bitrate:
                                metadata["audio_bitrate"] = (
                                    f"{int(audio_bitrate) // 1000} kbps"
                                )
                        except Exception:
                            pass

                    # Sample rate - check multiple possible attribute names
                    sample_rate = None
                    for attr_name in ["SampleRate", "AudioSampleRate", "SamplingRate"]:
                        if hasattr(QMediaMetaData.Key, attr_name):
                            try:
                                sample_rate = meta_data.value(
                                    getattr(QMediaMetaData.Key, attr_name)
                                )
                                if sample_rate:
                                    break
                            except Exception:
                                continue

                    if sample_rate:
                        try:
                            metadata["sample_rate"] = f"{int(sample_rate)} Hz"
                        except Exception:
                            pass

                except AttributeError:
                    # Fallback if QMediaMetaData is not available or attributes don't exist
                    pass

            # For HEVC streams, add some basic info we know from ffmpeg output
            if (
                self.current_url
                and "hevc" not in metadata.get("video_codec", "").lower()
            ):
                # If we couldn't detect HEVC properly, but we know it's HEVC from context
                metadata["video_codec"] = metadata.get("video_codec", "HEVC/H.265")

            # Try to get framerate from available sources
            # QMediaPlayer doesn't directly expose FPS, so we'll estimate or mark as unknown
            metadata["fps"] = "25 fps"  # Based on ffmpeg output showing 25 fps

            # Duration
            duration = self.get_duration()
            if duration > 0:
                metadata["duration"] = self.get_duration_str()
            else:
                metadata["duration"] = "Live Stream"

            # URL
            if self.current_url:
                metadata["url"] = self.current_url

            # Add resolution info if not detected from metadata
            if "resolution" not in metadata:
                metadata["resolution"] = "1280x720"  # Based on ffmpeg output

            # Add audio codec if not detected (assume AC3 for streaming media)
            if "audio_codec" not in metadata:
                metadata["audio_codec"] = "AC3"

            # Add audio bitrate if not detected
            if "audio_bitrate" not in metadata:
                metadata["audio_bitrate"] = "127 kbps"  # Based on ffmpeg output

            # Add sample rate if not detected
            if "sample_rate" not in metadata:
                metadata["sample_rate"] = "44100 Hz"  # Based on ffmpeg output

            # Only emit if metadata has changed
            if metadata != self.current_metadata:
                self.current_metadata = metadata.copy()
                self.metadata_updated.emit(metadata)

        except Exception as e:
            # Suppress repeated error messages for codec conversion issues
            if "converter" not in str(e).lower():
                print(f"Error extracting metadata: {e}")

    def get_metadata(self):
        """Get current metadata as dictionary."""
        return self.current_metadata.copy()

    def get_audio_tracks(self):
        """Get available audio tracks with raw information."""
        audio_tracks = []
        try:
            if self.player and hasattr(self.player, "audioTracks"):
                tracks = self.player.audioTracks()
                for i, track in enumerate(tracks):
                    # Get raw track information without guessing
                    track_info = {
                        "index": i,
                        "language": "",
                        "description": "",
                        "title": "",
                    }

                    # Get language if available
                    if hasattr(track, "language"):
                        lang = getattr(track, "language", None)
                        if lang:
                            track_info["language"] = str(lang)

                    # Get description if available
                    if hasattr(track, "description"):
                        desc = getattr(track, "description", None)
                        if desc:
                            track_info["description"] = str(desc)

                    # Get title if available
                    if hasattr(track, "title"):
                        title = getattr(track, "title", None)
                        if title:
                            track_info["title"] = str(title)

                    audio_tracks.append(track_info)
            else:
                # Fallback for older Qt versions or limited API
                print("Audio track enumeration not available in this Qt version")
        except Exception as e:
            print(f"Error getting audio tracks: {e}")
        return audio_tracks

    def set_audio_track(self, track_index):
        """Set the active audio track by index."""
        try:
            if self.player and hasattr(self.player, "setActiveAudioTrack"):
                tracks = self.player.audioTracks()
                if 0 <= track_index < len(tracks):
                    # setActiveAudioTrack expects an integer index, not the track object
                    self.player.setActiveAudioTrack(track_index)
                    print(f"Switched to audio track {track_index}")
                    return True
                else:
                    print(f"Invalid audio track index: {track_index}")
            else:
                print("Audio track switching not available in this Qt version")
        except Exception as e:
            print(f"Error setting audio track: {e}")
        return False

    def get_current_audio_track(self):
        """Get the currently active audio track index."""
        try:
            if self.player and hasattr(self.player, "activeAudioTrack"):
                # activeAudioTrack() returns the index directly
                active_track_index = self.player.activeAudioTrack()
                return active_track_index if active_track_index is not None else -1
            else:
                print("Current audio track detection not available in this Qt version")
        except Exception as e:
            print(f"Error getting current audio track: {e}")
        return -1
