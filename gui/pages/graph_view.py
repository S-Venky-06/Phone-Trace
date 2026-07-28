"""
PhoneTrace -- Graph View Page
================================

Interactive investigation graph showing events and correlations.
Uses QGraphicsView for zoom/pan and node selection.
"""

import math
import random
from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QPainter, QRadialGradient
from PyQt6.QtWidgets import (
    QComboBox, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsScene, QGraphicsTextItem, QGraphicsView,
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from case_config import INCIDENT_START, INCIDENT_END
from gui.theme import (
    ACCENT, BG_SECONDARY, BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM, WARNING,
    ARTIFACT_COLORS, BG_PRIMARY, BG_ELEVATED,
)

# Swimlane vertical coordinates
_LANE_Y = {
    "file": 80,
    "app_usage": 160,
    "browser": 240,
    "gps": 320,
    "sms": 400,
    "call": 480,
}


class _EventNode(QGraphicsEllipseItem):
    """A clickable node representing a ForensicEvent."""

    def __init__(self, event, x: float, y: float, radius: float = 8):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.event = event
        self.setPos(x, y)
        
        # Color matching artifact theme
        color_hex = ARTIFACT_COLORS.get(event.artifact_type, "#64748B")
        self._color = QColor(color_hex)
        
        # Radial gradient for subtle glow
        grad = QRadialGradient(0, 0, radius)
        grad.setColorAt(0.0, QColor(255, 255, 255, 220))
        grad.setColorAt(0.3, self._color)
        grad.setColorAt(1.0, QColor(self._color.red(), self._color.green(), self._color.blue(), 20))
        
        self.setBrush(QBrush(grad))
        self.setPen(QPen(self._color, 1.2))
        self.setToolTip(
            f"{event.artifact_type.upper()}: {event.title}\n"
            f"{event.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            f"Source: {event.source}"
        )
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.setPen(QPen(QColor(ACCENT), 2))
        self.setBrush(QBrush(self._color))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(self._color, 1.2))
        # Re-apply radial gradient
        grad = QRadialGradient(0, 0, 8)
        grad.setColorAt(0.0, QColor(255, 255, 255, 220))
        grad.setColorAt(0.3, self._color)
        grad.setColorAt(1.0, QColor(self._color.red(), self._color.green(), self._color.blue(), 20))
        self.setBrush(QBrush(grad))
        super().hoverLeaveEvent(event)


class GraphView(QWidget):
    """Interactive graph view of correlation relationships."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []
        self._nodes: dict[int, _EventNode] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Investigation Graph")
        header.setObjectName("heading")
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._filter = QComboBox()
        self._filter.addItems(["All Rules", "Communication Cluster",
                               "Movement Cluster", "Browser + GPS",
                               "File + GPS", "SMS + Browser",
                               "Call + Movement", "App + Movement"])
        self._filter.currentTextChanged.connect(self._rebuild)
        
        filter_label = QLabel("Correlation Rule:")
        filter_label.setStyleSheet(f"color: {TEXT_DIM}; font-weight: 500;")
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self._filter)

        toolbar.addSpacing(12)

        # Zoom Controls
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(30, 30)
        btn_zoom_in.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                border-color: {ACCENT};
            }}
        """)
        btn_zoom_in.setToolTip("Zoom In")
        btn_zoom_in.clicked.connect(lambda: self._view.scale(1.2, 1.2))
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedSize(30, 30)
        btn_zoom_out.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                border-color: {ACCENT};
            }}
        """)
        btn_zoom_out.setToolTip("Zoom Out")
        btn_zoom_out.clicked.connect(lambda: self._view.scale(0.8, 0.8))
        toolbar.addWidget(btn_zoom_out)

        btn_fit = QPushButton("Fit Window")
        btn_fit.setFixedHeight(30)
        btn_fit.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-weight: 500;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                border-color: {ACCENT};
            }}
        """)
        btn_fit.setToolTip("Fit all nodes in view")
        btn_fit.clicked.connect(self._fit)
        toolbar.addWidget(btn_fit)

        self._info = QLabel("")
        self._info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        toolbar.addStretch()
        toolbar.addWidget(self._info)

        layout.addLayout(toolbar)

        # Graphics view
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(0, 0, 4000, 560)
        self._scene.selectionChanged.connect(self._on_selection)

        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        layout.addWidget(self._view)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for atype, color_hex in ARTIFACT_COLORS.items():
            if atype == "unknown":
                continue
            dot = QLabel(f"● {atype.replace('_', ' ').title()}")
            dot.setStyleSheet(
                f"color: {color_hex}; font-size: 12px; font-weight: 600; background: transparent;"
            )
            legend.addWidget(dot)
        legend.addStretch()
        layout.addLayout(legend)

    def load_from_backend(self, backend) -> None:
        """Store correlation groups and build the graph."""
        if not backend or not backend.is_loaded:
            return
        self._groups = backend.correlations
        self._rebuild()

    def _rebuild(self, *args) -> None:
        """Rebuild the graph from stored groups."""
        self._scene.blockSignals(True)
        self._scene.clear()
        self._nodes.clear()

        rule_filter = self._filter.currentText()
        groups = self._groups
        if rule_filter != "All Rules":
            key = rule_filter.lower().replace(" + ", "_").replace(" ", "_")
            groups = [g for g in groups if g.rule_name == key]

        display_groups = groups[:80]

        all_events = []
        for g in display_groups:
            all_events.append(g.anchor_event)
            all_events.extend(g.correlated_events)

        if not all_events:
            self._info.setText("No correlations found.")
            self._scene.blockSignals(False)
            return

        min_time = min(e.timestamp for e in all_events)
        max_time = max(e.timestamp for e in all_events)
        if min_time.tzinfo is None:
            min_time = min_time.replace(tzinfo=timezone.utc)
        if max_time.tzinfo is None:
            max_time = max_time.replace(tzinfo=timezone.utc)

        min_ts = min_time.timestamp()
        max_ts = max_time.timestamp()

        # Draw vertical lines for day boundaries
        current_date = min_time.date()
        while current_date <= max_time.date():
            dt_day = datetime(current_date.year, current_date.month, current_date.day, tzinfo=min_time.tzinfo)
            day_ts = dt_day.timestamp()
            if min_ts <= day_ts <= max_ts:
                day_x = 150 + (day_ts - min_ts) / (max_ts - min_ts) * 3800
                self._scene.addLine(
                    day_x, 30, day_x, 520,
                    QPen(QColor(BORDER), 1, Qt.PenStyle.DashLine)
                )
                txt = self._scene.addText(current_date.strftime("%b %d"))
                txt.setDefaultTextColor(QColor(TEXT_DIM))
                txt.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                txt.setPos(day_x + 6, 12)
            current_date += timedelta(days=1)

        # Draw incident window highlight
        inc_start_ts = INCIDENT_START.timestamp()
        inc_end_ts = INCIDENT_END.timestamp()
        if min_ts <= inc_start_ts <= max_ts:
            ix1 = 150 + (inc_start_ts - min_ts) / (max_ts - min_ts) * 3800
            ix2 = 150 + (inc_end_ts - min_ts) / (max_ts - min_ts) * 3800
            rect_item = self._scene.addRect(
                QRectF(ix1, 30, max(ix2 - ix1, 10.0), 490),
                QPen(QColor(DANGER), 1, Qt.PenStyle.SolidLine),
                QBrush(QColor(239, 68, 68, 15))  # Soft red shade
            )
            rect_item.setToolTip("Incident Window")
            
            lbl = self._scene.addText("INCIDENT TIMEFRAME")
            lbl.setDefaultTextColor(QColor(DANGER))
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setPos(ix1 + 4, 500)

        # Draw axis line
        self._scene.addLine(
            150, 10, 150, 520,
            QPen(QColor(BORDER), 2)
        )
        for name, y in _LANE_Y.items():
            self._scene.addLine(
                150, y, 3950, y,
                QPen(QColor(BORDER), 1, Qt.PenStyle.DotLine)
            )
            lbl = self._scene.addText(name.replace("_", " ").upper())
            lbl.setDefaultTextColor(QColor(TEXT))
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setPos(15, y - 12)

        lane_occupied = {}

        def get_position(event):
            y = _LANE_Y.get(event.artifact_type, 300)
            ets = event.timestamp.replace(tzinfo=timezone.utc).timestamp() if event.timestamp.tzinfo is None else event.timestamp.timestamp()
            if max_ts == min_ts:
                x = 2000
            else:
                x = 150 + (ets - min_ts) / (max_ts - min_ts) * 3800
            
            bucket = int(x / 30)
            key = (y, bucket)
            count = lane_occupied.get(key, 0)
            lane_occupied[key] = count + 1
            
            offset = 0
            if count > 0:
                sign = 1 if count % 2 == 1 else -1
                offset = sign * ((count + 1) // 2) * 16
                
            return x, y + offset

        for group in display_groups:
            ax, ay = get_position(group.anchor_event)
            anchor = self._get_or_create_node(group.anchor_event, ax, ay)

            for evt in group.correlated_events:
                ex, ey = get_position(evt)
                node = self._get_or_create_node(evt, ex, ey)

                link_pen = QPen(QColor(125, 133, 144, 40), 1, Qt.PenStyle.SolidLine)
                self._scene.addLine(
                    ax, ay, ex, ey,
                    link_pen
                )

        self._info.setText(
            f"{len(display_groups)} groups | {len(self._nodes)} nodes"
        )
        self._scene.blockSignals(False)
        self._fit()

    def _get_or_create_node(self, event, x: float, y: float) -> _EventNode:
        uid = id(event)
        if uid in self._nodes:
            return self._nodes[uid]
        node = _EventNode(event, x, y)
        self._scene.addItem(node)
        self._nodes[uid] = node
        return node

    def _fit(self) -> None:
        if self._scene.items():
            self._view.fitInView(
                self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def _on_selection(self) -> None:
        selected = self._scene.selectedItems()
        for item in selected:
            if isinstance(item, _EventNode):
                self.event_selected.emit(item.event)
                break
