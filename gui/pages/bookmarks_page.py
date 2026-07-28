"""
PhoneTrace -- Bookmarks & Tagged Events Page
==============================================

Displays bookmarked evidence items, assigned tags, and investigator notes.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from gui.services.bookmark_manager import BookmarkManager
from gui.theme import (
    ACCENT, BG_ELEVATED, BG_PRIMARY, BG_SECONDARY,
    BORDER, DANGER, SELECTION, SUCCESS, TEXT, TEXT_DIM, WARNING,
)

_TAG_COLORS = {
    "Suspicious": DANGER,
    "Alibi Contradiction": WARNING,
    "Key Evidence": ACCENT,
    "Verified": SUCCESS,
}


class BookmarksPage(QWidget):
    """Viewer page for investigator bookmarked items and tags."""

    event_selected = pyqtSignal(object)

    def __init__(self, bookmark_manager: BookmarkManager, parent=None):
        super().__init__(parent)
        self._bm = bookmark_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Bookmarked Evidence & Tags")
        header.setObjectName("heading")
        layout.addWidget(header)

        sub = QLabel("Investigator flagged events, custom forensic tags, and investigation notes.")
        sub.setObjectName("subheading")
        layout.addWidget(sub)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._count_lbl = QLabel("0 Bookmarks")
        self._count_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        toolbar.addWidget(self._count_lbl)

        toolbar.addStretch()

        btn_remove = QPushButton("🗑 Remove Bookmark")
        btn_remove.setObjectName("dangerBtn")
        btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_remove.clicked.connect(self._on_remove)
        toolbar.addWidget(btn_remove)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Event ID", "Title", "Artifact", "Timestamp", "Forensic Tag"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_SECONDARY};
                alternate-background-color: {BG_PRIMARY};
                gridline-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 10px;
                selection-background-color: {SELECTION};
                selection-color: {TEXT};
                padding: 2px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border: none;
            }}
            QTableWidget::item:hover {{
                background-color: {BG_ELEVATED};
            }}
        """)
        layout.addWidget(self._table)

        self.refresh()

    def refresh(self) -> None:
        bookmarks = self._bm.bookmarks
        self._table.setRowCount(len(bookmarks))
        self._count_lbl.setText(f"{len(bookmarks)} Bookmarked Event(s)")

        for row, item in enumerate(bookmarks):
            self._table.setItem(row, 0, QTableWidgetItem(item.event_id))
            self._table.setItem(row, 1, QTableWidgetItem(item.title))
            self._table.setItem(row, 2, QTableWidgetItem(item.artifact_type.upper()))
            self._table.setItem(row, 3, QTableWidgetItem(item.timestamp_str))

            tag_item = QTableWidgetItem(item.tag)
            tag_color = _TAG_COLORS.get(item.tag, ACCENT)
            tag_item.setForeground(Qt.GlobalColor.white)
            self._table.setItem(row, 4, tag_item)

    def _selected_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 0).text()

    def _on_remove(self) -> None:
        eid = self._selected_id()
        if not eid:
            return
        self._bm.remove_bookmark(eid)
        self.refresh()
