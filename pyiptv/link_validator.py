#!/usr/bin/env python3
"""
Link Validator for PyIPTV

This module provides functionality to validate IPTV stream links,
detect dead links, and automatically remove them from playlists.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Tuple, Optional, Callable
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication


class LinkValidationResult:
    """Result of link validation."""
    
    def __init__(self, url: str, is_valid: bool, response_time: float = 0.0, 
                 error_message: str = "", status_code: int = 0):
        self.url = url
        self.is_valid = is_valid
        self.response_time = response_time
        self.error_message = error_message
        self.status_code = status_code
        self.timestamp = time.time()


class AsyncLinkValidator(QObject):
    """Asynchronous link validator for IPTV streams."""
    
    # Signals
    validation_progress = Signal(int, int)  # current, total
    validation_completed = Signal(list)  # List of LinkValidationResult
    validation_failed = Signal(str)  # error message
    
    def __init__(self, timeout_seconds: int = 10, max_concurrent: int = 10):
        super().__init__()
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self.is_running = False
        
    async def validate_single_link(self, session: aiohttp.ClientSession, url: str) -> LinkValidationResult:
        """Validate a single link."""
        start_time = time.time()
        
        try:
            # For IPTV streams, we'll do a HEAD request first, then GET if needed
            async with session.head(url, timeout=self.timeout_seconds) as response:
                response_time = time.time() - start_time
                
                # Consider 200-299 and some 3xx as valid
                if response.status in range(200, 400):
                    return LinkValidationResult(url, True, response_time, "", response.status)
                else:
                    return LinkValidationResult(url, False, response_time, 
                                              f"HTTP {response.status}", response.status)
                    
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return LinkValidationResult(url, False, response_time, "Timeout")
            
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            return LinkValidationResult(url, False, response_time, str(e))
            
        except Exception as e:
            response_time = time.time() - start_time
            return LinkValidationResult(url, False, response_time, f"Unexpected error: {str(e)}")
    
    async def validate_links_batch(self, urls: List[str], 
                                 progress_callback: Optional[Callable] = None) -> List[LinkValidationResult]:
        """Validate multiple links with concurrency control."""
        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def validate_with_semaphore(session, url, index):
            async with semaphore:
                result = await self.validate_single_link(session, url)
                if progress_callback:
                    progress_callback(index + 1, len(urls))
                return result
        
        try:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                tasks = [
                    validate_with_semaphore(session, url, i) 
                    for i, url in enumerate(urls)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out exceptions and convert to proper results
                final_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        final_results.append(
                            LinkValidationResult(urls[i], False, 0.0, str(result))
                        )
                    else:
                        final_results.append(result)
                
                return final_results
                
        except Exception as e:
            raise Exception(f"Batch validation failed: {str(e)}")


class LinkValidatorThread(QThread):
    """Thread for running link validation."""
    
    # Signals
    progress_updated = Signal(int, int)  # current, total
    validation_completed = Signal(list)  # List of LinkValidationResult
    validation_failed = Signal(str)  # error message
    
    def __init__(self, urls: List[str], timeout_seconds: int = 10, max_concurrent: int = 10):
        super().__init__()
        self.urls = urls
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self.results = []
        
    def run(self):
        """Run the validation in a separate thread."""
        try:
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            validator = AsyncLinkValidator(self.timeout_seconds, self.max_concurrent)
            
            def progress_callback(current, total):
                self.progress_updated.emit(current, total)
                QApplication.processEvents()  # Keep UI responsive
            
            # Run validation
            self.results = loop.run_until_complete(
                validator.validate_links_batch(self.urls, progress_callback)
            )
            
            self.validation_completed.emit(self.results)
            
        except Exception as e:
            self.validation_failed.emit(str(e))
        finally:
            try:
                loop.close()
            except:
                pass


class DeadLinkManager(QObject):
    """Manager for dead link detection and removal."""
    
    # Signals
    dead_links_detected = Signal(list)  # List of dead channel info
    links_validated = Signal(int, int)  # valid_count, total_count
    validation_progress = Signal(int, int)  # current, total
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.validation_thread = None
        self.auto_check_timer = QTimer()
        self.auto_check_timer.timeout.connect(self.start_auto_validation)
        
        # Setup auto-checking if enabled
        self.setup_auto_checking()
        
    def setup_auto_checking(self):
        """Setup automatic dead link checking."""
        if self.settings_manager.get_setting("dead_link_detection"):
            interval_hours = self.settings_manager.get_setting("dead_link_check_interval_hours", 6)
            interval_ms = interval_hours * 60 * 60 * 1000  # Convert to milliseconds
            self.auto_check_timer.start(interval_ms)
            
    def validate_channels(self, channels: List[Dict]) -> None:
        """Start validation of channel links."""
        if self.validation_thread and self.validation_thread.isRunning():
            return  # Already running
            
        urls = [channel.get("url", "") for channel in channels if channel.get("url")]
        
        if not urls:
            return
            
        timeout = self.settings_manager.get_setting("dead_link_timeout_seconds", 10)
        
        self.validation_thread = LinkValidatorThread(urls, timeout)
        self.validation_thread.progress_updated.connect(self.validation_progress.emit)
        self.validation_thread.validation_completed.connect(self._on_validation_completed)
        self.validation_thread.validation_failed.connect(self._on_validation_failed)
        self.validation_thread.start()
        
    def _on_validation_completed(self, results: List[LinkValidationResult]):
        """Handle validation completion."""
        dead_links = [result for result in results if not result.is_valid]
        valid_count = len(results) - len(dead_links)
        
        self.links_validated.emit(valid_count, len(results))
        
        if dead_links:
            self.dead_links_detected.emit(dead_links)
            
    def _on_validation_failed(self, error_message: str):
        """Handle validation failure."""
        print(f"Link validation failed: {error_message}")
        
    def start_auto_validation(self):
        """Start automatic validation (called by timer)."""
        # This would be connected to the main window to trigger validation
        # Implementation depends on how we access the current channel list
        pass
        
    def stop_auto_checking(self):
        """Stop automatic checking."""
        self.auto_check_timer.stop()
        
    def get_dead_link_statistics(self) -> Dict:
        """Get statistics about dead links."""
        # This could be expanded to track historical data
        return {
            "last_check": time.time(),
            "total_checked": 0,
            "dead_count": 0,
            "valid_count": 0
        }
