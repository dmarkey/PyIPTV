"""XMLTV parsing and now/next lookup for the Electronic Program Guide.

Xtream providers expose EPG via `xmltv.php?username=X&password=Y`. We pull
the whole dump once per hour, parse it into a per-channel sorted program
list keyed by XMLTV channel id (which matches `tvg-id` in the channel data),
and look up the current and upcoming program on demand.
"""

from __future__ import annotations

import bisect
import io
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

# (start_ts, stop_ts, title, description) — all ints for start/stop, strs for text.
EpgEntry = Tuple[int, int, str, str]

# Per-channel program list, sorted by start_ts ascending.
EpgIndex = Dict[str, List[EpgEntry]]


def parse_xmltv_datetime(s: str) -> int:
    """Parse an XMLTV datetime like '20260419220000 +0000' to a UTC unix timestamp.

    Accepts optional trailing offset. Returns 0 on unparseable input so callers
    can cheaply filter bad entries.
    """
    if not s:
        return 0
    parts = s.strip().split()
    date_part = parts[0]
    offset = parts[1] if len(parts) > 1 else "+0000"
    try:
        dt = datetime.strptime(date_part, "%Y%m%d%H%M%S")
        sign = 1 if offset.startswith("+") else -1
        hours = int(offset[1:3])
        minutes = int(offset[3:5])
        dt_utc = dt - sign * timedelta(minutes=hours * 60 + minutes)
        return int(dt_utc.replace(tzinfo=timezone.utc).timestamp())
    except (ValueError, IndexError):
        return 0


def parse_xmltv(content: bytes) -> EpgIndex:
    """Parse an XMLTV payload into a per-channel sorted program index.

    Uses streaming `iterparse` so large feeds (50–100MB) don't have to be
    fully materialised as an ElementTree. Programs with empty/zero timestamps
    or missing channel ids are dropped.
    """
    index: EpgIndex = {}
    stream = io.BytesIO(content)

    try:
        for _event, elem in ET.iterparse(stream, events=("end",)):
            if elem.tag != "programme":
                continue
            channel = elem.get("channel", "")
            start = parse_xmltv_datetime(elem.get("start", ""))
            stop = parse_xmltv_datetime(elem.get("stop", ""))
            if not channel or not start or not stop:
                elem.clear()
                continue
            title_el = elem.find("title")
            desc_el = elem.find("desc")
            title = (title_el.text or "") if title_el is not None else ""
            desc = (desc_el.text or "") if desc_el is not None else ""
            index.setdefault(channel, []).append((start, stop, title, desc))
            elem.clear()
    except ET.ParseError:
        # Return whatever we salvaged — some feeds end mid-stream.
        pass

    for programs in index.values():
        programs.sort(key=lambda p: p[0])
    return index


def find_current_next(
    programs: List[EpgEntry], now_ts: Optional[int] = None
) -> Tuple[Optional[EpgEntry], Optional[EpgEntry]]:
    """Return (current, next) for a channel. Either may be None.

    Uses binary search so per-channel lookups are O(log n), cheap enough to
    call from the virtualized channel list's paintEvent for every visible
    row on every repaint.
    """
    if not programs:
        return None, None
    if now_ts is None:
        now_ts = int(time.time())

    starts = [p[0] for p in programs]
    idx = bisect.bisect_right(starts, now_ts) - 1

    current: Optional[EpgEntry] = None
    if 0 <= idx < len(programs):
        prog = programs[idx]
        if prog[0] <= now_ts < prog[1]:
            current = prog

    next_idx = idx + 1
    next_: Optional[EpgEntry] = None
    if 0 <= next_idx < len(programs):
        candidate = programs[next_idx]
        if candidate[0] > now_ts:
            next_ = candidate

    return current, next_


def format_now_next(programs: List[EpgEntry], now_ts: Optional[int] = None) -> str:
    """Compact 'Now: X (HH:MM–HH:MM) · Next: Y' string. Empty if nothing known."""
    current, next_ = find_current_next(programs, now_ts=now_ts)
    parts: List[str] = []
    if current:
        start_s = datetime.fromtimestamp(current[0]).strftime("%H:%M")
        stop_s = datetime.fromtimestamp(current[1]).strftime("%H:%M")
        parts.append(f"Now: {current[2]} ({start_s}–{stop_s})")
    if next_:
        start_s = datetime.fromtimestamp(next_[0]).strftime("%H:%M")
        parts.append(f"Next: {next_[2]} ({start_s})")
    return " · ".join(parts)
