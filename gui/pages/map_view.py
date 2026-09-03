"""
PhoneTrace -- Interactive Tactical GPS Map Page (WebEngine + Folium)
====================================================================

Tactical forensic map utilizing Folium and Leaflet.js to plot suspect movement,
alibi location, and incident location on a real interactive map.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import folium
from folium import plugins
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout, QWidget
)

# Only import QWebEngineView here to avoid missing dependency errors in older phases
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

from case_config import ALIBI_LOCATION, INCIDENT_LOCATION, INCIDENT_START, INCIDENT_END
from gui.theme import (
    ACCENT, BG_CARD, BG_SECONDARY, BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM
)

logger = logging.getLogger("gui.MapView")


class MapView(QWidget):
    """Tactical GPS map plotting suspect movement and zones using Folium."""

    event_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list = []
        self._current_index = 0

        # Animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._step_animation)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        header = QLabel("Interactive GPS Map Visualization")
        header.setObjectName("heading")
        layout.addWidget(header)

        sub = QLabel("Tactical geospatial analysis plotting suspect movement using real map data (Folium/Leaflet).")
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

        if QWebEngineView is None:
            lbl = QLabel("PyQt6-WebEngine is required for the interactive map.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(lbl)
            self._web_view = None
        else:
            self._web_view = QWebEngineView()
            container_layout.addWidget(self._web_view, stretch=1)
            # Init empty map
            empty_map = folium.Map(location=[12.9716, 77.5946], zoom_start=11, tiles="OpenStreetMap")
            empty_map.get_root().header.add_child(folium.Element("""
            <style>
                .leaflet-tile-pane { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }
            </style>
            """))
            data = io.BytesIO()
            empty_map.save(data, close_file=False)
            
            self._current_map_script = ""
            self._web_view.loadFinished.connect(self._on_map_loaded)
            self._web_view.setHtml(data.getvalue().decode())

        # Floating Toolbar Overlay (now simpler since WebEngine has built-in zoom/pan)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 12)
        toolbar.setSpacing(8)

        toolbar.addStretch()

        btn_inc = QPushButton("⚡ Focus Active Ping")
        btn_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inc.setStyleSheet(self._btn_style(DANGER))
        btn_inc.clicked.connect(self._focus_incident)
        toolbar.addWidget(btn_inc)

        # Add toolbar overlay if we want it, but for web view it might block interactions
        # We will just place it above the web view in the container layout for simplicity
        top_bar_widget = QWidget()
        top_bar_widget.setLayout(toolbar)
        container_layout.insertWidget(0, top_bar_widget)

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
        self._speed_combo.addItems(["0.5x Speed", "1x Speed", "2x Speed", "5x Speed"])
        self._speed_combo.setCurrentIndex(1)
        self._speed_combo.setFixedHeight(34)
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
                background-color: #2D333B;
                border-color: {color};
            }}
        """

    def load_from_backend(self, backend) -> None:
        """Plot GPS events and geofences onto the Folium map."""
        if not backend or not backend.is_loaded or self._web_view is None:
            return

        gps_events = [e for e in backend.events if e.artifact_type == "gps" and e.location]
        self._events = gps_events

        if not gps_events:
            self._status_lbl.setText("No GPS events found in evidence.")
            return

        # Setup slider
        self._slider.setRange(0, len(gps_events) - 1)
        self._slider.setValue(0)

        # Compute Center
        lats = [e.location.latitude for e in gps_events]
        lons = [e.location.longitude for e in gps_events]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Generate Folium Map using default OpenStreetMap (free, no API key)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles="OpenStreetMap"
        )
        
        # Inject CSS to invert the OpenStreetMap tiles to match our dark theme
        m.get_root().header.add_child(folium.Element("""
        <style>
            .leaflet-tile-pane {
                filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
            }
        </style>
        """))

        # Draw Zones
        folium.Circle(
            location=[ALIBI_LOCATION['latitude'], ALIBI_LOCATION['longitude']],
            radius=1500,
            color=SUCCESS,
            fill=True,
            fill_color=SUCCESS,
            fill_opacity=0.2,
            tooltip=f"Alibi: {ALIBI_LOCATION['name']}"
        ).add_to(m)

        folium.Circle(
            location=[INCIDENT_LOCATION['latitude'], INCIDENT_LOCATION['longitude']],
            radius=1500,
            color=DANGER,
            fill=True,
            fill_color=DANGER,
            fill_opacity=0.2,
            tooltip=f"Incident: {INCIDENT_LOCATION['name']}"
        ).add_to(m)

        # 1) Extract path_coords
        path_coords = []
        for ev in gps_events:
            path_coords.append((ev.location.latitude, ev.location.longitude))

        # 2) Draw a dim static base path UNDER the dots
        folium.PolyLine(
            path_coords,
            color='#334155', # Dim slate gray
            weight=3,
            opacity=0.6
        ).add_to(m)        # Save to HTML string
        data = io.BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()

        # Build JSON for JS dynamic path and dots
        import json
        path_data = []
        for i, ev in enumerate(gps_events):
            is_inc = bool(ev.timestamp and INCIDENT_START <= ev.timestamp <= INCIDENT_END)
            ts_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp else "N/A"
            path_data.append({
                "lat": ev.location.latitude,
                "lon": ev.location.longitude,
                "isInc": is_inc,
                "ts": ts_str
            })
        path_json = json.dumps(path_data)

        script = f"""
            var _mapInstance = null;
            function _getMap() {{
                if (_mapInstance) return _mapInstance;
                for (var key in window) {{
                    if (key.startsWith('map_') && window[key] && typeof window[key].flyTo === 'function') {{
                        _mapInstance = window[key];
                        return _mapInstance;
                    }}
                }}
                return null;
            }}
            
            window.allPings = {path_json};
            window.activeMarker = null;
            window.dynamicPath = null;
            window.dotsGroup = null;
            
            window.initMapLayers = function() {{
                var m = _getMap();
                if (!m || typeof L === 'undefined') return;
                
                // Create glowing path first so it renders underneath dots
                if (!window.dynamicPath) {{
                    window.dynamicPath = L.polyline([], {{
                        color: '{ACCENT}', 
                        weight: 5, 
                        opacity: 0.9,
                        className: 'glowing-path'
                    }}).addTo(m);
                }}
                
                // Create dots layer group on top
                if (!window.dotsGroup) {{
                    var dots = window.allPings.map(function(p, i) {{
                        var color = p.isInc ? '{DANGER}' : '#475569';
                        return L.circleMarker([p.lat, p.lon], {{
                            radius: 3, 
                            color: color, 
                            fillColor: color, 
                            fillOpacity: 0.9,
                            weight: 1
                        }}).bindTooltip("Ping #" + i + ": " + p.ts + "<br>Lat: " + p.lat.toFixed(5) + ", Lon: " + p.lon.toFixed(5));
                    }});
                    window.dotsGroup = L.layerGroup(dots).addTo(m);
                }}
            }};
            
            window.updateActiveMarker = function(index, lat, lon) {{
                var m = _getMap();
                if (!m || typeof L === 'undefined') return;
                
                window.initMapLayers();
                
                var currentCoords = [];
                for (var i = 0; i <= index && i < window.allPings.length; i++) {{
                    currentCoords.push([window.allPings[i].lat, window.allPings[i].lon]);
                }}
                window.dynamicPath.setLatLngs(currentCoords);
                
                // Update the beacon marker
                if (!window.activeMarker) {{
                    var icon = L.divIcon({{
                        className: 'custom-beacon',
                        html: '<div style="background-color:{ACCENT}; width:16px; height:16px; border-radius:50%; border: 3px solid white; box-shadow: 0 0 15px {ACCENT};"></div>',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    }});
                    window.activeMarker = L.marker([lat, lon], {{icon: icon, zIndexOffset: 2000}}).addTo(m);
                }} else {{
                    window.activeMarker.setLatLng([lat, lon]);
                }}
            }};
            
            window.panToIncident = function(lat, lon) {{
                var m = _getMap();
                if (m) {{
                    m.flyTo([lat, lon], 15);
                }}
            }};
            
            // Add a style tag for the glowing path if needed
            if (!document.getElementById('custom-map-styles')) {{
                var style = document.createElement('style');
                style.id = 'custom-map-styles';
                style.innerHTML = '.glowing-path {{ filter: drop-shadow(0 0 4px {ACCENT}); }}';
                document.head.appendChild(style);
            }}
        """
        self._current_map_script = script
        self._web_view.setHtml(html)

    def _on_map_loaded(self, ok: bool) -> None:
        """Handle map load completion and inject JavaScript."""
        if not ok:
            return
            
        if hasattr(self, '_current_map_script') and self._current_map_script:
            self._web_view.page().runJavaScript(self._current_map_script)
            # Re-select the current ping so the beacon shows up immediately after map load
            self._select_ping(self._current_index if hasattr(self, '_current_index') and self._current_index >= 0 else 0)

    def _select_ping(self, index: int) -> None:
        """Update active status and move the beacon marker in JS."""
        if not self._events or index < 0 or index >= len(self._events):
            return

        self._current_index = index
        ev = self._events[index]
        lat = ev.location.latitude if ev.location else 0.0
        lon = ev.location.longitude if ev.location else 0.0

        if self._web_view:
            self._web_view.page().runJavaScript(f"updateActiveMarker({index}, {lat}, {lon});")

        ts_str = ev.timestamp.strftime("%Y-%m-%d  %H:%M:%S IST") if ev.timestamp else "N/A"
        
        self._status_lbl.setText(
            f"<b>Ping #{index + 1} / {len(self._events)}:</b> &nbsp;&nbsp;"
            f"<b>Time:</b> <span style='color:{ACCENT};'>{ts_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Coordinates:</b> <span style='color:{TEXT};'>{lat:.5f}° N, {lon:.5f}° E</span>"
        )
        self.event_selected.emit(ev)

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
            speed_idx = self._speed_combo.currentIndex()
            intervals = [100, 50, 40, 20]
            timer_ms = intervals[speed_idx] if speed_idx < len(intervals) else 50
            
            self._timer.start(timer_ms)
            self._btn_play.setText("⏸  Pause")
            self._btn_play.setStyleSheet(f"background-color: {DANGER}; color: #FFFFFF;")

    def _step_animation(self) -> None:
        if not self._events:
            return

        speed_idx = self._speed_combo.currentIndex()
        
        # 0.5x: step=1 (every 100ms)
        # 1.0x: step=1 (every 50ms)
        # 2.0x: step=2 (every 40ms)
        # 5.0x: step=5 (every 20ms)
        steps = [1, 1, 2, 5]
        step = steps[speed_idx] if speed_idx < len(steps) else 1

        total = len(self._events)
        if self._current_index < total - 1:
            next_idx = min(total - 1, self._current_index + step)
            self._slider.setValue(next_idx)
        else:
            self._timer.stop()
            self._btn_play.setText("▶  Play Path")
            self._btn_play.setStyleSheet("")

    def _focus_incident(self) -> None:
        """Focus camera on the current active ping via JS."""
        if self._web_view and self._events:
            ev = self._events[self._current_index]
            lat = ev.location.latitude if ev.location else 0.0
            lon = ev.location.longitude if ev.location else 0.0
            self._web_view.page().runJavaScript(f"panToIncident({lat}, {lon});")

