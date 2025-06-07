from PySide6.QtCore import QRect, Qt, QTimer, Signal, QThread, QUrl
from PySide6.QtGui import QFontMetrics, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import os


class ImageCache:
    """Simple image cache for channel logos."""
    
    def __init__(self):
        self.cache = {}
        self.network_manager = QNetworkAccessManager()
        self.loading = set()  # Track URLs currently being loaded
        
    def get_image(self, url, callback=None):
        """Get image from cache or download it."""
        if not url:
            return None
            
        # Return cached image if available
        if url in self.cache:
            return self.cache[url]
            
        # Don't start multiple downloads for the same URL
        if url in self.loading:
            return None
            
        # Start download
        if callback:
            self.loading.add(url)
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(b"User-Agent", b"PyIPTV/1.0")
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self._on_image_downloaded(reply, url, callback))
            
        return None
        
    def _on_image_downloaded(self, reply, url, callback):
        """Handle downloaded image."""
        self.loading.discard(url)
        
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Scale to appropriate size
                scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.cache[url] = scaled_pixmap
                callback()
        else:
            # Cache a placeholder for failed downloads
            self.cache[url] = None
            
        reply.deleteLater()


class EnhancedChannelList(QWidget):
    """
    Enhanced channel list widget with logo support.
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
        self.item_height = 40  # Increased height for logos
        self.visible_start_index = 0
        self.visible_count = 0
        self.selected_index = -1
        self.search_term = ""

        # Performance settings
        self.render_buffer = 5  # Extra items to render above/below visible area
        self.search_delay_ms = 300  # Delay before applying search filter

        # Image cache
        self.image_cache = ImageCache()

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
        self.viewport = EnhancedChannelViewport(self)

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

    def get_selected_channel(self):
        """Get the currently selected channel."""
        if 0 <= self.selected_index < len(self._filtered_channels):
            return self._filtered_channels[self.selected_index]
        return None

    # Navigation methods for compatibility
    def select_next_channel(self):
        """Select next channel."""
        if len(self._filtered_channels) == 0:
            return None
        new_index = min(self.selected_index + 1, len(self._filtered_channels) - 1)
        self._set_selection(new_index)
        return self.get_selected_channel()

    def select_previous_channel(self):
        """Select previous channel."""
        if len(self._filtered_channels) == 0:
            return None
        new_index = max(self.selected_index - 1, 0)
        self._set_selection(new_index)
        return self.get_selected_channel()

    def page_down(self):
        """Move down one page."""
        if len(self._filtered_channels) == 0:
            return
        new_index = min(self.selected_index + self.visible_count, len(self._filtered_channels) - 1)
        self._set_selection(new_index)

    def page_up(self):
        """Move up one page."""
        if len(self._filtered_channels) == 0:
            return
        new_index = max(self.selected_index - self.visible_count, 0)
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


class EnhancedChannelViewport(QFrame):
    """Enhanced viewport widget for rendering channel items with logos."""

    def __init__(self, parent_list):
        super().__init__()
        self.parent_list = parent_list
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)

    def paintEvent(self, event):
        """Render visible items with logos."""
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

        for i in range(render_start, render_end):
            y_pos = (i - start_idx) * item_height

            # Skip items outside viewport
            if y_pos + item_height < 0 or y_pos > self.height():
                continue

            item_rect = QRect(0, y_pos, self.width(), item_height)

            # Draw selection/hover background
            if i == self.parent_list.selected_index:
                painter.fillRect(item_rect, selected_color)
                painter.setPen(selected_text_color)
            elif i == self.parent_list.hover_index:
                hover_color = selected_color.lighter(150)
                painter.fillRect(item_rect, hover_color)
                painter.setPen(text_color)
            else:
                painter.setPen(text_color)

            # Draw channel item with logo
            channel = channels[i]
            self._draw_channel_item(painter, item_rect, channel)

    def _draw_channel_item(self, painter, rect, channel):
        """Draw a single channel item with logo and text."""
        # Logo area (left side)
        logo_size = 32
        logo_margin = 4
        logo_rect = QRect(
            rect.x() + logo_margin,
            rect.y() + (rect.height() - logo_size) // 2,
            logo_size,
            logo_size
        )

        # Text area (right side)
        text_margin = 8
        text_rect = QRect(
            logo_rect.right() + text_margin,
            rect.y(),
            rect.width() - logo_rect.width() - logo_margin - text_margin,
            rect.height()
        )

        # Draw logo
        logo_url = channel.get("tvg-logo", "")
        if logo_url:
            pixmap = self.parent_list.image_cache.get_image(
                logo_url, 
                callback=lambda: self.update()  # Refresh when image loads
            )
            if pixmap:
                painter.drawPixmap(logo_rect, pixmap)
            else:
                # Draw placeholder
                painter.drawRect(logo_rect)
                painter.drawText(logo_rect, Qt.AlignCenter, "📺")
        else:
            # Draw default icon
            painter.drawRect(logo_rect)
            painter.drawText(logo_rect, Qt.AlignCenter, "📺")

        # Draw channel name and category
        channel_name = channel.get("name", "Unknown Channel")
        
        # Main text (channel name)
        name_rect = QRect(text_rect.x(), text_rect.y() + 2, text_rect.width(), text_rect.height() // 2)
        font_metrics = QFontMetrics(self.font())
        elided_name = font_metrics.elidedText(channel_name, Qt.ElideRight, name_rect.width())
        painter.drawText(name_rect, Qt.AlignVCenter, elided_name)

        # Secondary text (category)
        category = channel.get("group-title", "")
        if category and category != "Uncategorized":
            # Use smaller font for category
            font = painter.font()
            font.setPointSize(max(6, font.pointSize() - 2))
            painter.setFont(font)
            
            category_rect = QRect(text_rect.x(), text_rect.y() + text_rect.height() // 2, text_rect.width(), text_rect.height() // 2 - 2)
            elided_category = font_metrics.elidedText(f"[{category}]", Qt.ElideRight, category_rect.width())
            
            # Use lighter color for category
            color = painter.pen().color()
            color.setAlpha(150)
            painter.setPen(color)
            painter.drawText(category_rect, Qt.AlignVCenter, elided_category)

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
        """Handle mouse wheel scrolling."""
        # Scroll by 3 items per wheel step
        delta = -event.angleDelta().y() // 120 * 3

        scrollbar = self.parent_list.v_scrollbar
        new_value = scrollbar.value() + delta
        new_value = max(0, min(scrollbar.maximum(), new_value))
        scrollbar.setValue(new_value)
