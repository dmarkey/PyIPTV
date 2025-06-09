import time
from enum import Enum
from typing import List, Optional

from PySide6.QtCore import QByteArray, QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget


class StatusLevel(Enum):
    """Status message levels."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    LOADING = "loading"


class StatusMessage:
    """Represents a status message."""

    def __init__(
        self,
        text: str,
        level: StatusLevel = StatusLevel.INFO,
        timeout: int = 0,
        actionable: bool = False,
        action_text: str = "",
    ):
        self.text = text
        self.level = level
        self.timeout = timeout  # 0 = no timeout
        self.actionable = actionable
        self.action_text = action_text
        self.timestamp = time.time()
        self.id = f"status_{int(self.timestamp * 1000)}"


class UnifiedStatusBar(QWidget):
    """Modern status bar with support for different message types and actions."""

    # Signals
    action_clicked = Signal(str)  # status_message_id
    status_dismissed = Signal(str)  # status_message_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_message: Optional[StatusMessage] = None
        self.message_queue: List[StatusMessage] = []
        self.auto_dismiss_timer = QTimer()
        self.auto_dismiss_timer.timeout.connect(self._auto_dismiss)
        self.init_ui()

    def init_ui(self):
        """Initialize the status bar UI."""
        self.setFixedHeight(24)  # Reduced from 32px to 24px
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)  # Reduced margins
        layout.setSpacing(6)  # Reduced spacing

        # Status icon/indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)  # Smaller indicator
        # Let the indicator inherit system colors
        pass
        layout.addWidget(self.status_indicator)

        # Status text
        self.status_label = QLabel("Ready")
        # Use smaller font but inherit colors from system theme
        font = self.status_label.font()
        font.setPointSize(max(9, font.pointSize() - 2))
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # Spacer
        layout.addStretch()

        # Action button (hidden by default)
        self.action_button = QPushButton()
        self.action_button.setVisible(False)
        # Use smaller font and inherit colors
        font = self.action_button.font()
        font.setPointSize(max(8, font.pointSize() - 2))
        self.action_button.setFont(font)
        self.action_button.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.action_button)

        # Dismiss button
        self.dismiss_button = QPushButton("×")
        self.dismiss_button.setVisible(False)
        self.dismiss_button.setFixedSize(16, 16)  # Smaller dismiss button
        # Inherit system colors and use smaller font
        font = self.dismiss_button.font()
        font.setPointSize(max(10, font.pointSize() - 1))
        font.setBold(True)
        self.dismiss_button.setFont(font)
        self.dismiss_button.clicked.connect(self._on_dismiss_clicked)
        layout.addWidget(self.dismiss_button)

        # Set default state
        self._apply_status_style(StatusLevel.INFO)

    def show_message(
        self,
        text: str,
        level: StatusLevel = StatusLevel.INFO,
        timeout: int = 0,
        actionable: bool = False,
        action_text: str = "",
    ) -> str:
        """Show a status message."""
        message = StatusMessage(text, level, timeout, actionable, action_text)

        # If there's a current message, queue this one
        if self.current_message and self.current_message.level in [
            StatusLevel.LOADING,
            StatusLevel.ERROR,
        ]:
            self.message_queue.append(message)
            return message.id

        self._display_message(message)
        return message.id

    def show_info(self, text: str, timeout: int = 5000) -> str:
        """Show an info message."""
        return self.show_message(text, StatusLevel.INFO, timeout)

    def show_success(self, text: str, timeout: int = 4000) -> str:
        """Show a success message."""
        return self.show_message(text, StatusLevel.SUCCESS, timeout)

    def show_warning(
        self,
        text: str,
        timeout: int = 0,
        actionable: bool = False,
        action_text: str = "",
    ) -> str:
        """Show a warning message."""
        return self.show_message(
            text, StatusLevel.WARNING, timeout, actionable, action_text
        )

    def show_error(
        self, text: str, actionable: bool = False, action_text: str = ""
    ) -> str:
        """Show an error message."""
        return self.show_message(text, StatusLevel.ERROR, 0, actionable, action_text)

    def show_loading(self, text: str) -> str:
        """Show a loading message."""
        return self.show_message(text, StatusLevel.LOADING)

    def update_message(self, message_id: str, text: str):
        """Update an existing message."""
        if self.current_message and self.current_message.id == message_id:
            self.current_message.text = text
            self.status_label.setText(text)

    def dismiss_message(self, message_id: str):
        """Dismiss a specific message."""
        if self.current_message and self.current_message.id == message_id:
            self._dismiss_current_message()

    def clear_all(self):
        """Clear all messages."""
        self.current_message = None
        self.message_queue.clear()
        self.auto_dismiss_timer.stop()
        self._show_default_message()

    def _display_message(self, message: StatusMessage):
        """Display a message."""
        self.current_message = message

        # Update UI
        self.status_label.setText(message.text)
        self._apply_status_style(message.level)

        # Handle action button
        if message.actionable and message.action_text:
            self.action_button.setText(message.action_text)
            self.action_button.setVisible(True)
        else:
            self.action_button.setVisible(False)

        # Handle dismiss button
        dismissible = message.level not in [StatusLevel.LOADING]
        self.dismiss_button.setVisible(dismissible)

        # Handle auto-dismiss
        if message.timeout > 0:
            self.auto_dismiss_timer.start(message.timeout)
        else:
            self.auto_dismiss_timer.stop()

        # Animate in
        self._animate_message_change()

    def _apply_status_style(self, level: StatusLevel):
        """Apply minimal status styling that respects system theme."""
        # Set indicator background based on status level using system colors
        if level == StatusLevel.SUCCESS:
            # Use system highlight color with green tint for success
            indicator_color = "palette(highlight)"
        elif level == StatusLevel.WARNING:
            # Use system mid color for warning
            indicator_color = "palette(mid)"
        elif level == StatusLevel.ERROR:
            # Use system bright-text color for errors
            indicator_color = "palette(bright-text)"
        elif level == StatusLevel.LOADING:
            # Use system highlight color for loading
            indicator_color = "palette(highlight)"
        else:
            # Default to system mid color
            indicator_color = "palette(mid)"

        # Apply minimal indicator styling using system colors
        self.status_indicator.setStyleSheet(
            f"""
            QLabel {{
                border-radius: 6px;
                background: {indicator_color};
            }}
        """
        )

        # Text inherits from system theme automatically
        # Background inherits from system theme automatically
        self.setStyleSheet(
            """
            UnifiedStatusBar {
                border-top: 1px solid palette(mid);
            }
        """
        )

        # Add loading animation for loading status
        if level == StatusLevel.LOADING:
            self._start_loading_animation()
        else:
            self._stop_loading_animation()

    def _start_loading_animation(self):
        """Start loading animation."""
        if not hasattr(self, "loading_animation"):
            self.loading_animation = QPropertyAnimation(
                self.status_indicator, QByteArray(b"styleSheet")
            )
            self.loading_animation.setDuration(1000)
            self.loading_animation.setLoopCount(-1)  # Infinite

        # Animate between system highlight and mid colors
        self.loading_animation.setKeyValueAt(
            0,
            """
            QLabel {
                border-radius: 6px;
                background: palette(highlight);
            }
        """,
        )
        self.loading_animation.setKeyValueAt(
            0.5,
            """
            QLabel {
                border-radius: 6px;
                background: palette(mid);
            }
        """,
        )
        self.loading_animation.setKeyValueAt(
            1,
            """
            QLabel {
                border-radius: 6px;
                background: palette(highlight);
            }
        """,
        )

        self.loading_animation.start()

    def _stop_loading_animation(self):
        """Stop loading animation."""
        if hasattr(self, "loading_animation"):
            self.loading_animation.stop()

    def _animate_message_change(self):
        """Animate message changes."""
        # Simple fade effect
        self.fade_animation = QPropertyAnimation(self, QByteArray(b"windowOpacity"))
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.7)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def _auto_dismiss(self):
        """Auto-dismiss current message."""
        self._dismiss_current_message()

    def _dismiss_current_message(self):
        """Dismiss the current message."""
        if self.current_message:
            message_id = self.current_message.id
            self.current_message = None
            self.auto_dismiss_timer.stop()

            # Show next message in queue or default
            if self.message_queue:
                next_message = self.message_queue.pop(0)
                self._display_message(next_message)
            else:
                self._show_default_message()

            self.status_dismissed.emit(message_id)

    def _show_default_message(self):
        """Show default ready message."""
        self.status_label.setText("Ready")
        self.action_button.setVisible(False)
        self.dismiss_button.setVisible(False)
        self._apply_status_style(StatusLevel.INFO)

    def _on_action_clicked(self):
        """Handle action button click."""
        if self.current_message:
            self.action_clicked.emit(self.current_message.id)

    def _on_dismiss_clicked(self):
        """Handle dismiss button click."""
        self._dismiss_current_message()


class StatusManager(QObject):
    """Central manager for coordinating status messages across the application."""

    def __init__(self):
        super().__init__()
        self.status_bar: Optional[UnifiedStatusBar] = None
        self.operation_statuses = {}  # Track operation-related statuses
        self.persistent_status_id: Optional[str] = None  # Track persistent status message

    def set_status_bar(self, status_bar: UnifiedStatusBar):
        """Set the status bar widget."""
        self.status_bar = status_bar
        if self.status_bar:
            self.status_bar.action_clicked.connect(self._on_status_action)

    def show_info(self, text: str, timeout: int = 5000) -> str:
        """Show info message."""
        if self.status_bar:
            return self.status_bar.show_info(text, timeout)
        return ""

    def show_success(self, text: str, timeout: int = 4000) -> str:
        """Show success message."""
        if self.status_bar:
            return self.status_bar.show_success(text, timeout)
        return ""

    def show_warning(
        self,
        text: str,
        timeout: int = 0,
        actionable: bool = False,
        action_text: str = "",
    ) -> str:
        """Show warning message."""
        if self.status_bar:
            return self.status_bar.show_warning(text, timeout, actionable, action_text)
        return ""

    def show_error(
        self, text: str, actionable: bool = False, action_text: str = ""
    ) -> str:
        """Show error message."""
        if self.status_bar:
            return self.status_bar.show_error(text, actionable, action_text)
        return ""

    def show_operation_status(self, operation_id: str, text: str) -> str:
        """Show status for a specific operation."""
        if self.status_bar:
            status_id = self.status_bar.show_loading(text)
            self.operation_statuses[operation_id] = status_id
            return status_id
        return ""

    def update_operation_status(self, operation_id: str, text: str):
        """Update status for an operation."""
        if operation_id in self.operation_statuses and self.status_bar:
            status_id = self.operation_statuses[operation_id]
            self.status_bar.update_message(status_id, text)

    def complete_operation_status(self, operation_id: str, success: bool, message: str):
        """Complete an operation status."""
        if operation_id in self.operation_statuses and self.status_bar:
            status_id = self.operation_statuses[operation_id]
            self.status_bar.dismiss_message(status_id)
            del self.operation_statuses[operation_id]

            # Show completion message
            if success:
                self.show_success(message)
            else:
                self.show_error(message)

    def show_persistent_info(self, text: str) -> str:
        """Show persistent info message that doesn't auto-dismiss."""
        if self.status_bar:
            # Clear any existing persistent status
            if self.persistent_status_id:
                self.status_bar.dismiss_message(self.persistent_status_id)

            # Show new persistent status (no timeout = persistent)
            self.persistent_status_id = self.status_bar.show_info(text, timeout=0)
            return self.persistent_status_id
        return ""

    def clear_persistent_info(self):
        """Clear persistent info message."""
        if self.persistent_status_id and self.status_bar:
            self.status_bar.dismiss_message(self.persistent_status_id)
            self.persistent_status_id = None

    def _on_status_action(self, status_id: str):
        """Handle status action clicks."""
        # Override in subclasses or connect to signals
        pass
