from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollBar,
    QFrame,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPainter, QFontMetrics, QPalette, QColor, QPen, QFont

from pyiptv.logo_cache import shared as shared_logo_cache


class VirtualizedChannelList(QWidget):
    """
    A virtualized list widget that can efficiently display millions of channels
    by only rendering visible items.
    """

    channel_selected = Signal(dict)  # Emits channel info dict
    channel_activated = Signal(dict)  # Emits channel info dict (double-click)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data
        self._all_channels = []
        self._filtered_channels = []
        self._filtered_indices = []  # Maps filtered index to original index

        # Display settings
        self.item_height = 56
        self.logo_size = 40
        self.visible_start_index = 0
        self.visible_count = 0
        self.selected_index = -1
        self.search_term = ""

        # Performance settings
        self.render_buffer = 5  # Extra items to render above/below visible area
        self.search_delay_ms = 300  # Delay before applying search filter

        # Shared logo cache (async). Repaint viewport when a requested logo lands.
        self._logo_cache = shared_logo_cache()
        self._logo_cache.logo_ready.connect(self._on_logo_ready)

        # Optional EPG provider: callable (channel_dict) -> str | None, returning
        # the now/next line to render as a second-line subtitle. When None, the
        # row shows only the channel name (existing behaviour).
        self._epg_provider = None

        # UI setup
        self.setup_ui()
        self.setup_timers()

        # Mouse tracking
        self.setMouseTracking(True)
        self.hover_index = -1

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search channels by name, category, or ID... (Ctrl+F to focus)"
        )
        self.search_input.textChanged.connect(self._on_search_changed)

        self.clear_search_btn = QPushButton("×")
        self.clear_search_btn.setMaximumWidth(30)
        self.clear_search_btn.clicked.connect(self._clear_search)
        self.clear_search_btn.setToolTip("Clear search")

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.clear_search_btn)
        layout.addLayout(search_layout)

        # Info label
        self.info_label = QLabel("No channels loaded")
        self.info_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.info_label)

        # Main display area
        display_layout = QHBoxLayout()
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(0)

        # Viewport for rendering items
        self.viewport = ChannelViewport(self)

        # Vertical scrollbar
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.valueChanged.connect(self._on_scroll)

        display_layout.addWidget(self.viewport, 1)
        display_layout.addWidget(self.v_scrollbar)
        layout.addLayout(display_layout, 1)

        # Set focus policy
        self.setFocusPolicy(Qt.StrongFocus)

    def setup_timers(self):
        """Setup timers for performance optimization."""
        # Search delay timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_search_filter)

    def set_channels(self, channels):
        """Set the channel data."""
        self._all_channels = channels
        self._apply_search_filter()
        self._update_info_label()

    def _update_info_label(self):
        """Update the info label with current stats."""
        total = len(self._all_channels)
        filtered = len(self._filtered_channels)

        if total == 0:
            self.info_label.setText("No channels loaded")
        elif self.search_term:
            self.info_label.setText(
                f"Showing {filtered:,} of {total:,} channels (filtered)"
            )
        else:
            self.info_label.setText(f"{total:,} channels loaded")

    def _on_search_changed(self, text):
        """Handle search text changes with delay."""
        self.search_term = text.lower().strip()
        self.search_timer.stop()
        self.search_timer.start(self.search_delay_ms)

    def _clear_search(self):
        """Clear the search filter."""
        self.search_input.clear()

    def _apply_search_filter(self):
        """Apply the current search filter."""
        if not self.search_term:
            self._filtered_channels = self._all_channels
            self._filtered_indices = list(range(len(self._all_channels)))
        else:
            self._filtered_channels = []
            self._filtered_indices = []

            for i, channel in enumerate(self._all_channels):
                # Search in multiple fields for better matching
                searchable_text = []
                searchable_text.append(channel.get("name", ""))
                searchable_text.append(channel.get("tvg-name", ""))
                searchable_text.append(channel.get("group-title", ""))
                searchable_text.append(channel.get("tvg-id", ""))

                # Combine all searchable text
                combined_text = " ".join(searchable_text).lower()

                if self.search_term in combined_text:
                    self._filtered_channels.append(channel)
                    self._filtered_indices.append(i)

        # Reset selection and scroll position
        self.selected_index = -1
        self.visible_start_index = 0

        # Update scrollbar
        self._update_scrollbar()
        self._update_visible_range()
        self._update_info_label()
        self.viewport.update()

    def _update_scrollbar(self):
        """Update scrollbar range and visibility."""
        total_items = len(self._filtered_channels)

        if total_items == 0:
            self.v_scrollbar.setVisible(False)
            return

        viewport_height = self.viewport.height()
        self.visible_count = max(1, viewport_height // self.item_height)

        if total_items <= self.visible_count:
            self.v_scrollbar.setVisible(False)
        else:
            self.v_scrollbar.setVisible(True)
            self.v_scrollbar.setMaximum(total_items - self.visible_count)
            self.v_scrollbar.setPageStep(self.visible_count)

    def _update_visible_range(self):
        """Update which items should be visible."""
        viewport_height = self.viewport.height()
        self.visible_count = max(1, viewport_height // self.item_height)

        # Ensure visible_start_index is within bounds
        max_start = max(0, len(self._filtered_channels) - self.visible_count)
        self.visible_start_index = min(self.visible_start_index, max_start)

    def _on_scroll(self, value):
        """Handle scrollbar changes."""
        self.visible_start_index = value
        self.viewport.update()

    def resizeEvent(self, event):
        """Handle widget resize."""
        super().resizeEvent(event)
        self._update_scrollbar()
        self._update_visible_range()

    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        if len(self._filtered_channels) == 0:
            return

        if event.key() == Qt.Key_Down:
            self._move_selection(1)
        elif event.key() == Qt.Key_Up:
            self._move_selection(-1)
        elif event.key() == Qt.Key_PageDown:
            self._move_selection(self.visible_count)
        elif event.key() == Qt.Key_PageUp:
            self._move_selection(-self.visible_count)
        elif event.key() == Qt.Key_Home:
            self._set_selection(0)
        elif event.key() == Qt.Key_End:
            self._set_selection(len(self._filtered_channels) - 1)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.selected_index >= 0:
                channel = self._filtered_channels[self.selected_index]
                self.channel_activated.emit(channel)
        else:
            super().keyPressEvent(event)

    def _move_selection(self, delta):
        """Move selection by delta."""
        if len(self._filtered_channels) == 0:
            return

        new_index = max(
            0, min(len(self._filtered_channels) - 1, self.selected_index + delta)
        )
        self._set_selection(new_index)

    def _set_selection(self, index):
        """Set selection to specific index."""
        if index < 0 or index >= len(self._filtered_channels):
            return

        self.selected_index = index

        # Ensure selected item is visible
        if index < self.visible_start_index:
            self.visible_start_index = index
            self.v_scrollbar.setValue(self.visible_start_index)
        elif index >= self.visible_start_index + self.visible_count:
            self.visible_start_index = index - self.visible_count + 1
            self.v_scrollbar.setValue(self.visible_start_index)

        # Emit selection signal
        if 0 <= index < len(self._filtered_channels):
            channel = self._filtered_channels[index]
            self.channel_selected.emit(channel)

        self.viewport.update()

    def get_selected_channel(self):
        """Get the currently selected channel."""
        if 0 <= self.selected_index < len(self._filtered_channels):
            return self._filtered_channels[self.selected_index]
        return None

    def _on_logo_ready(self, url):
        """Repaint the viewport when an async logo fetch lands."""
        # Cheap: viewport paint only touches visible rows, so an unconditional
        # update() is fine even if the URL isn't currently on screen.
        self.viewport.update()

    def set_epg_provider(self, provider):
        """Wire an EPG lookup. `provider(channel_dict) -> str | None`.

        Passing None removes any previously-set provider. Triggers a repaint.
        """
        self._epg_provider = provider
        self.viewport.update()


class ChannelViewport(QFrame):
    """Viewport widget for rendering visible channel items."""

    def __init__(self, parent_list):
        super().__init__()
        self.parent_list = parent_list
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)

    def paintEvent(self, event):
        """Render visible items."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get colors from palette
        palette = self.palette()
        bg_color = palette.color(QPalette.Base)
        text_color = palette.color(QPalette.Text)
        selected_color = palette.color(QPalette.Highlight)
        selected_text_color = palette.color(QPalette.HighlightedText)

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        # Get visible range
        channels = self.parent_list._filtered_channels
        start_idx = self.parent_list.visible_start_index
        visible_count = self.parent_list.visible_count
        item_height = self.parent_list.item_height

        if not channels:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No channels to display")
            return

        # Render visible items with buffer
        render_start = max(0, start_idx - self.parent_list.render_buffer)
        render_end = min(
            len(channels), start_idx + visible_count + self.parent_list.render_buffer
        )

        font_metrics = QFontMetrics(self.font())

        logo_size = self.parent_list.logo_size
        logo_pad = (item_height - logo_size) // 2
        logo_cache = self.parent_list._logo_cache
        placeholder_color = QColor(text_color)
        placeholder_color.setAlpha(60)

        for i in range(render_start, render_end):
            y_pos = (i - start_idx) * item_height

            # Skip items outside viewport
            if y_pos + item_height < 0 or y_pos > self.height():
                continue

            item_rect = QRect(0, y_pos, self.width(), item_height)

            # Draw selection/hover background
            if i == self.parent_list.selected_index:
                painter.fillRect(item_rect, selected_color)
                row_text_color = selected_text_color
            elif i == self.parent_list.hover_index:
                hover_color = selected_color.lighter(150)
                painter.fillRect(item_rect, hover_color)
                row_text_color = text_color
            else:
                row_text_color = text_color

            channel = channels[i]

            # Logo cell on the left.
            logo_rect = QRect(logo_pad, y_pos + logo_pad, logo_size, logo_size)
            logo_url = channel.get("tvg-logo") or ""
            pix = logo_cache.request(logo_url) if logo_url else None
            if pix is not None and not pix.isNull():
                scaled = pix.scaled(
                    logo_size,
                    logo_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # Center within the logo cell (scaled may be narrower).
                draw_x = logo_rect.x() + (logo_size - scaled.width()) // 2
                draw_y = logo_rect.y() + (logo_size - scaled.height()) // 2
                painter.drawPixmap(draw_x, draw_y, scaled)
            else:
                # Subtle placeholder box so rows line up before the logo loads.
                painter.save()
                painter.setPen(QPen(placeholder_color, 1))
                painter.drawRoundedRect(logo_rect, 4, 4)
                painter.restore()

            # Text cell to the right of the logo.
            channel_name = channel.get("name", "Unknown Channel")
            display_text = channel_name
            if self.parent_list.search_term:
                category = channel.get("group-title", "")
                if category and category != "Uncategorized":
                    display_text = f"{channel_name} [{category}]"

            text_left = logo_rect.right() + 8
            text_width = self.width() - text_left - 8

            # Optional EPG now/next line as a second-row subtitle.
            epg_text = ""
            provider = self.parent_list._epg_provider
            if provider is not None:
                try:
                    epg_text = provider(channel) or ""
                except Exception:
                    epg_text = ""

            # Catchup badge on the right — small ↻ pill on channels that
            # support Xtream timeshift. Reserves space so text eliding
            # accounts for it.
            has_catchup = bool(int(channel.get("xtream_tv_archive", 0) or 0))
            badge_width = 0
            if has_catchup:
                badge_text = "↻"
                badge_font = QFont(painter.font())
                badge_font.setBold(True)
                badge_metrics = QFontMetrics(badge_font)
                badge_w = badge_metrics.horizontalAdvance(badge_text) + 10
                badge_h = 18
                badge_rect = QRect(
                    self.width() - badge_w - 10,
                    y_pos + (item_height - badge_h) // 2,
                    badge_w,
                    badge_h,
                )
                painter.save()
                badge_bg = QColor(90, 160, 220, 120)
                painter.setBrush(badge_bg)
                painter.setPen(QPen(QColor(120, 180, 230, 180), 1))
                painter.drawRoundedRect(badge_rect, 4, 4)
                painter.setFont(badge_font)
                painter.setPen(row_text_color)
                painter.drawText(
                    badge_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    badge_text,
                )
                painter.restore()
                badge_width = badge_w + 14  # reserve space for text cell
            text_width -= badge_width

            if epg_text:
                name_rect = QRect(
                    text_left, y_pos + 4, text_width, item_height // 2
                )
                epg_rect = QRect(
                    text_left,
                    y_pos + item_height // 2,
                    text_width,
                    item_height // 2 - 4,
                )
                painter.setPen(row_text_color)
                painter.drawText(
                    name_rect,
                    Qt.AlignVCenter,
                    font_metrics.elidedText(
                        display_text, Qt.ElideRight, name_rect.width()
                    ),
                )
                # Secondary colour for the now/next line.
                epg_color = QColor(row_text_color)
                epg_color.setAlpha(150)
                painter.setPen(epg_color)
                small_font = painter.font()
                original_size = small_font.pointSize()
                if original_size > 0:
                    small_font.setPointSize(max(7, original_size - 2))
                painter.setFont(small_font)
                small_metrics = QFontMetrics(small_font)
                painter.drawText(
                    epg_rect,
                    Qt.AlignVCenter,
                    small_metrics.elidedText(
                        epg_text, Qt.ElideRight, epg_rect.width()
                    ),
                )
                # Restore font for subsequent rows.
                if original_size > 0:
                    small_font.setPointSize(original_size)
                    painter.setFont(small_font)
            else:
                text_rect = QRect(text_left, y_pos, text_width, item_height)
                elided_text = font_metrics.elidedText(
                    display_text, Qt.ElideRight, text_rect.width()
                )
                painter.setPen(row_text_color)
                painter.drawText(text_rect, Qt.AlignVCenter, elided_text)

    def mousePressEvent(self, event):
        """Handle mouse clicks."""
        if event.button() == Qt.LeftButton:
            self._handle_click(event.pos())

    def mouseDoubleClickEvent(self, event):
        """Handle double clicks."""
        if event.button() == Qt.LeftButton:
            index = self._get_index_at_position(event.pos())
            if 0 <= index < len(self.parent_list._filtered_channels):
                channel = self.parent_list._filtered_channels[index]
                self.parent_list.channel_activated.emit(channel)

    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects."""
        index = self._get_index_at_position(event.pos())
        if index != self.parent_list.hover_index:
            self.parent_list.hover_index = index
            self.update()

    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.parent_list.hover_index = -1
        self.update()

    def _handle_click(self, pos):
        """Handle click at position."""
        index = self._get_index_at_position(pos)
        if 0 <= index < len(self.parent_list._filtered_channels):
            self.parent_list._set_selection(index)

    def _get_index_at_position(self, pos):
        """Get the channel index at the given position."""
        y = pos.y()
        relative_index = y // self.parent_list.item_height
        return self.parent_list.visible_start_index + relative_index

    def wheelEvent(self, event):
        """Handle mouse wheel and trackpad scrolling.

        Mac trackpads send `pixelDelta` (and usually zero `angleDelta` for
        small gestures). The previous implementation only read `angleDelta`
        and truncated with `// 120`, so trackpad scrolls rounded to 0 items
        and the list felt frozen.
        """
        pixel_y = event.pixelDelta().y()
        angle_y = event.angleDelta().y()

        item_h = self.parent_list.item_height
        if pixel_y:
            # Trackpad. Convert pixels to items, but never round a non-zero
            # gesture down to zero.
            delta = -pixel_y / item_h
            delta = int(delta) if abs(delta) >= 1 else (-1 if pixel_y > 0 else 1)
        elif angle_y:
            # Traditional wheel: 120 units per notch, 3 items per notch.
            delta = -angle_y // 120 * 3 or (-1 if angle_y > 0 else 1)
        else:
            return

        scrollbar = self.parent_list.v_scrollbar
        new_value = scrollbar.value() + delta
        new_value = max(0, min(scrollbar.maximum(), new_value))
        scrollbar.setValue(new_value)
        event.accept()
