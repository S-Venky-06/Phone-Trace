"""
PhoneTrace -- Evidence Explorer Page
=======================================

Tree-style explorer for browsing parsed evidence by type.
Enhanced with custom artifact category badges and clean layouts.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from gui.theme import ARTIFACT_COLORS, TEXT_DIM, TEXT, BORDER


class EvidencePage(QWidget):
    """Evidence explorer with tree view grouped by artifact type."""

    event_selected = pyqtSignal(object)  # emits ForensicEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Evidence Explorer")
        header.setObjectName("heading")
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Evidence Type / Title", "Timestamp"])
        self._tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._tree.header().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: transparent;
                border-bottom: 1px solid {BORDER};
            }}
        """)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

        self._event_map: dict[int, object] = {}

    def load_from_backend(self, backend) -> None:
        """Populate the tree from the backend service."""
        self._tree.clear()
        self._event_map.clear()

        if not backend or not backend.is_loaded:
            return

        categories = {
            "Calls": ("call", "📞"),
            "SMS": ("sms", "💬"),
            "Browser": ("browser", "🌐"),
            "GPS": ("gps", "📍"),
            "App Usage": ("app_usage", "▶"),
            "Files": ("file", "📄"),
        }

        for label, (atype, icon) in categories.items():
            events = [e for e in backend.events if e.artifact_type == atype]
            color = ARTIFACT_COLORS.get(atype, "#64748B")

            # Style the category parent node
            parent = QTreeWidgetItem(
                self._tree, [f"{icon}  {label} ({len(events)})", ""]
            )
            parent.setForeground(0, Qt.GlobalColor.white)
            parent.setExpanded(False)

            for event in events[:200]:  # Limit for performance
                ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                child = QTreeWidgetItem(parent, [event.title, ts])
                child.setForeground(0, Qt.GlobalColor.white)
                child.setForeground(1, Qt.GlobalColor.gray)
                
                uid = id(event)
                child.setData(0, Qt.ItemDataRole.UserRole, uid)
                self._event_map[uid] = event

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        uid = item.data(0, Qt.ItemDataRole.UserRole)
        if uid and uid in self._event_map:
            self.event_selected.emit(self._event_map[uid])
