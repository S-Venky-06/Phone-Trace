"""
PhoneTrace -- Navigation Sidebar
==================================

Professional collapsible sidebar with icon+label navigation,
smooth width animation, section dividers, and persistent state.
"""

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt, pyqtSignal, QSize,
)
from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout,
    QSizePolicy,
)

from gui.theme import (
    ACCENT, AI_ACCENT, BG_ELEVATED, BG_SIDEBAR, BORDER, TEXT, TEXT_DIM,
)

# Width constants
EXPANDED_WIDTH = 220
COLLAPSED_WIDTH = 56

# Navigation items: (key, icon, label, group)
NAV_ITEMS = [
    ("dashboard",    "⊞",  "Dashboard",    "investigation"),
    ("cases",        "📁", "Cases",         "investigation"),
    ("timeline",     "⏱",  "Timeline",      "investigation"),
    ("correlations", "⚡", "Correlations",  "investigation"),
    ("evidence",     "🔍", "Evidence",      "investigation"),
    ("statistics",   "📊", "Statistics",    "analysis"),
    ("graph",        "◉",  "Graph View",    "analysis"),
    ("ai_assistant", "🤖", "AI Assistant",  "analysis"),
    ("reports",      "📋", "Reports",       "system"),
    ("settings",     "⚙",  "Settings",      "system"),
]


class _NavButton(QPushButton):
    """A single sidebar navigation button with icon and label."""

    def __init__(self, key: str, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._icon = icon
        self._label = label
        self._is_ai = key == "ai_assistant"
        self.setCheckable(True)
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._collapsed = False
        self._update_text()
        self._apply_style(False)

    def _update_text(self) -> None:
        if self._collapsed:
            self.setText(f" {self._icon}")
        else:
            self.setText(f"  {self._icon}   {self._label}")

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._update_text()

    def _apply_style(self, active: bool) -> None:
        accent = AI_ACCENT if self._is_ai else ACCENT
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_ELEVATED};
                    color: {accent};
                    border: none;
                    border-left: 3px solid {accent};
                    border-radius: 0px;
                    border-top-right-radius: 8px;
                    border-bottom-right-radius: 8px;
                    text-align: left;
                    padding-left: 12px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_DIM};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    border-top-right-radius: 8px;
                    border-bottom-right-radius: 8px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {BG_ELEVATED};
                    color: {TEXT};
                    border-left: 3px solid {BORDER};
                }}
            """)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self._apply_style(active)


class _SectionDivider(QFrame):
    """Thin horizontal divider with optional section label."""

    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self._label_text = label
        self._label_widget = None

        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 4)

        if label:
            self._label_widget = QLabel(label.upper())
            self._label_widget.setStyleSheet(
                f"font-size: 10px; font-weight: 600; color: {TEXT_DIM}; "
                f"letter-spacing: 1px; background: transparent;"
            )
            layout.addWidget(self._label_widget)
        layout.addStretch()

    def set_collapsed(self, collapsed: bool) -> None:
        if self._label_widget:
            self._label_widget.setVisible(not collapsed)


class Sidebar(QFrame):
    """Professional collapsible navigation sidebar.

    Emits ``page_changed(key)`` when the user clicks a navigation item.
    """

    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self.setFixedWidth(EXPANDED_WIDTH)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SIDEBAR};
                border-right: 1px solid {BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(2)

        # Top row: brand + collapse toggle
        top_row = QHBoxLayout()
        top_row.setContentsMargins(6, 0, 2, 0)

        self._brand = QLabel("PhoneTrace")
        self._brand.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {ACCENT}; "
            f"background: transparent; padding: 2px 4px;"
        )
        top_row.addWidget(self._brand)
        top_row.addStretch()

        self._toggle_btn = QPushButton("☰")
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_DIM};
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                color: {TEXT};
            }}
        """)
        self._toggle_btn.clicked.connect(self.toggle_collapse)
        top_row.addWidget(self._toggle_btn)
        layout.addLayout(top_row)

        layout.addSpacing(12)

        # Navigation buttons with section dividers
        self._buttons: dict[str, _NavButton] = {}
        self._dividers: list[_SectionDivider] = []
        last_group = None

        for key, icon, label, group in NAV_ITEMS:
            if group != last_group and last_group is not None:
                divider_label = {
                    "analysis": "Analysis",
                    "system": "System",
                }.get(group, "")
                divider = _SectionDivider(divider_label)
                layout.addWidget(divider)
                self._dividers.append(divider)
                last_group = group
            elif last_group is None:
                last_group = group

            btn = _NavButton(key, icon, label)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addStretch()

        # Version label
        self._ver = QLabel("v3.0  Phase 6")
        self._ver.setStyleSheet(
            f"font-size: 10px; color: {TEXT_DIM}; "
            f"padding: 4px; background: transparent;"
        )
        self._ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ver)

        # Default selection
        self.set_active("dashboard")

    def _on_click(self, key: str) -> None:
        self.set_active(key)
        self.page_changed.emit(key)

    def set_active(self, key: str) -> None:
        """Highlight the given nav item and deactivate others."""
        for k, btn in self._buttons.items():
            btn.set_active(k == key)

    def toggle_collapse(self) -> None:
        """Animate between expanded and collapsed states."""
        self._collapsed = not self._collapsed
        target = COLLAPSED_WIDTH if self._collapsed else EXPANDED_WIDTH

        anim = QPropertyAnimation(self, b"minimumWidth")
        anim.setDuration(200)
        anim.setStartValue(self.width())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim_min = anim  # prevent GC

        anim2 = QPropertyAnimation(self, b"maximumWidth")
        anim2.setDuration(200)
        anim2.setStartValue(self.width())
        anim2.setEndValue(target)
        anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim_max = anim2

        anim.start()
        anim2.start()

        # Update button text
        for btn in self._buttons.values():
            btn.set_collapsed(self._collapsed)
        for div in self._dividers:
            div.set_collapsed(self._collapsed)

        self._brand.setText("PT" if self._collapsed else "PhoneTrace")
        self._ver.setVisible(not self._collapsed)

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed
