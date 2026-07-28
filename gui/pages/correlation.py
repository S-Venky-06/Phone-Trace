"""
PhoneTrace -- Correlation Page
=================================

Displays correlation groups detected by the EvidenceCorrelator.
Enhanced with custom confidence badges and rule formatting.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QStyledItemDelegate, QStyle,
)

from gui.theme import (
    TEXT_DIM, ARTIFACT_COLORS, SUCCESS, WARNING, DANGER,
    BG_ELEVATED, TEXT, SELECTION,
)


class ConfidenceDelegate(QStyledItemDelegate):
    """Paints a custom confidence level badge."""

    def paint(self, painter, option, index):
        if index.column() == 4:  # Confidence column
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if not text:
                return

            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw background highlights
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QBrush(QColor(SELECTION)))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                painter.fillRect(option.rect, QBrush(QColor(BG_ELEVATED)))

            # Parse percentage
            try:
                pct = int(text.replace("%", "").strip())
            except ValueError:
                pct = 0

            # Select color based on confidence level
            if pct >= 80:
                color_hex = SUCCESS
            elif pct >= 50:
                color_hex = WARNING
            else:
                color_hex = DANGER

            color = QColor(color_hex)
            bg_color = QColor(color.red(), color.green(), color.blue(), 40)

            # Badge bounding box
            margin_x = 10
            margin_y = 5
            badge_rect = QRectF(
                option.rect.x() + margin_x,
                option.rect.y() + margin_y,
                option.rect.width() - 2 * margin_x,
                option.rect.height() - 2 * margin_y
            )

            # Draw badge background
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(color, 1))
            painter.drawRoundedRect(badge_rect, 4, 4)

            # Draw text
            painter.setPen(color)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
        else:
            super().paint(painter, option, index)


class CorrelationPage(QWidget):
    """Lists correlation groups with rule name, anchor, count, confidence."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Evidence Correlations")
        header.setObjectName("heading")
        layout.addWidget(header)

        self._count_label = QLabel("0 correlation groups")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        layout.addWidget(self._count_label)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Rule", "Anchor Event", "Anchor Time", "Related Count", "Confidence"
        ])
        
        # Apply confidence delegate
        self._table.setItemDelegateForColumn(4, ConfidenceDelegate())

        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 160)
        self._table.setColumnWidth(2, 140)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 110)
        
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellClicked.connect(self._on_click)
        layout.addWidget(self._table)

    def load_from_backend(self, backend) -> None:
        """Populate the table from backend correlation groups."""
        if not backend or not backend.is_loaded:
            return

        self._groups = backend.correlations
        self._table.setRowCount(len(self._groups))
        self._count_label.setText(f"{len(self._groups):,} correlation groups")

        for row, group in enumerate(self._groups):
            self._table.setItem(row, 0, QTableWidgetItem(
                group.rule_name.replace("_", " ").title()
            ))
            
            # Format Anchor with type context
            etype = group.anchor_event.artifact_type.upper()
            self._table.setItem(row, 1, QTableWidgetItem(
                f"[{etype}]  {group.anchor_event.title}"
            ))
            self._table.setItem(row, 2, QTableWidgetItem(
                group.anchor_event.timestamp.strftime("%Y-%m-%d %H:%M")
            ))
            self._table.setItem(row, 3, QTableWidgetItem(
                str(len(group.correlated_events))
            ))
            self._table.setItem(row, 4, QTableWidgetItem(
                f"{group.confidence:.0%}"
            ))

    def _on_click(self, row: int, col: int) -> None:
        if 0 <= row < len(self._groups):
            self.event_selected.emit(self._groups[row].anchor_event)
