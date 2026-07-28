"""
PhoneTrace -- Interactive Tactical GPS Map Page
=================================================

Tactical forensic map with interactive zoom/pan controls, coordinate & timestamp HUD
tooltips, geofence warning zones, path animation playback, and Inspector integration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QPainter, QPainterPath, QRadialGradient, QWheelEvent
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGraphicsEllipseItem,
    QGraphicsScene, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from case_config import ALIBI_LOCATION, INCIDENT_LOCATION, INCIDENT_START, INCIDENT_END
from gui.theme import (
    ACCENT, BG_CARD, BG_ELEVATED, BG_PRIMARY,
    BG_SECONDARY, BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM,
)

logger = logging.getLogger("gui.MapView")


class _TacticalGraphicsView(QGraphicsView):
    """Custom QGraphicsView with mouse-wheel zoom and drag panning."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self._zoom_factor = 1.15
        self._current_zoom = 1.0

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"background: {BG_PRIMARY}; border: none;")

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in or out using mouse wheel."""
        if event.angleDelta().y() > 0:
            if self._current_zoom < 10.0:
                self.scale(self._zoom_factor, self._zoom_factor)
                self._current_zoom *= self._zoom_factor
        else:
            if self._current_zoom > 0.2:
                self.scale(1.0 / self._zoom_factor, 1.0 / self._zoom_factor)
                self._current_zoom /= self._zoom_factor

    def reset_zoom(self) -> None:
        """Reset view zoom and center scene."""
        self.resetTransform()
        self._current_zoom = 1.0
        self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self) -> None:
        if self._current_zoom < 10.0:
            self.scale(self._zoom_factor, self._zoom_factor)
            self._current_zoom *= self._zoom_factor

    def zoom_out(self) -> None:
        if self._current_zoom > 0.2:
            self.scale(1.0 / self._zoom_factor, 1.0 / self._zoom_factor)
            self._current_zoom /= self._zoom_factor


class _GPSNodeItem(QGraphicsEllipseItem):
    """Clickable, hoverable node representing a GPS ping with HUD tooltips."""

    def __init__(self, event, x: float, y: float, on_select_cb=None, radius: float = 6):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.event = event
        self.setPos(x, y)
        self._cb = on_select_cb
        self._selected = False

        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Color based on incident window
        is_incident = False
        if event.timestamp and INCIDENT_START <= event.timestamp <= INCIDENT_END:
            is_incident = True

        self._color = QColor(DANGER) if is_incident else QColor(ACCENT)

        grad = QRadialGradient(0, 0, radius)
        grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        grad.setColorAt(0.4, self._color)
        grad.setColorAt(1.0, QColor(self._color.red(), self._color.green(), self._color.blue(), 30))

        self.setBrush(QBrush(grad))
        self.setPen(QPen(self._color, 1.2))

        # Format HUD Tooltip
        lat = event.location.latitude if event.location else 0.0
        lon = event.location.longitude if event.location else 0.0
        acc = f"± {event.location.accuracy}m" if event.location and event.location.accuracy else "N/A"
        ts_str = event.timestamp.strftime("%Y-%m-%d  %H:%M:%S IST") if event.timestamp else "N/A"
        inc_tag = " <span style='color:#EF4444; font-weight:bold;'>(INCIDENT WINDOW)</span>" if is_incident else ""

        self.setToolTip(
            f"<b>📍 GPS Location Ping</b>{inc_tag}<br/>"
            f"<b>Timestamp:</b> {ts_str}<br/>"
            f"<b>Coordinates:</b> {lat:.5f}° N, {lon:.5f}° E<br/>"
            f"<b>Accuracy:</b> {acc}<br/>"
            f"<b>Source:</b> {event.source}"
        )

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if self._cb:
            self._cb(self.event)

    def set_active(self, active: bool) -> None:
        self._selected = active
        if active:
            self.setPen(QPen(QColor("#FFFFFF"), 2.5))
        else:
            self.setPen(QPen(self._color, 1.2))


class MapView(QWidget):
    """Tactical GPS map plotting suspect movement, alibi, incident zones, and playback."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list = []
        self._nodes: list[_GPSNodeItem] = []
        self._current_index = 0

        # Animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._step_animation)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        header = QLabel("GPS Map Visualization")
        header.setObjectName("heading")
        layout.addWidget(header)

        sub = QLabel("Tactical geospatial analysis plotting suspect movement, alibi location, and incident location.")
        sub.setObjectName("subheading")
        layout.addWidget(sub)

        # Map Frame Container
        map_container = QFrame()
        map_container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        container_layout = QVBoxLayout(map_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Canvas Scene & View
        self._scene = QGraphicsScene()
        self._view = _TacticalGraphicsView(self._scene, parent=self)
        container_layout.addWidget(self._view, stretch=1)

        # Floating Toolbar Overlay
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 12)
        toolbar.setSpacing(8)

        btn_fit = QPushButton("⛶ Fit View")
        btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fit.setStyleSheet(self._btn_style())
        btn_fit.clicked.connect(self._view.reset_zoom)
        toolbar.addWidget(btn_fit)

        btn_in = QPushButton("＋ Zoom In")
        btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_in.setStyleSheet(self._btn_style())
        btn_in.clicked.connect(self._view.zoom_in)
        toolbar.addWidget(btn_in)

        btn_out = QPushButton("－ Zoom Out")
        btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_out.setStyleSheet(self._btn_style())
        btn_out.clicked.connect(self._view.zoom_out)
        toolbar.addWidget(btn_out)

        toolbar.addStretch()

        btn_inc = QPushButton("⚡ Incident Window")
        btn_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inc.setStyleSheet(self._btn_style(DANGER))
        btn_inc.clicked.connect(self._focus_incident)
        toolbar.addWidget(btn_inc)

        # Add toolbar on top layout row
        top_bar_widget = QWidget(map_container)
        top_bar_widget.setLayout(toolbar)
        top_bar_widget.setStyleSheet("background: transparent;")
        container_layout.addWidget(top_bar_widget)

        layout.addWidget(map_container, stretch=1)

        # Bottom Playback Control Bar
        playback_frame = QFrame()
        playback_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 10px 16px;
            }}
        """)
        pb_layout = QHBoxLayout(playback_frame)
        pb_layout.setContentsMargins(0, 0, 0, 0)
        pb_layout.setSpacing(12)

        self._btn_play = QPushButton("▶  Play Path")
        self._btn_play.setObjectName("primaryBtn")
        self._btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_play.setFixedWidth(110)
        self._btn_play.setFixedHeight(34)
        self._btn_play.clicked.connect(self._toggle_play)
        pb_layout.addWidget(self._btn_play)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 6px;
                background: {BORDER};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ACCENT};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                border: 2px solid {ACCENT};
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }}
        """)
        self._slider.valueChanged.connect(self._on_slider_moved)
        pb_layout.addWidget(self._slider, stretch=1)

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["0.5x Speed", "1x Speed (Normal)", "2x Speed", "5x Speed"])
        self._speed_combo.setCurrentIndex(1)  # Default to 1x Speed (Normal)
        self._speed_combo.setFixedHeight(34)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        pb_layout.addWidget(self._speed_combo)

        layout.addWidget(playback_frame)

        # Readout Status Label
        self._status_lbl = QLabel("📍 Load evidence to view GPS pings and path animation.")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._status_lbl)

    def _btn_style(self, color: str = ACCENT) -> str:
        return f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                border-color: {color};
            }}
        """

    def load_from_backend(self, backend) -> None:
        """Plot GPS events and geofences onto map."""
        if not backend or not backend.is_loaded:
            return

        gps_events = [e for e in backend.events if e.artifact_type == "gps" and e.location]
        self._events = gps_events
        self._nodes.clear()
        self._scene.clear()

        if not gps_events:
            self._status_lbl.setText("No GPS events found in evidence.")
            return

        # Setup slider
        self._slider.setRange(0, len(gps_events) - 1)
        self._slider.setValue(0)

        lats = [e.location.latitude for e in gps_events] + [ALIBI_LOCATION['latitude'], INCIDENT_LOCATION['latitude']]
        lons = [e.location.longitude for e in gps_events] + [ALIBI_LOCATION['longitude'], INCIDENT_LOCATION['longitude']]

        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        lat_range = max(max_lat - min_lat, 0.01)
        lon_range = max(max_lon - min_lon, 0.01)

        width = 1000
        height = 600

        def to_xy(lat: float, lon: float):
            x = 60 + ((lon - min_lon) / lon_range) * (width - 120)
            y = height - 60 - ((lat - min_lat) / lat_range) * (height - 120)
            return x, y

        # Draw Grid Overlay Lines
        grid_pen = QPen(QColor(BORDER), 0.8, Qt.PenStyle.DashLine)
        for gx in range(60, width, 100):
            self._scene.addLine(gx, 40, gx, height - 40, grid_pen)
        for gy in range(40, height, 80):
            self._scene.addLine(40, gy, width - 40, gy, grid_pen)

        # Draw Geofence Warning Zones
        # Alibi Zone (Koramangala)
        ax, ay = to_xy(ALIBI_LOCATION['latitude'], ALIBI_LOCATION['longitude'])
        alibi_zone = self._scene.addEllipse(ax - 45, ay - 45, 90, 90, QPen(QColor(SUCCESS), 1.5, Qt.PenStyle.DashLine), QBrush(QColor(16, 185, 129, 25)))
        alibi_zone.setToolTip(f"<b>🎯 Alibi Zone:</b> {ALIBI_LOCATION['name']}")

        alibi_lbl = self._scene.addText(f"🎯 Alibi: {ALIBI_LOCATION['name']}")
        alibi_lbl.setDefaultTextColor(QColor(SUCCESS))
        alibi_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        alibi_lbl.setPos(ax + 12, ay - 14)

        # Incident Zone (Electronic City)
        ix, iy = to_xy(INCIDENT_LOCATION['latitude'], INCIDENT_LOCATION['longitude'])
        inc_zone = self._scene.addEllipse(ix - 55, iy - 55, 110, 110, QPen(QColor(DANGER), 2, Qt.PenStyle.DashLine), QBrush(QColor(239, 68, 68, 30)))
        inc_zone.setToolTip(f"<b>🚨 Incident Zone:</b> {INCIDENT_LOCATION['name']}")

        inc_lbl = self._scene.addText(f"🚨 Incident: {INCIDENT_LOCATION['name']}")
        inc_lbl.setDefaultTextColor(QColor(DANGER))
        inc_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        inc_lbl.setPos(ix + 12, iy - 14)

        # Draw Connecting Path Lines
        last_x, last_y = None, None
        for ev in gps_events:
            x, y = to_xy(ev.location.latitude, ev.location.longitude)
            if last_x is not None:
                is_inc = INCIDENT_START <= ev.timestamp <= INCIDENT_END if ev.timestamp else False
                line_color = QColor(DANGER) if is_inc else QColor(ACCENT)
                pen_style = Qt.PenStyle.SolidLine if is_inc else Qt.PenStyle.SolidLine

                line = self._scene.addLine(last_x, last_y, x, y, QPen(line_color, 1.8, pen_style))
                line.setOpacity(0.65 if not is_inc else 0.9)
            last_x, last_y = x, y

            # GPS Node Item
            node = _GPSNodeItem(ev, x, y, on_select_cb=self._on_node_selected)
            self._scene.addItem(node)
            self._nodes.append(node)

        # Center view
        self._view.reset_zoom()

        # Create prominent animated suspect beacon (bright glowing target)
        self._beacon_node = self._scene.addEllipse(-10, -10, 20, 20, QPen(QColor("#FFFFFF"), 2.5), QBrush(QColor(56, 189, 248)))
        self._beacon_node.setZValue(100)
        grad = QRadialGradient(0, 0, 10)
        grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        grad.setColorAt(0.4, QColor(56, 189, 248, 240))
        grad.setColorAt(1.0, QColor(56, 189, 248, 40))
        self._beacon_node.setBrush(QBrush(grad))

        # Active progressive path trail
        self._trail_path = self._scene.addPath(
            QPainterPath(), QPen(QColor(56, 189, 248), 3.5, Qt.PenStyle.SolidLine)
        )
        self._trail_path.setZValue(50)
        self._trail_path.setOpacity(0.9)

        self._select_ping(0)

    def _on_node_selected(self, event) -> None:
        """Handle clicking a node on the map canvas."""
        self.event_selected.emit(event)
        if event in self._events:
            idx = self._events.index(event)
            self._slider.setValue(idx)

    def _select_ping(self, index: int) -> None:
        """Select node at index, move glowing beacon, update trail, and status."""
        if not self._events or index < 0 or index >= len(self._events):
            return

        self._current_index = index

        # Highlight node
        target_node = self._nodes[index]
        x, y = target_node.x(), target_node.y()

        # Update glowing beacon location
        if hasattr(self, "_beacon_node") and self._beacon_node:
            self._beacon_node.setPos(x, y)

        # Update progressive active trail
        if hasattr(self, "_trail_path") and self._trail_path:
            path = QPainterPath()
            if self._nodes:
                path.moveTo(self._nodes[0].x(), self._nodes[0].y())
                for i in range(1, index + 1):
                    path.lineTo(self._nodes[i].x(), self._nodes[i].y())
            self._trail_path.setPath(path)

        ev = self._events[index]
        ts_str = ev.timestamp.strftime("%Y-%m-%d  %H:%M:%S IST") if ev.timestamp else "N/A"
        lat = ev.location.latitude if ev.location else 0.0
        lon = ev.location.longitude if ev.location else 0.0

        self._status_lbl.setText(
            f"<b>Ping #{index + 1} / {len(self._events)}:</b> &nbsp;&nbsp;"
            f"<b>Time:</b> <span style='color:{ACCENT};'>{ts_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Coordinates:</b> <span style='color:{TEXT};'>{lat:.5f}° N, {lon:.5f}° E</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Source:</b> {ev.source}"
        )

    def _on_slider_moved(self, value: int) -> None:
        self._select_ping(value)

    def _toggle_play(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._btn_play.setText("▶  Play Path")
            self._btn_play.setObjectName("primaryBtn")
            self._btn_play.setStyleSheet("")
        else:
            if self._current_index >= len(self._events) - 1:
                self._current_index = 0
            self._timer.start(50)
            self._btn_play.setText("⏸  Pause")
            self._btn_play.setStyleSheet(f"background-color: {DANGER}; color: #FFFFFF;")

    def _step_animation(self) -> None:
        if not self._events:
            return

        total = len(self._events)
        speed_idx = self._speed_combo.currentIndex()
        # Speed presets: 0.5x (div 400), 1x (div 200), 2x (div 100), 5x (div 40)
        divisors = [400.0, 200.0, 100.0, 40.0]
        div = divisors[speed_idx] if speed_idx < len(divisors) else 200.0
        step = max(1, int(total / div))

        if self._current_index < total - 1:
            next_idx = min(total - 1, self._current_index + step)
            self._slider.setValue(next_idx)
        else:
            self._timer.stop()
            self._btn_play.setText("▶  Play Path")
            self._btn_play.setStyleSheet("")

    def _on_speed_changed(self, idx: int) -> None:
        pass  # Speed is computed dynamically in _step_animation

    def _focus_incident(self) -> None:
        """Focus camera on the incident window pings."""
        inc_nodes = [
            n for n in self._nodes
            if n.event.timestamp and INCIDENT_START <= n.event.timestamp <= INCIDENT_END
        ]
        if inc_nodes:
            self._on_node_selected(inc_nodes[0].event)
            ix = inc_nodes[0].x()
            iy = inc_nodes[0].y()
            self._view.centerOn(ix, iy)
