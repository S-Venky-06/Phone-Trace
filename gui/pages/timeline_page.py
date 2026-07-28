"""
PhoneTrace -- Timeline Page
==============================

QTableView-based timeline viewer with filter bar,
colored artifact badges, and interactive search.
"""

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QTableView,
    QVBoxLayout, QWidget, QStyledItemDelegate, QStyle,
)

from gui.theme import TEXT_DIM, ARTIFACT_COLORS, BG_PRIMARY, BG_ELEVATED, TEXT, SELECTION
from gui.widgets.search_bar import SearchBar
from timeline import TimelineFilter


class BadgeDelegate(QStyledItemDelegate):
    """Paints a beautiful pill-shaped badge for the artifact type column."""

    def paint(self, painter, option, index):
        if index.column() == 1:  # Type column
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if not text:
                return

            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw background highlight if row selected
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QBrush(QColor(SELECTION)))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                painter.fillRect(option.rect, QBrush(QColor(BG_ELEVATED)))

            # Get artifact color
            color_hex = ARTIFACT_COLORS.get(text.lower(), "#64748B")
            color = QColor(color_hex)
            bg_color = QColor(color.red(), color.green(), color.blue(), 40)

            # Badge bounding box
            margin_x = 6
            margin_y = 5
            badge_rect = QRectF(
                option.rect.x() + margin_x,
                option.rect.y() + margin_y,
                option.rect.width() - 2 * margin_x,
                option.rect.height() - 2 * margin_y
            )

            # Draw rounded rect pill
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(color, 1))
            painter.drawRoundedRect(badge_rect, 4, 4)

            # Draw text inside pill
            painter.setPen(color)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text.upper())
            painter.restore()
        else:
            super().paint(painter, option, index)


class _TimelineModel(QAbstractTableModel):
    """Qt Model/View model backed by a list of ForensicEvents."""

    COLUMNS = ["Timestamp", "Type", "Title", "Source", "Description", "Location"]

    def __init__(self, events=None, parent=None):
        super().__init__(parent)
        self._events = events or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._events)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        event = self._events[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            elif col == 1:
                return event.artifact_type.upper()
            elif col == 2:
                return event.title
            elif col == 3:
                return event.source
            elif col == 4:
                desc = event.description
                return desc[:100] + "..." if len(desc) > 100 else desc
            elif col == 5:
                if event.location:
                    return f"{event.location.latitude:.4f}, {event.location.longitude:.4f}"
                return ""
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return QColor(TEXT_DIM)
            return QColor(TEXT)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def get_event(self, row: int):
        if 0 <= row < len(self._events):
            return self._events[row]
        return None

    def update_events(self, events):
        self.beginResetModel()
        self._events = events
        self.endResetModel()


class TimelinePage(QWidget):
    """Timeline viewer with table, filters, and search."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_events = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Timeline")
        header.setObjectName("heading")
        layout.addWidget(header)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self._type_filter = QComboBox()
        self._type_filter.addItems(
            ["All Types", "call", "sms", "browser", "gps", "app_usage", "file"]
        )
        self._type_filter.currentTextChanged.connect(self._apply_filters)
        
        type_label = QLabel("Artifact Type:")
        type_label.setStyleSheet(f"color: {TEXT_DIM}; font-weight: 500;")
        filter_bar.addWidget(type_label)
        filter_bar.addWidget(self._type_filter)

        self._search = SearchBar("Search timeline...")
        self._search.searched.connect(self._apply_filters)
        filter_bar.addWidget(self._search, 1)

        self._count_label = QLabel("0 events")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        filter_bar.addWidget(self._count_label)

        layout.addLayout(filter_bar)

        # Table view
        self._model = _TimelineModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(False)
        self._table.setItemDelegateForColumn(1, BadgeDelegate())

        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 160)
        self._table.setColumnWidth(3, 120)
        self._table.setColumnWidth(5, 140)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.clicked.connect(self._on_click)
        layout.addWidget(self._table)

    def load_from_backend(self, backend) -> None:
        """Load all timeline events from backend."""
        if not backend or not backend.is_loaded:
            return
        self._all_events = backend.events
        self._model.update_events(self._all_events)
        self._count_label.setText(f"{len(self._all_events):,} events")

    def _apply_filters(self, *args) -> None:
        events = self._all_events

        # Type filter
        atype = self._type_filter.currentText()
        if atype != "All Types":
            events = TimelineFilter.by_artifact(events, atype)

        # Keyword search
        query = self._search.text
        if query:
            events = TimelineFilter.search(events, query)

        self._model.update_events(events)
        self._count_label.setText(f"{len(events):,} events")

    def _on_click(self, index: QModelIndex) -> None:
        event = self._model.get_event(index.row())
        if event:
            self.event_selected.emit(event)

    def _on_double_click(self, index: QModelIndex) -> None:
        event = self._model.get_event(index.row())
        if event:
            self.event_selected.emit(event)
