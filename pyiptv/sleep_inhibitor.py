"""Prevent the display/system from sleeping while fullscreen video is playing.

macOS uses IOKit's IOPMAssertion. Linux/Windows are no-ops for now — can be
extended (systemd-inhibit on Linux, SetThreadExecutionState on Windows).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from typing import Optional

_DARWIN = sys.platform == "darwin"

# kIOPMAssertionTypePreventUserIdleDisplaySleep — the display (and therefore
# system) stays awake. kIOPMAssertionLevelOn = 255.
_ASSERTION_TYPE = b"PreventUserIdleDisplaySleep"
_ASSERTION_LEVEL_ON = 255
_CF_STRING_ENCODING_UTF8 = 0x08000100


class SleepInhibitor:
    """RAII-style sleep-inhibit toggle. Calling inhibit() twice is a no-op."""

    def __init__(self, reason: str = "PyIPTV is playing video"):
        self._reason = reason
        self._assertion_id: Optional[ctypes.c_uint32] = None
        self._iokit = None
        self._cf = None
        if _DARWIN:
            iokit = ctypes.util.find_library("IOKit")
            cf = ctypes.util.find_library("CoreFoundation")
            if iokit and cf:
                try:
                    self._iokit = ctypes.CDLL(iokit)
                    self._cf = ctypes.CDLL(cf)
                    self._iokit.IOPMAssertionCreateWithName.restype = ctypes.c_int
                    self._iokit.IOPMAssertionRelease.restype = ctypes.c_int
                    self._cf.CFStringCreateWithCString.restype = ctypes.c_void_p
                    self._cf.CFRelease.argtypes = [ctypes.c_void_p]
                except OSError:
                    self._iokit = None
                    self._cf = None

    def _cfstr(self, s: bytes) -> Optional[int]:
        if self._cf is None:
            return None
        return self._cf.CFStringCreateWithCString(
            None, s, _CF_STRING_ENCODING_UTF8
        )

    def inhibit(self) -> bool:
        """Create the assertion. Returns True if now inhibiting, False otherwise."""
        if self._assertion_id is not None:
            return True
        if self._iokit is None or self._cf is None:
            return False

        assertion_type = self._cfstr(_ASSERTION_TYPE)
        assertion_name = self._cfstr(self._reason.encode("utf-8"))
        if not assertion_type or not assertion_name:
            return False

        aid = ctypes.c_uint32(0)
        try:
            result = self._iokit.IOPMAssertionCreateWithName(
                ctypes.c_void_p(assertion_type),
                ctypes.c_uint32(_ASSERTION_LEVEL_ON),
                ctypes.c_void_p(assertion_name),
                ctypes.byref(aid),
            )
        finally:
            self._cf.CFRelease(assertion_type)
            self._cf.CFRelease(assertion_name)

        if result == 0:
            self._assertion_id = aid
            return True
        return False

    def release(self) -> None:
        if self._assertion_id is None or self._iokit is None:
            return
        self._iokit.IOPMAssertionRelease(self._assertion_id)
        self._assertion_id = None

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
