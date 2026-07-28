"""
PhoneTrace -- Details Panel Widget
=====================================

Right-side inspector panel with collapsible sections for
event metadata, location, and related events.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from gui.theme import (
    ACCENT, AI_ACCENT, ARTIFACT_COLORS, BG_CARD, BG_ELEVATED,
    BG_SECONDARY, BORDER, TEXT, TEXT_DIM, WARNING,
)


class _CollapsibleSection(QFrame):
    """A collapsible section with chevron toggle."""

    def __init__(self, title: str, accent: str = "", parent=None):
        super().__init__(parent)
        self._expanded = True
        accent = accent or ACCENT

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header_btn = QPushButton(f"  ▾  {title}")
        header_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {accent};
                border: none;
                border-bottom: 1px solid {BORDER};
                border-radius: 0px;
                text-align: left;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
            }}
        """)
        header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_btn.clicked.connect(self._toggle)
        self._header_btn = header_btn
        self._title = title
        outer.addWidget(header_btn)

        # Content container
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 10)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        chevron = "▾" if self._expanded else "▸"
        self._header_btn.setText(f"  {chevron}  {self._title}")

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout


class DetailsPanel(QFrame):
    """Right-side panel showing selected event details with collapsible sections."""

    bookmark_requested = pyqtSignal(object)  # Emits ForensicEvent to bookmark

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border-left: 1px solid {BORDER};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Title
        self._title = QLabel("  🔍  Inspector")
        self._title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TEXT}; "
            f"padding: 12px 14px 10px 14px; background: transparent; "
            f"border-bottom: 1px solid {BORDER};"
        )
        outer.addWidget(self._title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        outer.addWidget(scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        placeholder = QLabel("Select an event to inspect its details.")
        placeholder.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; padding: 20px; background: transparent;"
        )
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(placeholder)

    def show_event(self, event) -> None:
        """Populate the panel with a ForensicEvent's data."""
        self._clear()

        if event is None:
            self._show_placeholder()
            return

        # Artifact type badge & bookmark button
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        atype = event.artifact_type
        color = ARTIFACT_COLORS.get(atype, "#64748B")
        badge = QLabel(f"  {atype.upper()}  ")
        badge.setFixedHeight(24)
        badge.setStyleSheet(
            f"background-color: {color}30; color: {color}; "
            f"border-radius: 4px; font-size: 11px; font-weight: 600; "
            f"padding: 2px 8px; letter-spacing: 0.5px;"
        )
        header_row.addWidget(badge)
        header_row.addStretch()

        btn_bm = QPushButton("★ Bookmark")
        btn_bm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bm.setFixedHeight(24)
        btn_bm.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {WARNING};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
            }}
        """)
        btn_bm.clicked.connect(lambda: self.bookmark_requested.emit(event))
        header_row.addWidget(btn_bm)

        self._layout.addLayout(header_row)

        # Evidence section
        evidence_sec = _CollapsibleSection("Evidence")
        self._add_field(evidence_sec.content_layout, "Title", event.title)
        self._add_field(
            evidence_sec.content_layout, "Timestamp",
            event.timestamp.strftime("%Y-%m-%d  %H:%M:%S"),
        )
        self._add_field(evidence_sec.content_layout, "Source", event.source)
        self._add_field(evidence_sec.content_layout, "Description", event.description)
        self._layout.addWidget(evidence_sec)

        # Location section
        if event.location:
            loc_sec = _CollapsibleSection("Location", "#10B981")
            self._add_field(
                loc_sec.content_layout, "Coordinates",
                f"{event.location.latitude:.6f}, {event.location.longitude:.6f}",
            )
            if event.location.accuracy:
                self._add_field(
                    loc_sec.content_layout, "Accuracy",
                    f"± {event.location.accuracy} m",
                )
            self._layout.addWidget(loc_sec)

        # Metadata section
        if event.metadata:
            meta_sec = _CollapsibleSection("Metadata", "#F59E0B")
            for key, val in event.metadata.items():
                display = str(val)
                if len(display) > 120:
                    display = display[:120] + "…"
                self._add_field(
                    meta_sec.content_layout,
                    key.replace("_", " ").title(),
                    display,
                )
            self._layout.addWidget(meta_sec)

        # Related events
        if event.related:
            rel_sec = _CollapsibleSection(
                f"Related Events ({len(event.related)})", AI_ACCENT
            )
            for i, rel in enumerate(event.related[:10]):
                rel_color = ARTIFACT_COLORS.get(rel.artifact_type, "#64748B")
                lbl = QLabel(
                    f"<span style='color: {rel_color}; font-weight: 600;'>"
                    f"[{rel.artifact_type.upper()}]</span> "
                    f"<span style='color: {TEXT};'>{rel.title}</span>"
                    f"<br><span style='color: {TEXT_DIM}; font-size: 11px;'>"
                    f"  {rel.timestamp.strftime('%H:%M:%S')}</span>"
                )
                lbl.setStyleSheet(
                    f"font-size: 12px; padding: 4px 0; background: transparent;"
                )
                lbl.setWordWrap(True)
                rel_sec.content_layout.addWidget(lbl)
            self._layout.addWidget(rel_sec)

        self._layout.addStretch()

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_field(self, layout: QVBoxLayout, label: str, value: str) -> None:
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"font-size: 10px; color: {TEXT_DIM}; font-weight: 600; "
            f"letter-spacing: 0.5px; background: transparent; margin-top: 4px;"
        )
        layout.addWidget(lbl)

        val = QLabel(str(value))
        val.setStyleSheet(
            f"font-size: 12px; color: {TEXT}; background: transparent;"
        )
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val)
