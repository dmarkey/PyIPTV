"""Persistent 'Now playing' program-info label for the active channel.

Renders the current EPG program (title, time range, short description) for
whatever channel is playing. Sits above the video in windowed mode and
reparents as a top-level frameless overlay alongside the control bar in
fullscreen. Hidden when no EPG is available for the playing channel.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ProgramInfoOverlay(QWidget):
    """Two-line: headline (title + time) on top, subtitle (description) below."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build()
        self.setVisible(False)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._title_label = QLabel("")
        title_font = self._title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(max(10, title_font.pointSize() + 1))
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: white;")

        self._time_label = QLabel("")
        time_font = self._time_label.font()
        time_font.setPointSize(max(8, time_font.pointSize() - 1))
        self._time_label.setFont(time_font)
        self._time_label.setStyleSheet("color: rgba(255, 255, 255, 180);")

        header.addWidget(self._title_label, 1)
        header.addWidget(self._time_label, 0, Qt.AlignmentFlag.AlignRight)

        self._desc_label = QLabel("")
        self._desc_label.setWordWrap(True)
        self._desc_label.setMaximumHeight(40)
        desc_font = self._desc_label.font()
        desc_font.setPointSize(max(8, desc_font.pointSize() - 1))
        self._desc_label.setFont(desc_font)
        self._desc_label.setStyleSheet("color: rgba(255, 255, 255, 170);")

        root.addLayout(header)
        root.addWidget(self._desc_label)

        self.setStyleSheet(
            "ProgramInfoOverlay {"
            " background: rgba(20, 20, 20, 200);"
            " border-radius: 8px;"
            " }"
        )

    def set_program(self, title: str, time_range: str, description: str = ""):
        """Render a program. Empty title hides the widget."""
        if not title:
            self.clear()
            return
        self._title_label.setText(title)
        self._time_label.setText(time_range)
        self._desc_label.setText(description or "")
        self._desc_label.setVisible(bool(description))
        self.setVisible(True)

    def clear(self):
        self._title_label.setText("")
        self._time_label.setText("")
        self._desc_label.setText("")
        self.setVisible(False)
