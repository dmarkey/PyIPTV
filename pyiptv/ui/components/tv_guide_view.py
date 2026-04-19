"""Classic program-guide grid: time on X, channels on Y, programs as strips.

Custom-painted for performance — a 16,937-channel playlist can have hundreds
of thousands of program entries, but we only render visible rows and the
current time window so paint stays cheap. Vertical axis is virtualized (row
offset); horizontal axis is windowed (anchor time + fixed pixels-per-hour).
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pyiptv.logo_cache import shared as shared_logo_cache


class _GuideCanvas(QFrame):
    """Inner canvas that does all the painting and mouse handling."""

    program_clicked = Signal(dict, object, bool)  # channel, program, is_catchup

    ROW_HEIGHT = 56
    LOGO_COL_WIDTH = 240
    HEADER_HEIGHT = 36
    PX_PER_HOUR = 240
    PX_PER_SECOND = PX_PER_HOUR / 3600.0
    # Show 12h centred around roughly "an hour ago" by default so the user
    # can scroll back into catchup immediately.
    DEFAULT_WINDOW_START_OFFSET = -3600

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setMouseTracking(True)
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._channels: List[dict] = []
        self._epg: Dict[str, list] = {}
        self._anchor_ts: int = int(time.time()) + self.DEFAULT_WINDOW_START_OFFSET
        self._row_offset: int = 0
        self._hover: Optional[Tuple[int, tuple]] = None
        # Search highlight — set of program tuples drawn with accent colour.
        self._highlighted_programs: set = set()
        self._logo_cache = shared_logo_cache()
        self._logo_cache.logo_ready.connect(lambda _: self.update())

    # --- data ---

    def set_data(self, channels: List[dict], epg_index: Dict[str, list]) -> None:
        self._channels = channels or []
        self._epg = epg_index or {}
        self.update()

    def set_anchor_ts(self, ts: int) -> None:
        self._anchor_ts = int(ts)
        self.update()

    def set_row_offset(self, offset: int) -> None:
        self._row_offset = max(0, int(offset))
        self.update()

    def set_highlighted_programs(self, programs) -> None:
        """Highlight a set of program tuples (drawn with accent colour)."""
        self._highlighted_programs = set(programs or ())
        self.update()

    def anchor_ts(self) -> int:
        return self._anchor_ts

    def row_offset(self) -> int:
        return self._row_offset

    def total_rows(self) -> int:
        return len(self._channels)

    def visible_rows(self) -> int:
        grid_h = max(0, self.height() - self.HEADER_HEIGHT)
        return max(1, grid_h // self.ROW_HEIGHT)

    def window_seconds(self) -> int:
        grid_w = max(0, self.width() - self.LOGO_COL_WIDTH)
        return int(grid_w / self.PX_PER_SECOND)

    # --- paint ---

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        palette = self.palette()
        bg = palette.color(QPalette.ColorRole.Base)
        text = palette.color(QPalette.ColorRole.Text)
        highlight = palette.color(QPalette.ColorRole.Highlight)
        window_bg = palette.color(QPalette.ColorRole.Window)

        painter.fillRect(self.rect(), bg)

        self._paint_time_header(painter, text, window_bg)
        self._paint_channel_column(painter, text, window_bg)
        self._paint_grid(painter, text, highlight)
        self._paint_now_line(painter)

    def _paint_time_header(self, painter, text_color, window_bg):
        """Top strip with hour marks across the current window."""
        rect = QRect(
            self.LOGO_COL_WIDTH, 0, self.width() - self.LOGO_COL_WIDTH, self.HEADER_HEIGHT
        )
        painter.fillRect(rect, window_bg.darker(108))

        painter.save()
        # Hour ticks — first hour boundary at or after the anchor.
        first_hour = self._anchor_ts - (self._anchor_ts % 3600) + 3600
        hour = first_hour
        end_ts = self._anchor_ts + self.window_seconds()
        pen = QPen(text_color)
        pen.setColor(QColor(text_color.red(), text_color.green(), text_color.blue(), 140))
        painter.setPen(pen)
        font = painter.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        painter.setFont(font)
        fm = QFontMetrics(font)
        while hour <= end_ts:
            x = self.LOGO_COL_WIDTH + int((hour - self._anchor_ts) * self.PX_PER_SECOND)
            painter.drawLine(x, 0, x, self.HEADER_HEIGHT)
            label = datetime.fromtimestamp(hour).strftime("%H:%M")
            painter.drawText(x + 4, self.HEADER_HEIGHT - 10, label)
            # Also show the day label when crossing midnight.
            if datetime.fromtimestamp(hour).hour == 0:
                day_label = datetime.fromtimestamp(hour).strftime("%a %d %b")
                painter.drawText(x + 4, fm.ascent() + 2, day_label)
            hour += 3600
        painter.restore()

    def _paint_channel_column(self, painter, text_color, window_bg):
        """Left-hand pinned column with logo + channel name."""
        rect = QRect(0, 0, self.LOGO_COL_WIDTH, self.height())
        painter.fillRect(rect, window_bg.darker(112))

        painter.save()
        pen = QPen(text_color)
        painter.setPen(pen)
        font = painter.font()
        name_metrics = QFontMetrics(font)

        visible = self.visible_rows()
        end_row = min(self._row_offset + visible + 1, len(self._channels))
        logo_size = 36
        logo_pad = (self.ROW_HEIGHT - logo_size) // 2

        for i in range(self._row_offset, end_row):
            y = self.HEADER_HEIGHT + (i - self._row_offset) * self.ROW_HEIGHT
            row_rect = QRect(0, y, self.LOGO_COL_WIDTH, self.ROW_HEIGHT)
            # Separator line.
            painter.setPen(QColor(text_color.red(), text_color.green(), text_color.blue(), 35))
            painter.drawLine(0, y + self.ROW_HEIGHT - 1, self.LOGO_COL_WIDTH, y + self.ROW_HEIGHT - 1)
            painter.setPen(text_color)

            channel = self._channels[i]

            # Logo
            logo_url = channel.get("tvg-logo") or ""
            logo = self._logo_cache.request(logo_url) if logo_url else None
            logo_rect = QRect(12, y + logo_pad, logo_size, logo_size)
            if logo is not None and not logo.isNull():
                scaled = logo.scaled(
                    logo_size,
                    logo_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                dx = logo_rect.x() + (logo_size - scaled.width()) // 2
                dy = logo_rect.y() + (logo_size - scaled.height()) // 2
                painter.drawPixmap(dx, dy, scaled)

            # Name + catchup indicator
            label = channel.get("name", "Unknown")
            if int(channel.get("xtream_tv_archive", 0) or 0):
                label += "  ↻"
            text_rect = QRect(
                logo_rect.right() + 10,
                y,
                row_rect.width() - logo_rect.right() - 16,
                self.ROW_HEIGHT,
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter,
                name_metrics.elidedText(label, Qt.TextElideMode.ElideRight, text_rect.width()),
            )
        # Vertical divider between channel column and grid.
        painter.setPen(QColor(text_color.red(), text_color.green(), text_color.blue(), 80))
        painter.drawLine(
            self.LOGO_COL_WIDTH - 1, 0, self.LOGO_COL_WIDTH - 1, self.height()
        )
        painter.restore()

    def _paint_grid(self, painter, text_color, highlight):
        """The program strips themselves."""
        painter.save()
        now_ts = int(time.time())
        start_ts = self._anchor_ts
        end_ts = start_ts + self.window_seconds()

        font = painter.font()
        small_font = QFont(font)
        small_font.setPointSize(max(8, font.pointSize() - 1))
        small_metrics = QFontMetrics(small_font)

        visible = self.visible_rows()
        end_row = min(self._row_offset + visible + 1, len(self._channels))

        # Clip program painting to the grid area so strips can't spill into
        # the channel column.
        grid_rect = QRect(
            self.LOGO_COL_WIDTH,
            self.HEADER_HEIGHT,
            self.width() - self.LOGO_COL_WIDTH,
            self.height() - self.HEADER_HEIGHT,
        )
        painter.setClipRect(grid_rect)

        for i in range(self._row_offset, end_row):
            channel = self._channels[i]
            y = self.HEADER_HEIGHT + (i - self._row_offset) * self.ROW_HEIGHT
            tvg_id = (channel.get("tvg-id") or "").strip()
            programs = self._epg.get(tvg_id) or []

            has_archive = bool(int(channel.get("xtream_tv_archive", 0) or 0))

            for prog in programs:
                p_start, p_stop, p_title, _p_desc = prog
                if p_stop <= start_ts or p_start >= end_ts:
                    continue  # outside the window

                x = self.LOGO_COL_WIDTH + int((p_start - start_ts) * self.PX_PER_SECOND)
                w = max(2, int((p_stop - p_start) * self.PX_PER_SECOND))
                strip = QRect(x, y + 2, w, self.ROW_HEIGHT - 4)

                is_current = p_start <= now_ts < p_stop
                is_past = p_stop <= now_ts
                is_future = p_start > now_ts
                is_highlighted = prog in self._highlighted_programs

                # Base fill
                if is_highlighted:
                    # Warm amber accent — reads clearly over past/future base.
                    fill = QColor(255, 186, 73, 140)
                elif is_current:
                    fill = QColor(highlight.red(), highlight.green(), highlight.blue(), 110)
                elif is_past:
                    fill = QColor(text_color.red(), text_color.green(), text_color.blue(), 30)
                elif is_future:
                    fill = QColor(text_color.red(), text_color.green(), text_color.blue(), 18)
                else:
                    fill = QColor(0, 0, 0, 40)

                painter.fillRect(strip, fill)

                # Border — thicker amber stroke for highlighted programs so
                # they read at a glance even with tiny strips.
                if is_highlighted:
                    painter.setPen(QPen(QColor(255, 170, 40), 2))
                else:
                    border_color = QColor(
                        text_color.red(), text_color.green(), text_color.blue(), 80
                    )
                    painter.setPen(QPen(border_color, 1))
                painter.drawRect(strip)

                # Text
                inner = strip.adjusted(6, 2, -6, -2)
                painter.setPen(text_color)
                painter.setFont(small_font)
                # Title on first line if we have room, time on second line
                title_elided = small_metrics.elidedText(
                    p_title, Qt.TextElideMode.ElideRight, inner.width()
                )
                time_label = datetime.fromtimestamp(p_start).strftime("%H:%M")
                if has_archive and is_past:
                    time_label = "↻ " + time_label
                if inner.height() >= 2 * small_metrics.height() and inner.width() > 30:
                    painter.drawText(inner, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, title_elided)
                    painter.drawText(
                        inner,
                        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                        small_metrics.elidedText(time_label, Qt.TextElideMode.ElideRight, inner.width()),
                    )
                elif inner.width() > 20:
                    painter.drawText(
                        inner,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                        title_elided,
                    )

        painter.restore()

    def _paint_now_line(self, painter):
        """Red vertical line showing the current time position."""
        now_ts = int(time.time())
        if now_ts < self._anchor_ts or now_ts > self._anchor_ts + self.window_seconds():
            return
        x = self.LOGO_COL_WIDTH + int((now_ts - self._anchor_ts) * self.PX_PER_SECOND)
        painter.save()
        painter.setPen(QPen(QColor(220, 60, 60), 2))
        painter.drawLine(x, 0, x, self.height())
        painter.restore()

    # --- mouse ---

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if pos.x() < self.LOGO_COL_WIDTH or pos.y() < self.HEADER_HEIGHT:
            return

        row_idx = self._row_offset + (pos.y() - self.HEADER_HEIGHT) // self.ROW_HEIGHT
        if row_idx < 0 or row_idx >= len(self._channels):
            return
        channel = self._channels[row_idx]

        clicked_ts = self._anchor_ts + (pos.x() - self.LOGO_COL_WIDTH) / self.PX_PER_SECOND
        tvg_id = (channel.get("tvg-id") or "").strip()
        programs = self._epg.get(tvg_id) or []

        hit = None
        for prog in programs:
            if prog[0] <= clicked_ts < prog[1]:
                hit = prog
                break

        now_ts = int(time.time())
        has_archive = bool(int(channel.get("xtream_tv_archive", 0) or 0))
        if hit is None:
            # No program info — just tune to the channel (live).
            self.program_clicked.emit(channel, None, False)
            return
        is_past = hit[1] <= now_ts
        is_catchup = is_past and has_archive
        self.program_clicked.emit(channel, hit, is_catchup)


class TvGuideView(QWidget):
    """Classic TV-guide grid with horizontal and vertical scrollbars.

    API:
      set_data(channels: list[dict], epg_index: dict[str, list])
      program_clicked signal → (channel_dict, program_tuple|None, is_catchup: bool)
      jump_to_now() — reset anchor to ~1h before current time
    """

    program_clicked = Signal(dict, object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_channels = []
        self._epg_index = {}
        self._canvas = _GuideCanvas(self)
        self._canvas.program_clicked.connect(self.program_clicked)

        self._v_scroll = QScrollBar(Qt.Orientation.Vertical, self)
        self._h_scroll = QScrollBar(Qt.Orientation.Horizontal, self)
        self._v_scroll.valueChanged.connect(self._on_v_scroll)
        self._h_scroll.valueChanged.connect(self._on_h_scroll)

        # Top toolbar — makes scroll-back discoverable. Back/Now/Forward
        # buttons plus a running label of the visible time range.
        self._toolbar = QWidget(self)
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(6)

        self._back_btn = QPushButton("◀ Back")
        self._back_btn.setToolTip("Go back 2 hours")
        self._back_btn.clicked.connect(lambda: self._h_scroll.setValue(
            self._h_scroll.value() - 8
        ))
        self._back_2d_btn = QPushButton("◀◀ 1d")
        self._back_2d_btn.setToolTip("Go back 1 day (where catchup is available)")
        self._back_2d_btn.clicked.connect(lambda: self._h_scroll.setValue(
            self._h_scroll.value() - 96
        ))
        self._now_btn = QPushButton("● Now")
        self._now_btn.setToolTip("Jump to the current time (Home)")
        self._now_btn.clicked.connect(self.jump_to_now)
        self._fwd_btn = QPushButton("Forward ▶")
        self._fwd_btn.setToolTip("Go forward 2 hours")
        self._fwd_btn.clicked.connect(lambda: self._h_scroll.setValue(
            self._h_scroll.value() + 8
        ))
        self._catchup_filter = QPushButton("↻ Catchup only")
        self._catchup_filter.setToolTip(
            "Show only channels that support timeshift / catchup playback"
        )
        self._catchup_filter.setCheckable(True)
        self._catchup_filter.toggled.connect(self._on_catchup_filter_toggled)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search programs… (e.g. 'snooker')")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setMaximumWidth(280)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        # Debounce search so typing doesn't scan 225k programs per keystroke.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._run_search)

        self._range_label = QLabel("")
        self._range_label.setStyleSheet("color: rgba(200, 200, 200, 180);")

        toolbar_layout.addWidget(self._back_2d_btn)
        toolbar_layout.addWidget(self._back_btn)
        toolbar_layout.addWidget(self._now_btn)
        toolbar_layout.addWidget(self._fwd_btn)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self._catchup_filter)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self._range_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self._search_input)

        # Small summary strip shown above the grid while a search is active.
        self._search_summary = QLabel("")
        self._search_summary.setStyleSheet(
            "padding: 4px 12px; color: rgba(255, 186, 73, 220);"
        )
        self._search_summary.setVisible(False)

        # Grid:  toolbar
        #        search summary (when search active)
        #        canvas | v_scroll
        #        h_scroll | (corner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._toolbar)
        root.addWidget(self._search_summary)

        inner = QGridLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        inner.addWidget(self._canvas, 0, 0)
        inner.addWidget(self._v_scroll, 0, 1)
        inner.addWidget(self._h_scroll, 1, 0)
        root.addLayout(inner, 1)

        self._h_step_seconds = 900  # 15 min per scrollbar tick
        self._h_range_seconds = 48 * 3600  # 48h total scrollable (24 back, 24 ahead)
        self._h_scroll.setMinimum(0)
        self._h_scroll.setMaximum(self._h_range_seconds // self._h_step_seconds)
        self._h_scroll.setSingleStep(1)
        self._h_scroll.setPageStep(8)  # 2 hours
        self._h_scroll.valueChanged.connect(self._update_range_label)

    def set_data(self, channels, epg_index):
        self._all_channels = list(channels or [])
        self._epg_index = epg_index or {}
        self._apply_catchup_filter()
        self.jump_to_now()

    def _apply_catchup_filter(self):
        """Push the current filter state into the canvas."""
        catchup_only = (
            self._catchup_filter.isChecked()
            if hasattr(self, "_catchup_filter")
            else False
        )
        if catchup_only:
            filtered = [
                c for c in self._all_channels
                if int(c.get("xtream_tv_archive", 0) or 0)
            ]
        else:
            filtered = self._all_channels
        self._canvas.set_data(filtered, self._epg_index)
        self._update_scrollbars()

    def _on_catchup_filter_toggled(self, _checked):
        self._apply_catchup_filter()
        # After filter flips, scroll back to top so the user starts at the
        # beginning of the filtered list rather than a stale offset.
        self._v_scroll.setValue(0)

    # --- global search ---

    def _on_search_text_changed(self, _text):
        self._search_timer.start()

    def _run_search(self):
        query = self._search_input.text().strip().lower()
        if not query:
            # Clear search: drop highlights, restore the regular filter scope.
            self._canvas.set_highlighted_programs(set())
            self._search_summary.setVisible(False)
            self._apply_catchup_filter()
            return

        # Walk every channel in the playlist once, record matching programs.
        channels_with_matches: List[dict] = []
        highlights: set = set()
        earliest_match_ts: Optional[int] = None
        total_match_count = 0

        for channel in self._all_channels:
            tvg_id = (channel.get("tvg-id") or "").strip()
            if not tvg_id:
                continue
            programs = self._epg_index.get(tvg_id)
            if not programs:
                continue
            channel_had_match = False
            for prog in programs:
                _start, _stop, title, desc = prog
                hay = (title + " " + (desc or "")).lower()
                if query in hay:
                    highlights.add(prog)
                    total_match_count += 1
                    channel_had_match = True
                    if earliest_match_ts is None or _start < earliest_match_ts:
                        earliest_match_ts = _start
            if channel_had_match:
                channels_with_matches.append(channel)

        # Show only the channels that match; keep all their programs so the
        # user can see context around each highlighted slot.
        self._canvas.set_data(channels_with_matches, self._epg_index)
        self._canvas.set_highlighted_programs(highlights)
        self._update_scrollbars()
        self._v_scroll.setValue(0)

        if earliest_match_ts is not None:
            # Anchor so the earliest match is ~1/4 into the visible window.
            window = max(3600, self._canvas.window_seconds() or 3600)
            new_anchor = earliest_match_ts - window // 4
            self._canvas.set_anchor_ts(new_anchor)
            now_ts = int(time.time())
            h_anchor = now_ts - self._h_range_seconds // 2
            ticks = (new_anchor - h_anchor) // self._h_step_seconds
            self._h_scroll.blockSignals(True)
            self._h_scroll.setValue(
                max(0, min(self._h_scroll.maximum(), int(ticks)))
            )
            self._h_scroll.blockSignals(False)
        self._update_range_label()

        query_echo = self._search_input.text().strip()
        if total_match_count:
            plural_p = "s" if total_match_count != 1 else ""
            plural_c = "s" if len(channels_with_matches) != 1 else ""
            self._search_summary.setText(
                f"{total_match_count} programme{plural_p} on "
                f"{len(channels_with_matches)} channel{plural_c} match "
                f"'{query_echo}'"
            )
        else:
            self._search_summary.setText(f"No programmes match '{query_echo}'")
        self._search_summary.setVisible(True)

    def jump_to_now(self):
        # Anchor the window so "now" is 1/4 into the visible area.
        now_ts = int(time.time())
        window = max(3600, self._canvas.window_seconds() or 3600)
        anchor = now_ts - window // 4
        self._canvas.set_anchor_ts(anchor)
        # Sync the horizontal scrollbar to match.
        h_anchor = now_ts - self._h_range_seconds // 2
        ticks = (self._canvas.anchor_ts() - h_anchor) // self._h_step_seconds
        self._h_scroll.blockSignals(True)
        self._h_scroll.setValue(max(0, min(self._h_scroll.maximum(), int(ticks))))
        self._h_scroll.blockSignals(False)

    def _update_scrollbars(self):
        total = self._canvas.total_rows()
        visible = self._canvas.visible_rows()
        self._v_scroll.setMinimum(0)
        self._v_scroll.setMaximum(max(0, total - visible))
        self._v_scroll.setPageStep(visible)
        self._v_scroll.setSingleStep(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scrollbars()

    def showEvent(self, event):
        super().showEvent(event)
        # Re-anchor to "now" each time the guide is shown, so the red line
        # is always at the expected 1/4-in position regardless of prior scroll.
        self.jump_to_now()
        self._update_range_label()

    def _on_v_scroll(self, value):
        self._canvas.set_row_offset(value)

    def _on_h_scroll(self, value):
        now_ts = int(time.time())
        h_anchor = now_ts - self._h_range_seconds // 2
        new_anchor = h_anchor + value * self._h_step_seconds
        self._canvas.set_anchor_ts(new_anchor)

    def _update_range_label(self, *_):
        start = self._canvas.anchor_ts()
        end = start + self._canvas.window_seconds()
        start_s = datetime.fromtimestamp(start).strftime("%a %d %b %H:%M")
        end_s = datetime.fromtimestamp(end).strftime("%H:%M")
        self._range_label.setText(f"{start_s} – {end_s}")

    def wheelEvent(self, event):
        """Map wheel/trackpad gestures to row and time scrolling.

        Mac trackpads emit pixelDelta().x() for horizontal two-finger swipes
        without any modifier — we treat that as time scrolling. Shift+wheel
        is a mouse-friendly fallback for the same thing.
        """
        pixel = event.pixelDelta()
        angle = event.angleDelta()

        # Trackpad horizontal swipe → time scroll
        if abs(pixel.x()) > abs(pixel.y()) and pixel.x() != 0:
            delta = -pixel.x() // 30 or (-1 if pixel.x() > 0 else 1)
            self._h_scroll.setValue(self._h_scroll.value() + delta)
            event.accept()
            return

        # Shift+wheel → time scroll (traditional mouse)
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            y_val = pixel.y() if pixel.y() else angle.y()
            delta = -y_val // 40 or (-1 if y_val > 0 else 1 if y_val < 0 else 0)
            if delta:
                self._h_scroll.setValue(self._h_scroll.value() + delta)
            event.accept()
            return

        # Plain vertical wheel → row scroll
        pixel_y = pixel.y()
        angle_y = angle.y()
        if pixel_y:
            delta = -pixel_y // self._canvas.ROW_HEIGHT or (-1 if pixel_y > 0 else 1)
        elif angle_y:
            delta = -angle_y // 120 * 3 or (-1 if angle_y > 0 else 1)
        else:
            return
        self._v_scroll.setValue(self._v_scroll.value() + delta)
        event.accept()

    def keyPressEvent(self, event):
        """Arrow keys navigate time/rows; Home jumps to now."""
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            direction = -1 if key == Qt.Key.Key_Left else 1
            self._h_scroll.setValue(self._h_scroll.value() + direction * 2)
            event.accept()
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            direction = -1 if key == Qt.Key.Key_Up else 1
            self._v_scroll.setValue(self._v_scroll.value() + direction)
            event.accept()
            return
        if key == Qt.Key.Key_Home:
            self.jump_to_now()
            event.accept()
            return
        super().keyPressEvent(event)
