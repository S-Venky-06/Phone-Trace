"""
PhoneTrace -- Stat Card Widget
================================

Professional metric card with icon badge, large value,
subtitle, trend indicator, and hover elevation.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout,
)

from gui.theme import (
    ACCENT, BG_CARD, BG_ELEVATED, BORDER, TEXT, TEXT_DIM,
)


class StatCard(QFrame):
    """Styled metric card with icon badge, value, title, and optional subtitle.

    Args:
        icon: Unicode icon character.
        title: Metric label (e.g. "Total Events").
        value: The metric value to display.
        subtitle: Optional secondary text (e.g. trend indicator).
        accent_color: Optional accent color for the icon badge.
    """

    def __init__(
        self,
        icon: str = "",
        title: str = "",
        value: str = "0",
        subtitle: str = "",
        accent_color: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._accent = accent_color or ACCENT
        self.setObjectName("statCard")
        self._apply_base_style()
        self.setMinimumWidth(200)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        # Top row: icon badge + title
        top = QHBoxLayout()
        top.setSpacing(8)

        if icon:
            badge = QLabel(icon)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background-color: {self._accent}20; "
                f"color: {self._accent}; "
                f"border-radius: 6px; "
                f"font-size: 14px; "
                f"font-weight: 600;"
            )
            top.addWidget(badge)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_DIM}; "
            f"font-weight: 600; letter-spacing: 0.5px; "
            f"background: transparent;"
        )
        top.addWidget(title_lbl)
        top.addStretch()
        layout.addLayout(top)

        # Value
        self._value_lbl = QLabel(str(value))
        self._value_lbl.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {TEXT}; "
            f"background: transparent; margin-top: 2px;"
        )
        layout.addWidget(self._value_lbl)

        # Subtitle / trend
        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_DIM}; background: transparent;"
        )
        self._sub_lbl.setVisible(bool(subtitle))
        layout.addWidget(self._sub_lbl)

        layout.addStretch()

    def _apply_base_style(self) -> None:
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
            QFrame#statCard:hover {{
                background-color: {BG_ELEVATED};
                border-color: {self._accent};
            }}
        """)

    def set_value(self, value: str) -> None:
        """Update the displayed value."""
        self._value_lbl.setText(str(value))

    def set_subtitle(self, text: str) -> None:
        """Update the subtitle text."""
        self._sub_lbl.setText(text)
        self._sub_lbl.setVisible(bool(text))
